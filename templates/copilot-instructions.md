# {{PROJECT_NAME}}

**Type:** {{DOMAIN_TYPE}}
**Description:** {{DOMAIN_DESCRIPTION}}

This workspace contains an **LLM Wiki** — a persistent, LLM-maintained knowledge base following the [Karpathy pattern](./karpathy_llm_wiki_pattern.md).

## Vault

- **Path:** `{{VAULT_PATH}}`
- **Type:** `{{DOMAIN_TYPE}}`

> **Note for LLMs orchestrating wiki-* skills:** the absolute path above is the authoritative `vault_path`. Pass it as the `vault_path` argument to every wiki-* skill invocation (`wiki-search`, `wiki-read-page`, `wiki-write-source-page`, `wiki-write-analysis`, `wiki-update-index`, `wiki-append-log`, `wiki-summarize-source`, `wiki-lint-check`). Do not attempt to detect the vault path by walking the filesystem — this file is the single source of truth. See [ADR-0010](https://github.com/AntonioBilotta/Llm-Wiki-Scaffolder/blob/main/docs/decisions/0010-eliminate-wiki-detect-vault.md).

## Layout

- `raw/` — **immutable** source material. Only the user writes here. **Never** modify anything under `raw/`.
- `wiki/` — LLM-maintained markdown (entities, concepts, sources, analysis, plus domain-specific folders, and the navigation files `index.md`, `log.md`, `overview.md`).

## Commands

Operational commands come from the **user-level llm-wiki-scaffolder install** (per [ADR-0009](https://github.com/AntonioBilotta/Llm-Wiki-Scaffolder/blob/main/docs/decisions/0009-evaluate-user-level-vault-operational-customizations.md) Model D): skills and prompts are installed once per machine and work in any vault workspace or from Copilot CLI.

Cross-surface primitives (installed at user level):

- `/wiki-ingest <path>` — ingest a source (single file or folder) into the wiki.
- `/wiki-lint` — health-check the wiki (contradictions, orphans, stale claims, coverage gaps).
- `/wiki-query "<question>" [--archive]` — one-shot query with citations; optionally archives the answer.
- `wiki-*` skills (`wiki-search`, `wiki-read-page`, ...) — atomic capabilities auto-invokable by Copilot and composable from third-party skills (e.g. OpenSpec).

Vault-scoped roles (this `.github/agents/` folder, optional per domain):

- `@wiki-maintainer` — interactive ingest with vault-specific domain personality (e.g. ADR format for development, spoiler-safe for reading-fiction, PII redaction for business).
- `@wiki-reader` — interactive query with the same domain personality; can archive substantive answers in `wiki/analysis/`.
- `@wiki-auditor` — interactive audit; may repair frontmatter but never edits page content.

If the slash-commands and skills are not available in Copilot's picker, the user-level install is missing. Run once:

```
git clone https://github.com/AntonioBilotta/Llm-Wiki-Scaffolder ~/llm-wiki-scaffolder
cd ~/llm-wiki-scaffolder && ./bin/install.sh
```

Then reload the VS Code window.

## Conventions

Formatting rules (YAML frontmatter, `snake_case`, Obsidian callouts, `[[wikilink]]`, domain-specific conventions) live in [`.github/instructions/wiki-conventions.instructions.md`](./instructions/wiki-conventions.instructions.md). They are auto-loaded by VS Code Copilot when working on any file under `wiki/**` or `raw/**` — you do not need to reference them explicitly.

## Reference

- Original pattern: [`karpathy_llm_wiki_pattern.md`](./karpathy_llm_wiki_pattern.md) (copied into this vault so it stays available even outside the parent workspace).
