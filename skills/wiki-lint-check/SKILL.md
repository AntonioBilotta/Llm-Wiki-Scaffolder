---
name: wiki-lint-check
description: Run 9 health-check audits on an LLM Wiki vault — contradictions, orphan pages, missing cross-references, stale claims, missing pages, knowledge gaps, frontmatter integrity, source fidelity (a bundled script greps numbers, dates and quotes back in the raw files), and link integrity (a bundled script finds duplicate page names that make `[[wikilinks]]` ambiguous, and broken wikilinks). Returns a structured report. Dual output - JSON by default (composable with downstream repair actions), Markdown if `format=md` (human-readable). Read-only; the caller applies repairs. Use for periodic health checks, at the end of batch ingest, or when the user asks 'lint the wiki', 'check wiki health', 'audit the wiki', 'find contradictions in the wiki'.
argument-hint: "[format=<json|md>] [scope=<vault|pages:comma-separated>] [vault_path=<absolute path>]"
user-invocable: false
---

# wiki-lint-check

Produce a Lint Report by running 9 checks over the vault: seven by reasoning, two mechanical (bundled scripts). No writes.

## Algorithm

1. **Resolve `vault_path`** — required argument, passed by the calling workflow (`wiki-ingest`, `wiki-query`, `wiki-lint`, or a vault agent). If you are invoked directly without it, resolve it with the rule in step 1 of the `wiki-ingest` Preflight: argument → `## Vault` signpost in context (`.github/copilot-instructions.md` or `AGENTS.md`) → current folder if it is a vault root → ask the user.

2. **Determine scope:**
   - `scope=vault` (default) — every markdown file under `<vault_path>/wiki/` except `index.md`, `log.md`, `overview.md`.
   - `scope=pages:name1,name2,...` — only the listed pages. Full-scope checks (orphans, coverage gaps) still evaluate the whole vault to preserve correctness; per-page checks (contradictions on this page, frontmatter of this page) restrict to the listed pages.

3. **Run 9 checks** in order:

   1. **Contradictions** — for each factual claim in scope, look for another page that directly contradicts it. Flag with page-pair references.
   2. **Orphans** — pages with zero inbound `[[wikilinks]]` from any other page (excluding index/log/overview).
   3. **Missing cross-references** — for each page in scope, scan its body for mentions of known entity/concept/domain-item names that lack the corresponding `[[wikilink]]`. Only flag proposals where the target page name is unambiguous.
   4. **Stale claims** — sort `wiki/sources/` by `source_date` ascending (fallback to `creation_date` if `source_date` is missing). For each older claim referenced across pages, check whether a newer source contradicts or supersedes it. Flag with the specific pages and the newer source.
   5. **Missing pages** — entities/concepts/domain items mentioned frequently (≥3 mentions across pages) but lacking their own page.
   6. **Knowledge gaps** — topics with thin coverage: fewer than 2 sources touching, or fewer than 2 cross-links to other pages.
   7. **Frontmatter integrity** — for each page in scope, verify required fields: `type`, `creation_date`, `update_date`. For missing `update_date`, mark `auto_repairable: true` with `proposed_fix: <today YYYY-MM-DD>`. For missing `type` or `creation_date`, mark `auto_repairable: false` (needs user judgment). Also validate `related_sources` are actual pages (not broken links).

   8. **Source fidelity** (mechanical, then judged) — run the bundled script via the platform terminal tool (`<skill-dir>` is the directory containing this SKILL.md; on Windows use `python` or `py -3` if `python3` is not on PATH):

      ```bash
      python3 <skill-dir>/scripts/check_evidence.py --vault-path "<vault_path>" [--pages "name1,name2"]
      ```

      Pass `--pages` only when `scope=pages:...`. The script prints JSON and always exits 0. It follows each page to its evidence (`related_sources` and inline `[[source]]` links → the source page's `- **Provenance**:` path → the raw file) and reports:
      - `fidelity` — specific numbers (`10,000`, `3.14`, `42K`, `99.9%`, 4+ digits), ISO dates and quotes of 15+ characters that do **not** appear verbatim in the linked raw files. These are **suspects, not verdicts**: open the raw file and drop the ones that are legitimate (a derived value whose components are shown, a product name, a date in a Stale callout that comes from a newer source). Report only real mismatches, with the raw context.
      - `evidence_errors` — pages that cannot be verified: `no_sources`, `related_source_not_found`, `no_provenance`, `provenance_not_found`, `provenance_outside_raw`, `ambiguous_page_name`. `ambiguous_page_name` is a symptom of a duplicate page name: report it here only as a pointer ("see Link integrity"); the files and the affected links belong to check 9.
      - `unverifiable` — the evidence is not plain text (PDF, image, Office file). Suggest keeping a Markdown extraction next to it in `raw/`.
      - `unreferenced_raw` — raw files no source page points to (ingest backlog). Files logged as `ingest | no material: raw/<path>` are excluded.

      Never auto-fix any of these: facts are the maintainer's call.

   9. **Link integrity** (mechanical) — Obsidian resolves a bare `[[name]]` by file name across the whole vault, so two pages with the same name in different folders make every bare link to that name ambiguous (Obsidian silently picks one, and so does `check_evidence.py`). Run the second bundled script the same way:

      ```bash
      python3 <skill-dir>/scripts/check_links.py --vault-path "<vault_path>" [--pages "name1,name2"]
      ```

      Pass `--pages` only when `scope=pages:...`. The script prints JSON and always exits 0. It reports:
      - `duplicate_basenames` — each page name (case-insensitive, as Obsidian treats it) held by two or more files under `wiki/`, with their `paths` and `ambiguous_links_from`: the pages that link to it with a bare `[[name]]`. Path-qualified links (`[[folder/name]]`) are not ambiguous and are not listed. Always computed over the whole vault; `--pages` only narrows `ambiguous_links_from`.
      - `broken_links` — wikilinks and embeds (frontmatter included) whose target matches no file in the vault (`.obsidian/` and other dot-folders excluded). Links inside fenced or inline code are ignored.

      Never rename or relink automatically: the fix is a design choice. Propose the two options and let the maintainer pick — (a) rename one set of pages with a distinguishing prefix or suffix and update the links, or (b) keep the names and qualify every link with its folder (`[[hats/red_hat]]`). For a broken link, say whether the target looks like a typo of an existing page (name it) or a page still to be written (cross-check with check 5).

4. **Format output** per `format` argument.

## Return value — JSON (default)

```yaml
version: 1
scope: <"vault" | list of pages>
checked: <count of pages inspected>
findings:
  contradictions:
    - pages: [<name>, <name>]
      detail: <string>
  orphans: [<page name>, ...]
  missing_xrefs:
    - page: <name>
      mentioned_but_unlinked: [<target>, ...]
  stale:
    - page: <name>
      superseded_by: <newer source name>
      detail: <string>
  missing_pages: [<name>, ...]
  knowledge_gaps: [<topic>, ...]
  frontmatter:
    - page: <name>
      issue: <string>
      auto_repairable: <bool>
      proposed_fix: <string or null>
  fidelity:                       # only suspects confirmed after judging the script output
    - page: <name>
      value: <literal as written on the page>
      kind: number | date | quote
      raw: <raw file checked>
      detail: <what the raw file says instead, or "not found">
  evidence_errors:
    - page: <name>
      issue: <script issue code>
      detail: <string>
  unverifiable: [{page: <name>, raw: <path>}]
  unreferenced_raw: [<vault-relative raw path>, ...]
  duplicate_basenames:
    - name: <page name>
      paths: [<vault-relative path>, ...]
      ambiguous_links_from: [<vault-relative path>, ...]
  broken_links:
    - page: <vault-relative path>
      targets: [<link target as written>, ...]
summary:
  total_findings: <int>
  auto_repairable: <int>
  needs_user_approval: <int>
```

## Return value — Markdown (if `format=md`)

A human-readable Lint Report with 9 sections (one per check; the source-fidelity section also lists evidence errors, unverifiable sources and the unreferenced-raw backlog) plus a summary footer. In the link-integrity section give each duplicate name one bullet with its files and the number of ambiguous links (list the linking pages only when there are 10 or fewer), then the broken links. Same information as the JSON, but formatted for human reading. Each finding is a bullet with the page name and issue detail.

Example section:

```markdown
## Frontmatter integrity

- `entity_foo` — missing `update_date` (auto-repairable → 2026-07-22)
- `concept_bar` — missing `type` field (needs user approval)
```

## Constraints

- **Read-only.** Never modify any wiki page. Repairs are the caller's job — the `wiki-lint` workflow applies them with the platform file-edit tool after reading this skill's JSON output. Both bundled scripts are read-only too. Link-integrity findings are never auto-repairable: count them under `needs_user_approval`.
- **Deterministic ordering.** Within each section, sort findings by page name.
- If `wiki/` is empty (fresh scaffold), return zero findings with a `note` field.
- If `format` is any value other than `json` or `md`, default to `json` and add a `warning` field.

## Gotchas

- The 9 checks are sequential; checks 8 and 9 are scripts and take seconds even on large vaults. Total runtime scales roughly linearly with vault size. For very large vaults (>500 pages), pass `scope=pages:name1,name2,...` to limit per-page checks (full-scope checks like orphans still evaluate the whole vault).
- Auto-repairable frontmatter fixes are ONLY for missing/invalid `update_date` — the fix proposes today's date. Missing `type` or `creation_date` always require user approval since the correct value is not inferrable.
- Fidelity suspects that the script cannot see: small plain integers (`42`, `500`), spelled-out dates, currencies, paraphrased claims. Those stay under the write-time source-fidelity rule and check 1 (contradictions).
- Contradiction detection is heuristic and produces some false positives on similarly-worded but distinct claims. Treat the output as "pages to review", not "pages guaranteed wrong".
- Orphan detection excludes `index.md`, `log.md`, and `overview.md` (which are structurally always "orphaned"). All other pages under `wiki/` are candidates.
- The Markdown output (`format=md`) contains the same information as the JSON but is not intended for programmatic parsing — use JSON for automation.
- Duplicate page names usually come from mirroring one subject in two folders (a concept in `hats/` and its implementation in `agents/`). One naming choice can make dozens of links ambiguous: report one finding per name, not one per link.
