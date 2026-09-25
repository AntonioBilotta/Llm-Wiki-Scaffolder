# {{PROJECT_NAME}}

**Type:** {{DOMAIN_TYPE}}
**Description:** {{DOMAIN_DESCRIPTION}}

This vault is an **LLM Wiki** following the [Karpathy pattern](.github/karpathy_llm_wiki_pattern.md). This file is the signpost for assistants other than VS Code Copilot: Claude Code loads it through the vault's `CLAUDE.md`, and Codex, OpenCode, Aider and Cursor read `AGENTS.md` at the repo root directly. Copilot users see the equivalent signpost at `.github/copilot-instructions.md`.

## Vault

- **Path:** `{{VAULT_PATH}}`
- **Type:** `{{DOMAIN_TYPE}}`

> **Note for LLMs orchestrating wiki-* skills:** the path above is the `vault_path` to pass to every wiki-* skill. If that absolute path does not exist in your environment (vault opened from another machine, a mounted folder, a cloud session), use the directory containing this file instead — `AGENTS.md` sits at the vault root. Do not walk the filesystem looking for other vaults.

## Layout

- `raw/` — **immutable** source material. Only the user writes here. **Never** modify anything under `raw/`.
- `wiki/` — LLM-maintained markdown: `entities/`, `concepts/`, `sources/`, `analysis/`, plus domain-specific folders, and the navigation files `index.md`, `log.md`, `overview.md`.
- `.github/` — schema and roles (see below).

## Operations

Three operations: **INGEST** (add a source), **QUERY** (ask a question), **LINT** (health-check). They are provided by the user-level `wiki-ingest`, `wiki-query` and `wiki-lint` skills installed by llm-wiki-scaffolder (in Claude Code: `/wiki-ingest <path>`, `/wiki-query "<question>"`, `/wiki-lint`).

## Roles

Three roles, defined in detail under `.github/agents/` (when present):

- **`wiki-maintainer`** — INGEST. Reads `raw/`, writes `wiki/`. Handles single and batch ingest.
- **`wiki-reader`** — QUERY. Read-only. Answers questions with `[[wikilink]]` citations. May archive substantive answers under `wiki/analysis/`.
- **`wiki-auditor`** — LINT. Health-checks the wiki. May repair frontmatter but never edits page content.

## Conventions

Formatting rules — YAML frontmatter, `snake_case` file names, Obsidian syntax (`[[wikilink]]`, callouts), source fidelity, cross-reference discipline, and the `raw/` immutability rule — live in `.github/instructions/wiki-conventions.instructions.md`. VS Code Copilot auto-loads that file; **every other assistant must read it before writing anything under `wiki/`**.

## Reference

Full pattern description in `.github/karpathy_llm_wiki_pattern.md` (copied into this vault at creation time so it stays available offline and version-pinned).
