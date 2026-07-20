#!/usr/bin/env python3
"""scaffold.py — Deterministic LLM Wiki Scaffolder (Karpathy pattern).

Creates a new Obsidian vault structured as an LLM Wiki. Copies templates
from ~/.config/llm-wiki/templates/ (or $LLM_WIKI_TEMPLATES if set) into
the target path with placeholder substitution.

Karpathy pattern invariants enforced:
  - raw/ is user-owned and immutable. The script only creates empty raw/
    subfolders (with .gitkeep) and, if --seed is given, adds a single
    starter source. It never modifies existing raw/ content.
  - wiki/ is LLM-owned. The script creates only the navigation files
    (index.md, log.md, overview.md) and leaves all content folders
    (entities/, concepts/, sources/, analysis/, extra folders) empty.
  - The signpost (.github/copilot-instructions.md) stays minimal.
    Conventions live in .github/instructions/wiki-conventions.instructions.md.

Requires Python 3.8+. Standard library only.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TEMPLATES_ENV = "LLM_WIKI_TEMPLATES"

# Cross-platform default templates directory:
#   Windows:  %APPDATA%\llm-wiki\templates
#   Unix:     ~/.config/llm-wiki/templates
if sys.platform == "win32":
    _appdata = os.environ.get("APPDATA")
    DEFAULT_TEMPLATES = Path(_appdata) / "llm-wiki" / "templates" if _appdata else Path.home() / ".config" / "llm-wiki" / "templates"
else:
    DEFAULT_TEMPLATES = Path.home() / ".config" / "llm-wiki" / "templates"
WIKI_MARKER = "LLM Wiki"  # marker string in .github/copilot-instructions.md

# Domain configurations. Keys are the internal domain type identifiers.
# `display_type` is the user-facing string written to {{DOMAIN_TYPE}}.
DOMAIN_CONFIGS: Dict[str, Dict] = {
    "research": {
        "display_type": "research",
        "raw_folders": ["research", "notes", "data"],
        "extra_wiki_folders": ["findings", "open_questions"],
        "extra_page_types": ["finding", "hypothesis"],
        "overview_template": "research.md",
        "seed_default_subfolder": "research",
        "conventions": (
            "Cite every factual claim with a link to a `wiki/sources/` page. "
            "When a hypothesis is contradicted by a new source, flag it with "
            "`> [!warning] Contradiction:` on the affected page and update or "
            "revise the corresponding `wiki/findings/` and `wiki/open_questions/` entries."
        ),
    },
    "development": {
        "display_type": "development",
        "raw_folders": ["specs", "meetings", "tickets", "brainstorming"],
        "extra_wiki_folders": ["decisions", "requirements"],
        "extra_page_types": ["decision", "requirement"],
        "overview_template": "development.md",
        "seed_default_subfolder": "specs",
        "conventions": (
            "Decisions follow ADR format (context, decision, consequences) under `wiki/decisions/`. "
            "Requirements use stable IDs like `REQ-001` both in the file name (`req_001_<slug>.md`) "
            "and in the frontmatter (`id: REQ-001`). `raw/specs/` is treated as authoritative user input."
        ),
    },
    "reading_fiction": {
        "display_type": "reading (fiction)",
        "raw_folders": ["chapters", "notes"],
        "extra_wiki_folders": ["characters", "themes"],
        "extra_page_types": ["character", "theme"],
        "overview_template": "reading_fiction.md",
        "seed_default_subfolder": "chapters",
        "conventions": (
            "Wiki pages reflect only the reader's current state of knowledge. "
            "Do not add information from chapters not yet ingested. "
            "If a later revelation retroactively changes an earlier fact, flag it with "
            "`> [!warning] Retcon: <detail>` on the affected page and cite the chapter where the revelation occurs."
        ),
    },
    "reading_nonfiction": {
        "display_type": "reading (non-fiction)",
        "raw_folders": ["chapters", "notes"],
        "extra_wiki_folders": ["authors", "arguments"],
        "extra_page_types": ["author", "argument"],
        "overview_template": "reading_nonfiction.md",
        "seed_default_subfolder": "chapters",
        "conventions": (
            "Each argument tracks premises, evidence, and objections separately under `wiki/arguments/`. "
            "Distinguish verbatim quotations from paraphrases in `wiki/sources/` — "
            "use `> quote` blocks for quotations and note page numbers when available."
        ),
    },
    "personal": {
        "display_type": "personal",
        "raw_folders": ["journal", "articles", "podcasts"],
        "extra_wiki_folders": ["goals", "patterns", "reflections"],
        "extra_page_types": ["goal", "pattern", "reflection"],
        "overview_template": "personal.md",
        "seed_default_subfolder": "articles",
        "conventions": (
            "This wiki may contain personal or sensitive information. Treat all pages as personal-scope. "
            "When flagging emotional patterns, prefer descriptive language over diagnostic labels. "
            "Do not commit to a public git remote without review."
        ),
    },
    "business": {
        "display_type": "business",
        "raw_folders": ["meetings", "reports", "competitors", "customers"],
        "extra_wiki_folders": ["processes", "people", "initiatives"],
        "extra_page_types": ["process", "initiative"],
        "overview_template": "business.md",
        "seed_default_subfolder": "reports",
        "conventions": (
            "Meeting notes go under `raw/meetings/YYYY-MM-DD_<topic>.md`. "
            "People pages track role, team, and working relationship — not personal details. "
            "Redact or omit sensitive customer identifiers before ingest."
        ),
    },
    "learning": {
        "display_type": "learning",
        "raw_folders": ["courses", "exercises", "references"],
        "extra_wiki_folders": ["topics", "flashcards"],
        "extra_page_types": ["topic", "exercise"],
        "overview_template": "learning.md",
        "seed_default_subfolder": "references",
        "conventions": (
            "Concept pages under `wiki/topics/` should include at least one worked example. "
            "Flashcards under `wiki/flashcards/` follow a minimal question/answer format with "
            "`tags: [flashcard]` in frontmatter."
        ),
    },
    "hobby": {
        "display_type": "hobby",
        "raw_folders": ["references", "notes"],
        "extra_wiki_folders": [],
        "extra_page_types": [],
        "overview_template": "hobby.md",
        "seed_default_subfolder": "references",
        "conventions": (
            "This is a `custom`/`hobby` domain, so structure is intentionally open. "
            "Define conventions here as the vault evolves and record every change in this file."
        ),
    },
}

BASE_TYPES = ["research", "development", "reading", "personal", "business", "learning", "hobby"]

USAGE = """\
Usage:
  scaffold.py --path <vault> --name "<name>" --type <type> --desc "<desc>" --lang <lang> [options]
  scaffold.py --detect-only --path <vault>
  scaffold.py --help

Deterministic scaffolder for LLM Wiki vaults (Karpathy pattern).

Required (except in --help / --detect-only):
  --path <path>              Vault path (will be created if absent)
  --name "<name>"            Human-readable project name
  --type <type>              Domain type: research | development | reading | personal
                             | business | learning | hobby
  --desc "<desc>"            One-line domain description
  --lang <italian|english>   Wiki content language

Reading subvariant (required when --type reading):
  --fiction                  Fiction subvariant (chapters, characters, themes)
  --nonfiction               Non-fiction subvariant (chapters, authors, arguments)

Optional:
  --raw-folders "a,b,c"           Override default raw/ subfolders
  --extra-wiki-folders "a,b,c"    Override default extra wiki/ subfolders
  --force                          Overwrite existing vault content
  --upgrade                        Only fill missing .github/ files; never overwrite
  --seed <path>                    Copy a starter source into raw/<domain-default>/
  --dry-run                        Print plan, touch nothing on disk
  --detect-only                    Report vault state as JSON, exit
  --json-out                       Emit machine-readable JSON summary
  --templates <path>               Override templates dir (default: ~/.config/llm-wiki/templates)
  --help, -h                       Show this help and exit

Examples:
  scaffold.py --path ~/vaults/lotr --name "LOTR reading" \\
      --type reading --fiction --desc "Reading Tolkien" --lang english

  scaffold.py --path ~/vaults/my-proj --name "MyProj" \\
      --type development --desc "SaaS auth service" --lang english \\
      --seed ~/docs/spec.md

Karpathy pattern:
  raw/    is user-owned and immutable. The script only creates empty raw/
          subfolders. The optional --seed adds ONE starter source; existing
          raw/ content is never modified.
  wiki/   is LLM-owned. The script creates index.md, log.md, overview.md
          and leaves all content folders empty (populated by @wiki-maintainer
          at first /wiki-ingest).
"""


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def die(msg: str, code: int = 1, json_out: bool = False) -> None:
    """Emit error and exit."""
    if json_out:
        json.dump({"status": "error", "error": msg}, sys.stdout)
        sys.stdout.write("\n")
    else:
        sys.stderr.write(f"error: {msg}\n")
    sys.exit(code)


def substitute(text: str, mapping: Dict[str, str]) -> str:
    """Replace {{KEY}} placeholders with their mapped values."""
    for key, value in mapping.items():
        text = text.replace(key, value)
    return text


def get_templates_dir(override: Optional[str]) -> Path:
    if override:
        return Path(override).expanduser().resolve()
    env = os.environ.get(TEMPLATES_ENV)
    if env:
        return Path(env).expanduser().resolve()
    return DEFAULT_TEMPLATES


def validate_vault_path(vault: Path) -> None:
    """Refuse dangerous paths."""
    resolved = vault.resolve()
    if resolved == Path("/"):
        die("Refusing to scaffold at the filesystem root.")
    if resolved == Path.home():
        die("Refusing to scaffold at $HOME. Choose a subdirectory.")
    if ".." in vault.parts:
        die("Vault path may not contain '..'. Use an absolute path.")


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------


def detect_vault_state(vault: Path) -> Dict:
    """Classify the target: absent, existing_llm_wiki, or existing_non_wiki."""
    if not vault.exists():
        return {"state": "absent", "domain_type_hint": None, "hint_note": None}
    if vault.is_file():
        return {"state": "existing_non_wiki", "domain_type_hint": None,
                "hint_note": "path points to a file, not a directory"}
    try:
        is_empty = not any(vault.iterdir())
    except PermissionError:
        die(f"Cannot read {vault} (permission denied).")
    if is_empty:
        return {"state": "absent", "domain_type_hint": None, "hint_note": None}
    marker_file = vault / ".github" / "copilot-instructions.md"
    if marker_file.is_file():
        try:
            content = marker_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            content = ""
        if WIKI_MARKER in content:
            hint = detect_domain_hint(vault)
            return {"state": "existing_llm_wiki", "domain_type_hint": hint, "hint_note": None}
    hint = detect_domain_hint(vault)
    return {"state": "existing_non_wiki", "domain_type_hint": hint, "hint_note": None}


def detect_domain_hint(vault: Path) -> Optional[str]:
    """Heuristic domain suggestion from raw/ subfolder names."""
    raw = vault / "raw"
    if not raw.is_dir():
        return None
    try:
        subfolders = {d.name for d in raw.iterdir() if d.is_dir()}
    except OSError:
        return None
    # Priority order: most specific signal first.
    if "chapters" in subfolders:
        return "reading"  # subvariant remains user's choice
    if "specs" in subfolders or "tickets" in subfolders:
        return "development"
    if "papers" in subfolders or "research" in subfolders:
        return "research"
    if "journal" in subfolders:
        return "personal"
    if "customers" in subfolders or "competitors" in subfolders or "reports" in subfolders:
        return "business"
    if "courses" in subfolders or "exercises" in subfolders:
        return "learning"
    return None


# ---------------------------------------------------------------------------
# Type resolution
# ---------------------------------------------------------------------------


def resolve_type(base_type: str, fiction: bool, nonfiction: bool) -> str:
    """Map user-facing type + reading subvariant → internal DOMAIN_CONFIGS key."""
    if base_type == "reading":
        if fiction and nonfiction:
            die("--fiction and --nonfiction are mutually exclusive.")
        if not fiction and not nonfiction:
            sys.stderr.write(
                "warning: --type reading given without --fiction or --nonfiction; defaulting to --fiction.\n"
            )
            return "reading_fiction"
        return "reading_fiction" if fiction else "reading_nonfiction"
    if base_type in DOMAIN_CONFIGS:
        return base_type
    die(f"Unknown --type '{base_type}'. Valid: {', '.join(BASE_TYPES)}.")
    return ""  # unreachable


# ---------------------------------------------------------------------------
# Content generation for files that are not simple templates
# ---------------------------------------------------------------------------


def render_index(project_name: str, extra_wiki_folders: List[str], today: str) -> str:
    """Generate wiki/index.md content."""
    lines = [
        "---",
        "type: index",
        f"update_date: {today}",
        "---",
        "",
        f"# Wiki Index — {project_name}",
        "",
        "Quick links: [[overview]] · [[log]]",
        "",
        "## Entities",
        "",
        "| Page | Description | Last modified |",
        "|------|-------------|---------------|",
        "| _(empty)_ | | |",
        "",
        "## Concepts",
        "",
        "| Page | Description | Last modified |",
        "|------|-------------|---------------|",
        "| _(empty)_ | | |",
        "",
    ]
    for folder in extra_wiki_folders:
        heading = folder.replace("_", " ").capitalize()
        lines.extend([
            f"## {heading}",
            "",
            "| Page | Description | Last modified |",
            "|------|-------------|---------------|",
            "| _(empty)_ | | |",
            "",
        ])
    lines.extend([
        "## Sources",
        "",
        "| Page | Description | Last modified |",
        "|------|-------------|---------------|",
        "| _(empty)_ | | |",
        "",
        "## Analysis",
        "",
        "| Page | Description | Last modified |",
        "|------|-------------|---------------|",
        "| _(empty)_ | | |",
        "",
    ])
    return "\n".join(lines)


def render_log(project_name: str, raw_folders: List[str], extra_wiki_folders: List[str], today: str) -> str:
    """Generate wiki/log.md content with the init entry."""
    raw_list = ", ".join(raw_folders + ["assets"])
    wiki_extras = ", ".join(["entities", "concepts"] + extra_wiki_folders + ["sources", "analysis"])
    return (
        f"# Log — {project_name}\n"
        f"\n"
        f"## [{today}] init | Wiki creation\n"
        f"Pages created: [[overview]], [[index]]\n"
        f"Structure initialized: raw/ ({raw_list}), wiki/ ({wiki_extras})\n"
        f"Customization: .github/ (copilot-instructions.md, "
        f"instructions/wiki-conventions, agents/wiki-{{reader,maintainer,auditor}}, "
        f"prompts/wiki-{{ingest,lint}})\n"
    )


# ---------------------------------------------------------------------------
# File application (mode-aware writer)
# ---------------------------------------------------------------------------


class FileOp:
    """Record of one file write intent."""

    __slots__ = ("dest", "content", "kind", "protected_in_upgrade")

    def __init__(self, dest: Path, content: str, kind: str, protected_in_upgrade: bool = False):
        # kind: 'text' | 'gitkeep' | 'seed'
        self.dest = dest
        self.content = content
        self.kind = kind
        # protected_in_upgrade: files that --upgrade must never touch even if missing.
        # (Currently unused: --upgrade fills missing files by design; we keep the
        #  slot in case future decisions change.)
        self.protected_in_upgrade = protected_in_upgrade


def apply_file(op: FileOp, mode: str, dry_run: bool) -> str:
    """Return one of: 'created', 'overwritten', 'skipped-exists', 'skipped-upgrade-preserves'."""
    dest = op.dest
    exists = dest.exists()
    if exists:
        if mode == "force":
            status = "overwritten"
        elif mode == "upgrade":
            # In upgrade mode, never overwrite. Existing file wins.
            return "skipped-upgrade-preserves"
        else:  # fresh mode should not encounter existing files (detect_vault_state guards)
            return "skipped-exists"
    else:
        status = "created"
    if not dry_run:
        dest.parent.mkdir(parents=True, exist_ok=True)
        if op.kind == "seed":
            shutil.copy2(op.content, dest)  # content is source path in this case
        else:
            dest.write_text(op.content, encoding="utf-8")
    return status


# ---------------------------------------------------------------------------
# Plan construction
# ---------------------------------------------------------------------------


def build_plan(
    vault: Path,
    templates_dir: Path,
    config: Dict,
    mapping: Dict[str, str],
    raw_folders: List[str],
    extra_wiki_folders: List[str],
    today: str,
    project_name: str,
) -> Tuple[List[Path], List[FileOp]]:
    """Compute the deterministic set of directories and file operations."""
    dirs: List[Path] = [
        vault / "raw" / "assets",
        vault / "wiki" / "entities",
        vault / "wiki" / "concepts",
        vault / "wiki" / "sources",
        vault / "wiki" / "analysis",
        vault / ".github" / "instructions",
        vault / ".github" / "agents",
        vault / ".github" / "prompts",
    ]
    for f in raw_folders:
        dirs.append(vault / "raw" / f)
    for f in extra_wiki_folders:
        dirs.append(vault / "wiki" / f)

    ops: List[FileOp] = []

    # .gitkeep in each content folder that should stay empty at scaffold time.
    # NOTE: wiki/entities, wiki/concepts, wiki/sources, wiki/analysis, and
    # extra wiki folders stay empty per Karpathy pattern — populated later by
    # @wiki-maintainer. raw/ subfolders also stay empty for the user to fill.
    gitkeep_folders = [d for d in dirs if d.parent.name in ("raw", "wiki") or d.name in ("raw", "wiki")]
    for folder in gitkeep_folders:
        ops.append(FileOp(folder / ".gitkeep", "", "text"))

    # Root files.
    ops.append(FileOp(
        vault / "AGENTS.md",
        substitute((templates_dir / "AGENTS.md").read_text(encoding="utf-8"), mapping),
        "text",
    ))
    ops.append(FileOp(
        vault / ".gitignore",
        (templates_dir / "gitignore").read_text(encoding="utf-8"),
        "text",
    ))

    # .github/ tree.
    ops.append(FileOp(
        vault / ".github" / "copilot-instructions.md",
        substitute((templates_dir / "copilot-instructions.md").read_text(encoding="utf-8"), mapping),
        "text",
    ))
    ops.append(FileOp(
        vault / ".github" / "karpathy_llm_wiki_pattern.md",
        (templates_dir / "karpathy_llm_wiki_pattern.md").read_text(encoding="utf-8"),
        "text",
    ))
    ops.append(FileOp(
        vault / ".github" / "instructions" / "wiki-conventions.instructions.md",
        substitute(
            (templates_dir / "instructions" / "wiki-conventions.instructions.md").read_text(encoding="utf-8"),
            mapping,
        ),
        "text",
    ))
    for agent in ("wiki-reader.agent.md", "wiki-maintainer.agent.md", "wiki-auditor.agent.md"):
        ops.append(FileOp(
            vault / ".github" / "agents" / agent,
            substitute((templates_dir / "agents" / agent).read_text(encoding="utf-8"), mapping),
            "text",
        ))
    for prompt in ("wiki-ingest.prompt.md", "wiki-lint.prompt.md"):
        ops.append(FileOp(
            vault / ".github" / "prompts" / prompt,
            (templates_dir / "prompts" / prompt).read_text(encoding="utf-8"),
            "text",
        ))

    # wiki/ navigation files.
    overview_template = templates_dir / "overview" / config["overview_template"]
    if not overview_template.exists():
        die(f"Missing overview template: {overview_template}")
    ops.append(FileOp(
        vault / "wiki" / "overview.md",
        substitute(overview_template.read_text(encoding="utf-8"), mapping),
        "text",
    ))
    ops.append(FileOp(
        vault / "wiki" / "index.md",
        render_index(project_name, extra_wiki_folders, today),
        "text",
    ))
    ops.append(FileOp(
        vault / "wiki" / "log.md",
        render_log(project_name, raw_folders, extra_wiki_folders, today),
        "text",
    ))

    return dirs, ops


# ---------------------------------------------------------------------------
# Seed handling
# ---------------------------------------------------------------------------


def plan_seed(seed: Path, vault: Path, config: Dict, raw_folders: List[str]) -> FileOp:
    """Return a FileOp for the seed copy. Does NOT overwrite existing files in raw/."""
    if not seed.exists() or not seed.is_file():
        die(f"--seed: file not found: {seed}")
    subfolder = config["seed_default_subfolder"]
    if subfolder not in raw_folders:
        # Fall back to the first user-chosen raw folder, or 'assets'.
        subfolder = raw_folders[0] if raw_folders else "assets"
    dest = vault / "raw" / subfolder / seed.name
    if dest.exists():
        die(
            f"--seed: destination already exists ({dest}). "
            "Refusing to overwrite content in raw/ (Karpathy immutability rule)."
        )
    # We reuse FileOp with kind='seed' — 'content' field carries the source path.
    return FileOp(dest, str(seed), "seed")


# ---------------------------------------------------------------------------
# Output emission
# ---------------------------------------------------------------------------


def emit_json(payload: Dict) -> None:
    json.dump(payload, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


def emit_human(payload: Dict) -> None:
    status = payload.get("status")
    mode = payload.get("mode", "?")
    vault_path = payload.get("vault_path", "?")
    files_created = payload.get("files_created", [])
    files_skipped = payload.get("files_skipped", [])
    files_overwritten = payload.get("files_overwritten", [])
    seed_path_final = payload.get("seed_path_final")
    print(f"scaffold: {status} · mode={mode} · vault={vault_path}")
    print(
        f"  files: created={len(files_created)} "
        f"overwritten={len(files_overwritten)} "
        f"skipped={len(files_skipped)}"
    )
    if seed_path_final:
        print(f"  seed:  {seed_path_final}")
    if payload.get("warnings"):
        for w in payload["warnings"]:
            print(f"  warn:  {w}")


# ---------------------------------------------------------------------------
# Argparse
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(add_help=False, description="LLM Wiki Scaffolder")
    p.add_argument("--help", "-h", dest="help_only", action="store_true")
    p.add_argument("--path", dest="path")
    p.add_argument("--name", dest="name")
    p.add_argument("--type", dest="type", choices=BASE_TYPES)
    p.add_argument("--desc", dest="desc")
    p.add_argument("--lang", dest="lang", choices=["italian", "english"])
    p.add_argument("--fiction", dest="fiction", action="store_true")
    p.add_argument("--nonfiction", dest="nonfiction", action="store_true")
    p.add_argument("--raw-folders", dest="raw_folders")
    p.add_argument("--extra-wiki-folders", dest="extra_wiki_folders")
    p.add_argument("--force", dest="force", action="store_true")
    p.add_argument("--upgrade", dest="upgrade", action="store_true")
    p.add_argument("--seed", dest="seed")
    p.add_argument("--dry-run", dest="dry_run", action="store_true")
    p.add_argument("--detect-only", dest="detect_only", action="store_true")
    p.add_argument("--json-out", dest="json_out", action="store_true")
    p.add_argument("--templates", dest="templates")
    return p


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.help_only:
        sys.stdout.write(USAGE)
        return 0

    if not args.path:
        die("--path is required. Use --help for usage.", json_out=args.json_out)

    vault = Path(args.path).expanduser()
    if not vault.is_absolute():
        vault = (Path.cwd() / vault).resolve()
    validate_vault_path(vault)

    templates_dir = get_templates_dir(args.templates)
    if not templates_dir.is_dir():
        die(
            f"Templates directory not found: {templates_dir}. "
            "Run ./bin/install.sh from the llm-wiki-scaffolder repo.",
            json_out=args.json_out,
        )

    state_info = detect_vault_state(vault)

    # --detect-only: emit state and exit.
    if args.detect_only:
        emit_json({
            "status": "ok",
            "vault_path": str(vault),
            "state": state_info["state"],
            "domain_type_hint": state_info["domain_type_hint"],
            "hint_note": state_info["hint_note"],
        })
        return 0

    # Validate scaffold arguments.
    for req in ("name", "type", "desc", "lang"):
        if not getattr(args, req):
            die(f"--{req} is required.", json_out=args.json_out)

    if args.force and args.upgrade:
        die("--force and --upgrade are mutually exclusive.", json_out=args.json_out)

    # Determine mode.
    warnings: List[str] = []
    if state_info["state"] == "existing_llm_wiki":
        if args.force:
            mode = "force"
        elif args.upgrade:
            mode = "upgrade"
        else:
            die(
                "Vault already contains an LLM Wiki. "
                "Re-run with --upgrade (fill missing .github files) or --force (overwrite), "
                "or choose a different path.",
                code=2,
                json_out=args.json_out,
            )
    elif state_info["state"] == "existing_non_wiki":
        if args.force:
            mode = "force"
            warnings.append(f"path already contains non-wiki content; --force will overlay files")
        elif args.upgrade:
            die(
                "--upgrade requires an existing LLM Wiki at the target path. "
                "This path contains non-wiki content. Use --force to overlay or pick another path.",
                code=2,
                json_out=args.json_out,
            )
        else:
            die(
                "Target path is not empty and is not an LLM Wiki. "
                "Use --force to overlay, or pick an empty/non-existent path.",
                code=2,
                json_out=args.json_out,
            )
    else:
        mode = "fresh"

    # Resolve internal type and load config.
    internal_type = resolve_type(args.type, args.fiction, args.nonfiction)
    config = DOMAIN_CONFIGS[internal_type]

    raw_folders = (
        [f.strip() for f in args.raw_folders.split(",") if f.strip()]
        if args.raw_folders else config["raw_folders"]
    )
    extra_wiki_folders = (
        [f.strip() for f in args.extra_wiki_folders.split(",") if f.strip()]
        if args.extra_wiki_folders else config["extra_wiki_folders"]
    )

    today = date.today().isoformat()
    display_type = config["display_type"]
    extra_types_str = " | ".join(config["extra_page_types"]) if config["extra_page_types"] else "(none)"

    mapping = {
        "{{PROJECT_NAME}}": args.name,
        "{{DOMAIN_TYPE}}": display_type,
        "{{DOMAIN_DESCRIPTION}}": args.desc,
        "{{LANGUAGE}}": args.lang,
        "{{DOMAIN_EXTRA_TYPES}}": extra_types_str,
        "{{DOMAIN_SPECIFIC_CONVENTIONS}}": config["conventions"],
        "{{TODAY}}": today,
    }

    dirs, ops = build_plan(
        vault=vault,
        templates_dir=templates_dir,
        config=config,
        mapping=mapping,
        raw_folders=raw_folders,
        extra_wiki_folders=extra_wiki_folders,
        today=today,
        project_name=args.name,
    )

    seed_op: Optional[FileOp] = None
    if args.seed:
        seed_path = Path(args.seed).expanduser()
        seed_op = plan_seed(seed_path, vault, config, raw_folders)
        ops.append(seed_op)

    # Execute (or dry-run).
    files_created: List[str] = []
    files_overwritten: List[str] = []
    files_skipped: List[str] = []

    if not args.dry_run:
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    for op in ops:
        status = apply_file(op, mode, args.dry_run)
        rel = str(op.dest)
        if status == "created":
            files_created.append(rel)
        elif status == "overwritten":
            files_overwritten.append(rel)
        else:
            files_skipped.append(rel)

    payload = {
        "status": "ok",
        "mode": mode,
        "vault_path": str(vault),
        "domain_type": args.type,
        "internal_type": internal_type,
        "language": args.lang,
        "raw_folders": raw_folders,
        "extra_wiki_folders": extra_wiki_folders,
        "files_created": files_created,
        "files_overwritten": files_overwritten,
        "files_skipped": files_skipped,
        "seed_path_final": str(seed_op.dest) if seed_op else None,
        "dry_run": args.dry_run,
        "warnings": warnings,
    }

    if args.json_out:
        emit_json(payload)
    else:
        emit_human(payload)

    return 0


if __name__ == "__main__":
    sys.exit(main())
