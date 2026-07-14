---
description: "Ingest a source (single file or a folder) from `raw/` into the LLM Wiki. Delegates to @wiki-maintainer. Folder mode batches all sources in chronological order and runs a lint pass at the end."
argument-hint: "<path under raw/, e.g. raw/specs/auth.md or raw/specs/>"
agent: "wiki-maintainer"
---

Ingest the source at `${input:source_path}` into the wiki.

- If `${input:source_path}` is a single file: follow the single-source INGEST workflow (steps 1–8) defined in your agent instructions.
- If `${input:source_path}` is a folder: follow **batch mode** — enumerate sources under the folder, order them chronologically (by source `date` frontmatter if present, otherwise filesystem `mtime`, oldest first), process each with the single-source workflow, then invoke `@wiki-auditor` at the end to run a lint pass on the touched pages.

When done, report a brief summary: created pages, updated pages, contradictions flagged, and (in batch mode) the auditor's findings.
