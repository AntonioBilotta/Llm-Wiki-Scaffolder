---
description: "Run a full health-check on the LLM Wiki: contradictions, orphans, missing cross-references, stale claims, coverage gaps, frontmatter integrity. Produces a Lint Report. Only unambiguous frontmatter fixes are auto-applied; content changes and deletions are flagged for user approval. Delegates to @wiki-auditor."
agent: "wiki-auditor"
---

Run a full LINT pass on the LLM Wiki. Follow the 7-step checklist defined in your agent instructions and produce a markdown Lint Report.

- Auto-repair only unambiguous frontmatter issues (e.g. missing `update_date` → today).
- Flag all proposed content changes, deletions, and additions for user approval.
- Append the standard `## [YYYY-MM-DD] lint | Maintenance pass` entry to `wiki/log.md` when done.
