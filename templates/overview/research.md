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
| Sources | 0 |
| Entity pages | 0 |
| Concept pages | 0 |
| Findings | 0 |
| Open questions | 0 |
| Analyses | 0 |

## How to use this wiki

- **INGEST** — add a source under `raw/` (e.g. `raw/research/paper.pdf`) then run:
  ```
  /wiki-ingest raw/research/paper.pdf
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

## Research question

_What is the central question this research aims to answer? Fill this in before the first ingest._

## Corpus

_Kinds of sources being collected: papers, articles, reports, datasets. Populated by `@wiki-maintainer` as sources are ingested._

## Emerging hypotheses

_Working hypotheses that the corpus supports so far. Updated on ingest._

## Knowledge gaps

_Questions the corpus does not yet answer. Populated by `@wiki-auditor` during lint passes._

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
