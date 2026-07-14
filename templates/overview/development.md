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
| Decisions | 0 |
| Requirements | 0 |
| Analyses | 0 |

## How to use this wiki

- **INGEST** — add a source under `raw/` (e.g. `raw/specs/auth.md`) then run:
  ```
  /wiki-ingest raw/specs/auth.md
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

## Project description

_Short description of what this project builds and its current phase._

## Main entities

_Key modules, services, components, actors. Populated by `@wiki-maintainer` as specs and meetings are ingested._

## Open architectural decisions

_Decisions under discussion or pending. Once settled, they migrate to `wiki/decisions/` as ADR-style pages._

## High-level requirements

_Functional and non-functional requirements at the epic level. Detailed requirements live under `wiki/requirements/`._

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
