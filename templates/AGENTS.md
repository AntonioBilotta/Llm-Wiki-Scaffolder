# {{PROJECT_NAME}}

**Type:** {{DOMAIN_TYPE}}
**Description:** {{DOMAIN_DESCRIPTION}}

This vault is an **LLM Wiki** following the [Karpathy pattern](.github/karpathy_llm_wiki_pattern.md). This file is a bridge for coding assistants other than VS Code Copilot (e.g. Codex, OpenCode, Aider, Cursor) that read `AGENTS.md` at the repo root. Copilot users see the equivalent signpost at `.github/copilot-instructions.md`.

## Layout

- `raw/` — **immutable** source material. Only the user writes here. **Never** modify anything under `raw/`.
- `wiki/` — LLM-maintained markdown: `entities/`, `concepts/`, `sources/`, `analysis/`, plus domain-specific folders, and the navigation files `index.md`, `log.md`, `overview.md`.
- `.github/` — schema and roles (see below).

## Roles and operations

Three roles, defined in detail under `.github/agents/`:

- **`wiki-maintainer`** — INGEST. Reads `raw/`, writes `wiki/`. Handles single and batch ingest.
- **`wiki-reader`** — QUERY. Read-only. Answers questions with `[[wikilink]]` citations. May archive substantive answers under `wiki/analysis/`.
- **`wiki-auditor`** — LINT. Health-checks the wiki. May repair frontmatter but never edits page content.

Three operations: **INGEST** (add a source), **QUERY** (ask a question), **LINT** (health-check).

## Conventions

Formatting rules — YAML frontmatter, `snake_case` file names, Obsidian syntax (`[[wikilink]]`, callouts), cross-reference discipline, and the `raw/` immutability rule — live in `.github/instructions/wiki-conventions.instructions.md`.

## Reference

Full pattern description in `.github/karpathy_llm_wiki_pattern.md` (copied into this vault at creation time so it stays available offline and version-pinned).
