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
| Sources (meetings / reports / calls) | 0 |
| People tracked | 0 |
| Processes | 0 |
| Initiatives | 0 |
| Open decisions | 0 |
| Analyses | 0 |

## How to use this wiki

- **INGEST** — drop a meeting transcript, report, or customer-call note under `raw/` then run:
  ```
  /wiki-ingest raw/meetings/2026-07-14_sync.md
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

## Company context

_What the team/company does, current phase, key priorities. Fill this in before the first ingest._

## Main stakeholders

_Internal people, customers, competitors, partners. Each has its own page under `wiki/people/`._

## Ongoing initiatives

_Active projects and workstreams. Each has its own page under `wiki/initiatives/` with status, owner, and related sources._

## Open decisions

_Decisions currently under discussion or recently resolved. Kept in-place with status; no migration to a separate folder._

## Suggested first questions

_To be populated by the LLM after scaffold with 4–5 seed questions specific to `{{PROJECT_NAME}}`._

## God pages

_High-centrality hub pages in the wiki graph. Populated by `@wiki-auditor` at the first `/wiki-lint` pass._

## Git & team

This vault is a plain git repo of markdown files. To start versioning (recommend a **private** remote for internal knowledge):

```
git init && git add . && git commit -m "init llm wiki"
```

The included `.gitignore` excludes Obsidian cache/workspace files and OS junk (`.DS_Store`, `Thumbs.db`). Everything else — including `.obsidian/` settings, `raw/`, and `wiki/` — is committed by default.
