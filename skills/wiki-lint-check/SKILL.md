---
name: wiki-lint-check
description: Run 7 health-check audits on an LLM Wiki vault — contradictions, orphan pages, missing cross-references, stale claims, missing pages, knowledge gaps, and frontmatter integrity. Returns a structured report. Dual output - JSON by default (composable with downstream repair actions), Markdown if `format=md` (human-readable). Read-only; the caller applies repairs. Use for periodic health checks, at the end of batch ingest, or when the user asks 'lint the wiki', 'check wiki health', 'audit the wiki', 'find contradictions in the wiki'.
argument-hint: "[format=<json|md>] [scope=<vault|pages:comma-separated>] [vault_path=<absolute path>]"
user-invocable: false
---

# wiki-lint-check

Produce a Lint Report by running 7 checks over the vault. No writes.

## Algorithm

1. **Resolve `vault_path`** (from `vault_path` argument, required — read from the workspace's `.github/copilot-instructions.md` under `## Vault / **Path:**`).

2. **Determine scope:**
   - `scope=vault` (default) — every markdown file under `<vault_path>/wiki/` except `index.md`, `log.md`, `overview.md`.
   - `scope=pages:name1,name2,...` — only the listed pages. Full-scope checks (orphans, coverage gaps) still evaluate the whole vault to preserve correctness; per-page checks (contradictions on this page, frontmatter of this page) restrict to the listed pages.

3. **Run 7 checks** in order:

   1. **Contradictions** — for each factual claim in scope, look for another page that directly contradicts it. Flag with page-pair references.
   2. **Orphans** — pages with zero inbound `[[wikilinks]]` from any other page (excluding index/log/overview).
   3. **Missing cross-references** — for each page in scope, scan its body for mentions of known entity/concept/domain-item names that lack the corresponding `[[wikilink]]`. Only flag proposals where the target page name is unambiguous.
   4. **Stale claims** — sort `wiki/sources/` by `creation_date` ascending. For each older claim referenced across pages, check whether a newer source contradicts or supersedes it. Flag with the specific pages and the newer source.
   5. **Missing pages** — entities/concepts/domain items mentioned frequently (≥3 mentions across pages) but lacking their own page.
   6. **Knowledge gaps** — topics with thin coverage: fewer than 2 sources touching, or fewer than 2 cross-links to other pages.
   7. **Frontmatter integrity** — for each page in scope, verify required fields: `type`, `creation_date`, `update_date`. For missing `update_date`, mark `auto_repairable: true` with `proposed_fix: <today YYYY-MM-DD>`. For missing `type` or `creation_date`, mark `auto_repairable: false` (needs user judgment). Also validate `related_sources` are actual pages (not broken links).

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
summary:
  total_findings: <int>
  auto_repairable: <int>
  needs_user_approval: <int>
```

## Return value — Markdown (if `format=md`)

A human-readable Lint Report with 7 sections (one per check) plus a summary footer. Same information as the JSON, but formatted for human reading. Each finding is a bullet with the page name and issue detail.

Example section:

```markdown
## Frontmatter integrity

- `entity_foo` — missing `update_date` (auto-repairable → 2026-07-22)
- `concept_bar` — missing `type` field (needs user approval)
```

## Constraints

- **Read-only.** Never modify any wiki page. Repairs are the caller's job — the `/wiki-lint` prompt orchestrates them via the platform `edit` tool after reading this skill's JSON output.
- **Deterministic ordering.** Within each section, sort findings by page name.
- If `wiki/` is empty (fresh scaffold), return zero findings with a `note` field.
- If `format` is any value other than `json` or `md`, default to `json` and add a `warning` field.

## Gotchas

- The 7 checks are sequential. Total runtime scales roughly linearly with vault size. For very large vaults (>500 pages), pass `scope=pages:name1,name2,...` to limit per-page checks (full-scope checks like orphans still evaluate the whole vault).
- Auto-repairable frontmatter fixes are ONLY for missing/invalid `update_date` — the fix proposes today's date. Missing `type` or `creation_date` always require user approval since the correct value is not inferrable.
- Contradiction detection is heuristic and produces some false positives on similarly-worded but distinct claims. Treat the output as "pages to review", not "pages guaranteed wrong".
- Orphan detection excludes `index.md`, `log.md`, and `overview.md` (which are structurally always "orphaned"). All other pages under `wiki/` are candidates.
- The Markdown output (`format=md`) contains the same information as the JSON but is not intended for programmatic parsing — use JSON for automation.
