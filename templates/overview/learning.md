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
| Sources (lessons / references) | 0 |
| Topics covered | 0 |
| Exercises done | 0 |
| Flashcards | 0 |
| Analyses | 0 |
| Progress | 0% |

## How to use this wiki

- **INGEST** — drop lecture notes, exercise solutions, or references under `raw/` then run:
  ```
  /wiki-ingest raw/courses/lesson_01.md
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

## Course or subject

_What is being studied, at what level, and via which primary materials._

## Learning objectives

_What "done" looks like. Skills to acquire, concepts to master._

## Key concepts

_Central concepts of the subject. Each has its own page under `wiki/concepts/` or `wiki/topics/` with definition, examples, and related sources._

## Progress

_Which lessons/chapters have been ingested; exercises attempted; current position._

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
