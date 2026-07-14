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
| Sources (journal / articles / podcasts) | 0 |
| Active goals | 0 |
| Recurring patterns | 0 |
| Reflections | 0 |
| Analyses | 0 |

## How to use this wiki

- **INGEST** — drop a journal entry, article, or podcast note under `raw/` then run:
  ```
  /wiki-ingest raw/journal/2026-07-14.md
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

## Life areas tracked

_Health, career, relationships, finances, creative work, learning. Adjust to what you actually track._

## Active goals

_Goals currently being pursued. Each has its own page under `wiki/goals/` with status, milestones, and related sources._

## Recurring patterns

_Behavioral or emotional patterns observed across journal entries. Each has its own page under `wiki/patterns/`._

## Key insights

_Reflections and syntheses. Each has its own page under `wiki/reflections/`._

> [!important] Sensitive data
> This wiki may contain personal or sensitive information. Do not commit to a public git repo without review. Consider a local-only workflow or a private repo.

## Suggested first questions

_To be populated by the LLM after scaffold with 4–5 seed questions specific to `{{PROJECT_NAME}}`._

## God pages

_High-centrality hub pages in the wiki graph. Populated by `@wiki-auditor` at the first `/wiki-lint` pass._

## Git & team

This vault is a plain git repo of markdown files. To start versioning (recommend a **private** remote):

```
git init && git add . && git commit -m "init llm wiki"
```

The included `.gitignore` excludes Obsidian cache/workspace files and OS junk (`.DS_Store`, `Thumbs.db`). Everything else — including `.obsidian/` settings, `raw/`, and `wiki/` — is committed by default.
