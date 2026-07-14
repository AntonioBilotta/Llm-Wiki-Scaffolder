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
| Characters | 0 |
| Themes | 0 |
| Analyses | 0 |
| Reading progress | 0% |

## How to use this wiki

- **INGEST** — after reading a chapter, drop your notes under `raw/chapters/` (e.g. `raw/chapters/ch_01.md`) then run:
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
- **Genre:** fiction

## Structure

_Volumes, parts, chapters as the reading progresses. Populated by `@wiki-maintainer` on ingest._

## Main characters

_Characters introduced so far, with brief traits. Each has its own page under `wiki/characters/`._

## Emerging themes

_Themes surfaced across chapters. Each has its own page under `wiki/themes/`._

## Reading progress

_Which chapters have been ingested; current position in the work._

> [!important] Spoiler discipline
> Wiki pages should reflect only the reader's current state of knowledge. Do not add information from chapters not yet ingested. If a later revelation retroactively changes an earlier fact, flag it with `> [!warning] Retcon: <detail>` and cite the chapter where the revelation occurs.

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
