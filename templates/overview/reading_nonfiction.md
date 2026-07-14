---
type: overview
creation_date: {{TODAY}}
update_date: {{TODAY}}
related_sources: []
tags: []
---

# Overview — {{PROJECT_NAME}}

**Type:** {{DOMAIN_TYPE}} · **Description:** {{DOMAIN_DESCRIPTION}}

## Knowledge state

| Metric | Count |
|--------|-------|
| Sources (chapters) | 0 |
| Authors cited | 0 |
| Arguments tracked | 0 |
| Analyses | 0 |
| Reading progress | 0% |

## How to use this wiki

- **INGEST** — after reading a chapter or section, drop your notes under `raw/chapters/` then run:
  ```
  /wiki-ingest raw/chapters/ch_01.md
  ```
- **QUERY** — ask a question, get a cited answer:
  ```
  @wiki-reader "your question"
  ```
- **LINT** — periodic health-check:
  ```
  /wiki-lint
  ```

Any evolution of structure (new page types, new folders, new conventions) must be documented in `.github/instructions/wiki-conventions.instructions.md`. The root `copilot-instructions.md` stays a signpost — do not grow it.

## Work

- **Title:** _fill after first ingest_
- **Author:** _fill after first ingest_
- **Genre:** non-fiction

## Structure

_Parts, chapters, appendices as the reading progresses. Populated by `@wiki-maintainer` on ingest._

## Authors cited

_Authors and thinkers referenced by the work. Each has its own page under `wiki/authors/`._

## Arguments

_Central claims and lines of reasoning. Each argument has its own page under `wiki/arguments/`, tracking premises, evidence, and objections._

## Reading progress

_Which chapters have been ingested; current position in the work._

## Suggested first questions

_To be populated by the LLM after scaffold with 4–5 seed questions specific to `{{PROJECT_NAME}}`._

## God pages

_High-centrality hub pages in the wiki graph. Populated by `@wiki-auditor` at the first `/wiki-lint` pass._

## Git & team

This vault is a plain git repo of markdown files. To start versioning:

```
git init && git add . && git commit -m "init llm wiki"
```

The included `.gitignore` excludes Obsidian cache/workspace files and OS junk (`.DS_Store`, `Thumbs.db`). Everything else — including `.obsidian/` settings, `raw/`, and `wiki/` — is committed by default.
