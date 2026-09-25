---
name: wiki-lint-check
description: Run 8 health-check audits on an LLM Wiki vault — contradictions, orphan pages, missing cross-references, stale claims, missing pages, knowledge gaps, frontmatter integrity, and source fidelity (a bundled script greps numbers, dates and quotes back in the raw files). Returns a structured report. Dual output - JSON by default (composable with downstream repair actions), Markdown if `format=md` (human-readable). Read-only; the caller applies repairs. Use for periodic health checks, at the end of batch ingest, or when the user asks 'lint the wiki', 'check wiki health', 'audit the wiki', 'find contradictions in the wiki'.
argument-hint: "[format=<json|md>] [scope=<vault|pages:comma-separated>] [vault_path=<absolute path>]"
user-invocable: false
---

# wiki-lint-check

Produce a Lint Report by running 8 checks over the vault: seven by reasoning, one mechanical (bundled script). No writes.

## Algorithm

1. **Resolve `vault_path`** — required argument, passed by the calling workflow (`wiki-ingest`, `wiki-query`, `wiki-lint`, or a vault agent). If you are invoked directly without it, resolve it with the rule in step 1 of the `wiki-ingest` Preflight: argument → `## Vault` signpost in context (`.github/copilot-instructions.md` or `AGENTS.md`) → current folder if it is a vault root → ask the user.

2. **Determine scope:**
   - `scope=vault` (default) — every markdown file under `<vault_path>/wiki/` except `index.md`, `log.md`, `overview.md`.
   - `scope=pages:name1,name2,...` — only the listed pages. Full-scope checks (orphans, coverage gaps) still evaluate the whole vault to preserve correctness; per-page checks (contradictions on this page, frontmatter of this page) restrict to the listed pages.

3. **Run 8 checks** in order:

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
      - `evidence_errors` — pages that cannot be verified: `no_sources`, `related_source_not_found`, `no_provenance`, `provenance_not_found`, `provenance_outside_raw`, `ambiguous_page_name`.
      - `unverifiable` — the evidence is not plain text (PDF, image, Office file). Suggest keeping a Markdown extraction next to it in `raw/`.
      - `unreferenced_raw` — raw files no source page points to (ingest backlog). Files logged as `ingest | no material: raw/<path>` are excluded.

      Never auto-fix any of these: facts are the maintainer's call.


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
summary:
  total_findings: <int>
  auto_repairable: <int>
  needs_user_approval: <int>
```

## Return value — Markdown (if `format=md`)

A human-readable Lint Report with 8 sections (one per check; the source-fidelity section also lists evidence errors, unverifiable sources and the unreferenced-raw backlog) plus a summary footer. Same information as the JSON, but formatted for human reading. Each finding is a bullet with the page name and issue detail.

Example section:

```markdown
## Frontmatter integrity

- `entity_foo` — missing `update_date` (auto-repairable → 2026-07-22)
- `concept_bar` — missing `type` field (needs user approval)
```

## Constraints

- **Read-only.** Never modify any wiki page. Repairs are the caller's job — the `wiki-lint` workflow applies them with the platform file-edit tool after reading this skill's JSON output. The bundled script is read-only too.
- **Deterministic ordering.** Within each section, sort findings by page name.
- If `wiki/` is empty (fresh scaffold), return zero findings with a `note` field.
- If `format` is any value other than `json` or `md`, default to `json` and add a `warning` field.

## Gotchas

- The 8 checks are sequential; check 8 is a script and takes seconds even on large vaults. Total runtime scales roughly linearly with vault size. For very large vaults (>500 pages), pass `scope=pages:name1,name2,...` to limit per-page checks (full-scope checks like orphans still evaluate the whole vault).
- Auto-repairable frontmatter fixes are ONLY for missing/invalid `update_date` — the fix proposes today's date. Missing `type` or `creation_date` always require user approval since the correct value is not inferrable.
- Fidelity suspects that the script cannot see: small plain integers (`42`, `500`), spelled-out dates, currencies, paraphrased claims. Those stay under the write-time source-fidelity rule and check 1 (contradictions).
- Contradiction detection is heuristic and produces some false positives on similarly-worded but distinct claims. Treat the output as "pages to review", not "pages guaranteed wrong".
- Orphan detection excludes `index.md`, `log.md`, and `overview.md` (which are structurally always "orphaned"). All other pages under `wiki/` are candidates.
- The Markdown output (`format=md`) contains the same information as the JSON but is not intended for programmatic parsing — use JSON for automation.
