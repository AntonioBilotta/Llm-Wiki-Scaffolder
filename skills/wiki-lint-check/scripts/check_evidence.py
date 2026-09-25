#!/usr/bin/env python3
"""check_evidence.py — mechanical source-fidelity check for an LLM Wiki vault.

Read-only. Never modifies any file. Prints one JSON document on stdout and
always exits 0: the report is the interface, not the exit code.

The grounding invariant (see the vault's wiki-conventions.instructions.md,
"Source fidelity"): every load-bearing literal on a wiki page — specific
numbers, ISO dates, direct quotes — exists verbatim in the raw/ file behind
a source page the wiki page cites. Idea adapted from Astro-Han/karpathy-llm-wiki
(MIT); the implementation is independent and follows this vault's layout:

    wiki page --related_sources / [[wikilink]]--> wiki/sources/<page>.md
    source page --"- **Provenance**: `<raw path>`"--> raw/<file>

Three sweeps:

1. fidelity         — candidate literals of each page in scope that are not
                      found in any raw file linked to it. Candidates are
                      suspects, not verdicts: derived values, product names
                      and deliberate paraphrases show up too. Judging them is
                      the caller's job (wiki-lint-check), not this script's.
2. evidence_errors  — pages that cannot be verified at all: no sources, a
                      related_sources entry that is not a page, a source page
                      without a resolvable Provenance, a raw path outside raw/.
   unverifiable     — evidence exists but is not text (PDF, image, Office),
                      so literals cannot be grepped.
3. unreferenced_raw — raw files no source page points to, excluding files
                      logged as "## [date] ingest | no material: raw/<path>".
                      Always computed over the whole vault.

Candidate set (closed, deliberately narrow):
  - quotes of 15+ characters: "…", “…”, and plain body blockquotes
  - ISO dates: YYYY-MM-DD, YYYY-MM
  - specific numbers: thousands-grouped (10,000), dotted (3.14, 2.1.80),
    suffixed (42K, 1.5M, 99.9%), or 4+ digits (2026)
Small plain integers ("42", "500") are not checked; they fall under the
write-time "locate before you write" rule and under judgment review.
Masked before extraction: frontmatter, fenced code, inline code, wikilinks,
link targets, HTML comments, and the source page's Provenance/Date lines.

Usage:
  check_evidence.py --vault-path <vault root> [--pages name1,name2,...]

Requires Python 3.8+. Standard library only (ADR-0001).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

EXCLUDED_PAGES = {"index", "log", "overview"}
NON_TEXT_SUFFIXES = {
    ".pdf", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".tif", ".tiff",
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".odt", ".zip", ".epub",
    ".mp3", ".mp4", ".wav", ".mov",
}
MIN_QUOTE_LEN = 15

FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
INLINE_CODE_RE = re.compile(r"(`+)(?:(?!\1).)+?\1")
EMBED_OR_WIKILINK_RE = re.compile(r"!?\[\[[^\]\n]*\]\]")
WIKILINK_TARGET_RE = re.compile(r"\[\[([^\]|#\n]+)(?:[#|][^\]\n]*)?\]\]")
LINK_TARGET_RE = re.compile(r"\]\([^)\n]*\)")
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
CALLOUT_MARK_RE = re.compile(r"^>\s*\[![A-Za-z-]+\][+-]?\s*")
BLOCKQUOTE_RE = re.compile(r"^>\s?(.*)$")
METADATA_LINE_RE = re.compile(r"^-\s+\*\*(Provenance|Date)\*\*:")
PROVENANCE_RE = re.compile(r"^-\s+\*\*Provenance\*\*:\s*(`+)\s?(.*?)\s?\1", re.M)
QUOTE_RES = [re.compile(r'"([^"\n]+)"'), re.compile(r"“([^”\n]+)”")]
DATE_RE = re.compile(r"(?<![\d-])\d{4}-\d{2}(?:-\d{2})?(?![\d-])")
NUMBER_RE = re.compile(
    r"(?<![\w.,])"
    r"(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)+|\d+)"
    r"(\s?[KMB%](?![A-Za-z]))?"
    r"(?![\d])"
)
NO_MATERIAL_RE = re.compile(r"^##\s*\[[^\]]*\]\s*ingest\s*\|\s*no material:\s*(\S+)", re.I)
FLOW_ITEM_RE = re.compile(r'"((?:[^"\\]|\\.)*)"|\'([^\']*)\'|([^,\s][^,]*)')


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def split_frontmatter(text: str) -> Tuple[Dict[str, object], str, int]:
    """Return (fields, body, body_start_line). Lenient: only `type` and list
    fields matter here. A malformed block is treated as no frontmatter."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}, text, 1
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            fm_lines = lines[1:i]
            body = "\n".join(lines[i + 1:])
            return parse_simple_yaml(fm_lines), body, i + 2
    return {}, text, 1


def parse_simple_yaml(lines: List[str]) -> Dict[str, object]:
    fields: Dict[str, object] = {}
    current_list: Optional[str] = None
    for raw in lines:
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if m:
            key, value = m.group(1), m.group(2).strip()
            current_list = None
            if value.startswith("[") and value.endswith("]"):
                fields[key] = parse_flow_list(value[1:-1])
            elif value == "":
                fields[key] = []
                current_list = key
            else:
                fields[key] = value.split(" #")[0].strip().strip("\"'")
            continue
        item = re.match(r"^\s*-\s+(.*)$", line)
        if item and current_list is not None:
            lst = fields.setdefault(current_list, [])
            if isinstance(lst, list):
                lst.append(item.group(1).strip().strip("\"'"))
    return fields


def parse_flow_list(inner: str) -> List[str]:
    out: List[str] = []
    for m in FLOW_ITEM_RE.finditer(inner):
        if m.group(1) is not None:
            try:
                out.append(json.loads('"' + m.group(1) + '"'))
            except ValueError:
                out.append(m.group(1))
        elif m.group(2) is not None:
            out.append(m.group(2))
        elif m.group(3) is not None and m.group(3).strip():
            out.append(m.group(3).strip())
    return [x for x in out if x]


def page_name(ref: str) -> str:
    """Normalize a page reference: strip [[ ]], folders, .md, whitespace."""
    ref = ref.strip().strip("[]").strip()
    ref = ref.split("|", 1)[0].split("#", 1)[0]
    ref = ref.replace("\\", "/").rsplit("/", 1)[-1]
    if ref.lower().endswith(".md"):
        ref = ref[:-3]
    return ref.strip()


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = (text.replace("“", '"').replace("”", '"')
                .replace("‘", "'").replace("’", "'")
                .replace(" ", " "))
    return re.sub(r"\s+", " ", text)


def normalize_for_quote(text: str) -> str:
    text = normalize_text(text)
    text = re.sub(r"[*_`]", "", text)  # markdown emphasis/code in raw or wiki
    return text.casefold().strip(" .,;:!?\"'")


def normalize_number(token: str) -> str:
    return re.sub(r"\s+", "", token).upper()


# ---------------------------------------------------------------------------
# Candidate extraction
# ---------------------------------------------------------------------------


def extract_candidates(body: str, first_line: int) -> List[Tuple[str, str, int]]:
    """Return (kind, value, line_number) for each candidate literal."""
    body = HTML_COMMENT_RE.sub(lambda m: "\n" * m.group(0).count("\n"), body)
    out: List[Tuple[str, str, int]] = []
    in_fence: Optional[str] = None
    for offset, raw_line in enumerate(body.split("\n")):
        lineno = first_line + offset
        fence = FENCE_RE.match(raw_line)
        if in_fence is not None:
            if fence and fence.group(1)[0] == in_fence[0] and len(fence.group(1)) >= len(in_fence):
                in_fence = None
            continue
        if fence:
            in_fence = fence.group(1)
            continue
        line = raw_line.strip()
        if not line or METADATA_LINE_RE.match(line):
            continue
        line = INLINE_CODE_RE.sub(" ", line)
        line = EMBED_OR_WIKILINK_RE.sub(" ", line)
        line = LINK_TARGET_RE.sub("]", line)

        is_callout = bool(CALLOUT_MARK_RE.match(line))
        line = CALLOUT_MARK_RE.sub("", line)
        bq = BLOCKQUOTE_RE.match(line)
        if bq and not is_callout:
            quoted = bq.group(1).strip()
            if len(quoted) >= MIN_QUOTE_LEN:
                out.append(("quote", quoted, lineno))
            line = quoted

        for rx in QUOTE_RES:
            for m in rx.finditer(line):
                if len(m.group(1).strip()) >= MIN_QUOTE_LEN:
                    out.append(("quote", m.group(1).strip(), lineno))

        for m in DATE_RE.finditer(line):
            out.append(("date", m.group(0), lineno))
        masked = DATE_RE.sub(lambda m: " " * len(m.group(0)), line)

        for m in NUMBER_RE.finditer(masked):
            number, suffix = m.group(1), m.group(2) or ""
            specific = bool(suffix) or "," in number or "." in number or len(number) >= 4
            if specific:
                out.append(("number", (number + suffix).strip(), lineno))
    return out


def found_in(kind: str, value: str, raw_norm: str, raw_quote_norm: str) -> bool:
    if kind == "quote":
        return normalize_for_quote(value) in raw_quote_norm
    if kind == "date":
        return re.search(r"(?<![\d-])" + re.escape(value) + r"(?![\d])", raw_norm) is not None
    token = normalize_number(value)
    m = re.match(r"^(.*?)([KMB%]?)$", token)
    digits, suffix = (m.group(1), m.group(2)) if m else (token, "")
    pattern = r"(?<![\d.,])" + re.escape(digits)
    pattern += (r"\s?" + re.escape(suffix)) if suffix else r"(?![\d]|[.,]\d)"
    return re.search(pattern, raw_norm, re.I) is not None


# ---------------------------------------------------------------------------
# Vault model
# ---------------------------------------------------------------------------


class Vault:
    def __init__(self, root: Path):
        self.root = root
        self.wiki = root / "wiki"
        self.raw = root / "raw"
        self.pages: Dict[str, Path] = {}
        self.duplicates: Set[str] = set()
        for path in sorted(self.wiki.rglob("*.md")):
            name = path.stem
            if name in self.pages:
                self.duplicates.add(name)
                continue
            self.pages[name] = path
        self._parsed: Dict[str, Tuple[Dict[str, object], str, int]] = {}
        self._raw_cache: Dict[Path, Tuple[str, str]] = {}

    def rel(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self.root.resolve()).as_posix()
        except ValueError:
            return path.as_posix()

    def parsed(self, name: str) -> Tuple[Dict[str, object], str, int]:
        if name not in self._parsed:
            text = self.pages[name].read_text(encoding="utf-8", errors="replace")
            self._parsed[name] = split_frontmatter(text.replace("\r\n", "\n"))
        return self._parsed[name]

    def is_source_page(self, name: str) -> bool:
        path = self.pages[name]
        fields = self.parsed(name)[0]
        return path.parent == self.wiki / "sources" or fields.get("type") == "source"

    def resolve_raw(self, recorded: str) -> Tuple[Optional[Path], Optional[str]]:
        """Map a Provenance path to a file under raw/. Absolute paths recorded
        on another machine are re-anchored on their `raw/` segment."""
        recorded = recorded.strip()
        if not recorded:
            return None, "empty_provenance"
        candidates: List[Path] = []
        p = Path(recorded)
        if p.is_absolute():
            candidates.append(p)
        else:
            candidates.append(self.root / recorded)
        posix = recorded.replace("\\", "/")
        idx = posix.lower().rfind("/raw/")
        tail = posix[idx + 5:] if idx >= 0 else (posix[4:] if posix.lower().startswith("raw/") else None)
        if tail:
            candidates.append(self.raw / tail)
        for cand in candidates:
            if cand.is_file():
                try:
                    cand.resolve().relative_to(self.raw.resolve())
                except ValueError:
                    return None, "provenance_outside_raw"
                return cand, None
        return None, "provenance_not_found"

    def provenance(self, name: str) -> Tuple[Optional[Path], Optional[str]]:
        body = self.parsed(name)[1]
        m = PROVENANCE_RE.search(body)
        if not m:
            return None, "no_provenance"
        return self.resolve_raw(m.group(2))

    def raw_text(self, path: Path) -> Optional[Tuple[str, str]]:
        if path not in self._raw_cache:
            if path.suffix.lower() in NON_TEXT_SUFFIXES:
                return None
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                return None
            self._raw_cache[path] = (normalize_text(text), normalize_for_quote(text))
        return self._raw_cache[path]

    def cited_sources(self, name: str) -> Tuple[List[str], List[str]]:
        """Return (source page names, related_sources entries that are not pages)."""
        fields, body, _ = self.parsed(name)
        related = fields.get("related_sources") or []
        if isinstance(related, str):
            related = [related]
        sources: List[str] = []
        missing: List[str] = []
        for ref in related:
            n = page_name(str(ref))
            if n in self.pages:
                if n not in sources:
                    sources.append(n)
            elif n:
                missing.append(n)
        for m in WIKILINK_TARGET_RE.finditer(body):
            n = page_name(m.group(1))
            if n in self.pages and n != name and self.is_source_page(n) and n not in sources:
                sources.append(n)
        return sources, missing


# ---------------------------------------------------------------------------
# Sweeps
# ---------------------------------------------------------------------------


def check(vault: Vault, scope: Optional[List[str]]) -> Dict[str, object]:
    fidelity: List[Dict[str, object]] = []
    errors: List[Dict[str, str]] = []
    unverifiable: List[Dict[str, str]] = []
    candidates_checked = 0

    all_names = [n for n in sorted(vault.pages) if n not in EXCLUDED_PAGES]
    if scope is None:
        names = all_names
    else:
        names = []
        for ref in scope:
            n = page_name(ref)
            if n in vault.pages:
                if n not in EXCLUDED_PAGES and n not in names:
                    names.append(n)
            else:
                errors.append({"page": n, "issue": "page_not_found", "detail": "listed in --pages"})
        names.sort()

    for name in sorted(vault.duplicates):
        errors.append({"page": name, "issue": "ambiguous_page_name",
                       "detail": "same file name in several wiki folders; only the first is checked"})

    for name in names:
        fields = vault.parsed(name)[0]
        if fields.get("type") in ("index", "overview"):
            continue
        if vault.is_source_page(name):
            source_pages = [name]
            missing: List[str] = []
        else:
            source_pages, missing = vault.cited_sources(name)
            for n in missing:
                errors.append({"page": name, "issue": "related_source_not_found", "detail": n})
            if not source_pages:
                errors.append({"page": name, "issue": "no_sources",
                               "detail": "no related_sources and no [[source]] citation; cannot verify"})
                continue

        raw_texts: List[Tuple[str, str]] = []
        raw_rel: List[str] = []
        for src in source_pages:
            raw_path, problem = vault.provenance(src)
            if raw_path is None:
                errors.append({"page": name, "issue": problem or "provenance_error",
                               "detail": f"source page {src}"})
                continue
            texts = vault.raw_text(raw_path)
            if texts is None:
                unverifiable.append({"page": name, "raw": vault.rel(raw_path),
                                     "reason": "raw file is not plain text"})
                continue
            raw_texts.append(texts)
            raw_rel.append(vault.rel(raw_path))

        if not raw_texts:
            continue
        _, body, first_line = vault.parsed(name)
        suspects: List[Dict[str, object]] = []
        seen: Set[Tuple[str, str]] = set()
        for kind, value, lineno in extract_candidates(body, first_line):
            if (kind, value) in seen:
                continue
            seen.add((kind, value))
            candidates_checked += 1
            if not any(found_in(kind, value, t, q) for t, q in raw_texts):
                suspects.append({"kind": kind, "value": value, "line": lineno})
        if suspects:
            fidelity.append({"page": name, "path": vault.rel(vault.pages[name]),
                             "raw": sorted(raw_rel), "suspects": suspects})

    unreferenced = inventory(vault)
    return {
        "version": 1,
        "vault": str(vault.root),
        "scope": "vault" if scope is None else names,
        "checked": len(names),
        "fidelity": fidelity,
        "evidence_errors": sorted(errors, key=lambda e: (e["page"], e["issue"], e["detail"])),
        "unverifiable": sorted(unverifiable, key=lambda e: (e["page"], e["raw"])),
        "unreferenced_raw": unreferenced,
        "summary": {
            "pages_checked": len(names),
            "candidates_checked": candidates_checked,
            "suspects": sum(len(f["suspects"]) for f in fidelity),  # type: ignore[arg-type]
            "evidence_errors": len(errors),
            "unverifiable": len(unverifiable),
            "unreferenced_raw": len(unreferenced),
        },
    }


def inventory(vault: Vault) -> List[str]:
    if not vault.raw.is_dir():
        return []
    referenced: Set[str] = set()
    for name in vault.pages:
        if vault.is_source_page(name):
            raw_path, _ = vault.provenance(name)
            if raw_path is not None:
                referenced.add(vault.rel(raw_path).casefold())
    no_material: Set[str] = set()
    log = vault.wiki / "log.md"
    if log.is_file():
        for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
            m = NO_MATERIAL_RE.match(line.strip())
            if m:
                no_material.add(m.group(1).replace("\\", "/").strip("`").casefold())
    out: List[str] = []
    for path in sorted(vault.raw.rglob("*")):
        if not path.is_file():
            continue
        rel = vault.rel(path)
        parts = Path(rel).parts
        if path.name == ".gitkeep" or any(p.startswith(".") for p in parts):
            continue
        if len(parts) > 1 and parts[1] == "assets":
            continue
        key = rel.casefold()
        if key not in referenced and key not in no_material:
            out.append(rel)
    return out


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Mechanical source-fidelity check (read-only, JSON on stdout).")
    parser.add_argument("--vault-path", required=True, help="Vault root (contains wiki/ and raw/).")
    parser.add_argument("--pages", default="", help="Comma-separated page names to limit fidelity/evidence checks.")
    args = parser.parse_args(argv)
    # Windows consoles default to a legacy code page; the report may contain
    # any Unicode from wiki pages, so force UTF-8 on stdout when possible.
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (ValueError, OSError):
            pass

    root = Path(args.vault_path).expanduser()
    if not (root / "wiki").is_dir():
        json.dump({"version": 1, "vault": str(root), "note": "no wiki/ directory under vault path",
                   "fidelity": [], "evidence_errors": [], "unverifiable": [], "unreferenced_raw": []},
                  sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0
    scope = [p for p in (x.strip() for x in args.pages.split(",")) if p] or None
    report = check(Vault(root), scope)
    json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
