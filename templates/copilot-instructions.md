# {{PROJECT_NAME}}

**Type:** {{DOMAIN_TYPE}}
**Description:** {{DOMAIN_DESCRIPTION}}

This workspace contains an **LLM Wiki** — a persistent, LLM-maintained knowledge base following the [Karpathy pattern](./karpathy_llm_wiki_pattern.md).

## Layout

- `raw/` — **immutable** source material. Only the user writes here. **Never** modify anything under `raw/`.
- `wiki/` — LLM-maintained markdown (entities, concepts, sources, analysis, plus domain-specific folders, and the navigation files `index.md`, `log.md`, `overview.md`).

## Commands

- `/wiki-ingest <path>` — ingest a source (single file or folder) into the wiki.
- `/wiki-lint` — health-check the wiki (contradictions, orphans, stale claims, coverage gaps).
- `@wiki-reader "question"` — query the wiki with an open question.

The three underlying roles are:

- `@wiki-maintainer` — reads `raw/`, writes `wiki/`, handles single and batch ingest.
- `@wiki-reader` — read-only, answers questions with citations, optionally archives substantive answers in `wiki/analysis/`.
- `@wiki-auditor` — health-checks the wiki; may repair frontmatter but never edits page content.

## Conventions

Formatting rules (YAML frontmatter, `snake_case`, Obsidian callouts, `[[wikilink]]`, domain-specific conventions) live in [`.github/instructions/wiki-conventions.instructions.md`](./instructions/wiki-conventions.instructions.md). They are auto-loaded by VS Code Copilot when working on any file under `wiki/**` or `raw/**` — you do not need to reference them explicitly.

## Reference

- Original pattern: [`karpathy_llm_wiki_pattern.md`](./karpathy_llm_wiki_pattern.md) (copied into this vault so it stays available even outside the parent workspace).
