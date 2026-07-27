---
name: wiki-ingest
description: Ingest a source (single file or folder) from `raw/` into the LLM Wiki. Composes atomic wiki-* skills (`wiki-summarize-source`, `wiki-write-source-page`, `wiki-update-index`, `wiki-append-log`, and `wiki-lint-check` in batch mode) into the canonical INGEST workflow. Handles single-source and batch (folder) modes with chronological ordering. Trigger keywords - 'ingest this source', 'ingest raw/', 'add source to wiki', 'process this into the wiki', '/wiki-ingest', 'add to knowledge base'.
argument-hint: "source_path=<path under raw/, e.g. raw/specs/auth.md or raw/specs/> [vault_path=<absolute path>]"
---

# wiki-ingest

Ingest a source (single file or folder) from `raw/` into the LLM Wiki following the canonical INGEST workflow. Composes user-level atomic wiki-* skills; does not delegate to a vault-level agent (but respects one if active — see step 3 of Preflight).

## Preflight

1. **Resolve `vault_path`** (required):
   - Use the `vault_path` argument if provided by the caller.
   - Otherwise, read the absolute path from the auto-loaded `.github/copilot-instructions.md` in the current workspace (field `**Path:**` under the `## Vault` heading — see [ADR-0010](https://github.com/AntonioBilotta/Llm-Wiki-Scaffolder/blob/main/docs/decisions/0010-eliminate-wiki-detect-vault.md)).
   - If neither is available, refuse and ask the user to provide the vault path or to open the vault workspace.
2. **Determine mode** from `source_path`:
   - Single file → **single-source workflow** (below).
   - Folder → **batch workflow** (below).
3. **Agent interaction**: if a vault-level `@wiki-maintainer` agent is active in the current chat, it may take precedence to apply domain-specific guardrails (ADR format for `development`, spoiler-safe for `reading`, PII redaction for `business`/`personal`, etc.). Follow the agent's instructions if that happens. Otherwise proceed with generic behavior below.

## Single-source workflow

1. Apply `wiki-summarize-source` with `vault_path=<from preflight>` and `source_path=<from args>` (relative to the vault root; the skill resolves it under `<vault_path>/raw/`).
2. Briefly discuss the summary with the user: which entities/concepts to emphasize, whether to skip anything. Skip discussion only if the user has already given explicit direction.
3. Apply `wiki-write-source-page` with `vault_path=<...>` and the summary from step 1. It creates `wiki/sources/<slug>.md` and refuses to overwrite an existing source page.
4. For each entity/concept/domain item listed by the summary, apply `wiki-read-page` with `vault_path=<...>` and `page=<name>` to check whether the corresponding page already exists.
   - **Exists**: update the page with the new information the source contributes — cite the new source via `[[wikilink]]`, bump `update_date` to today, flag any contradiction with a `> [!warning] Contradiction: <detail>` callout. Use file-edit tools for content changes (no atomic skill exists for generic page content editing — this is per-vault content work).
   - **Missing**: create the page with the file-create tool, using the frontmatter conventions from `<vault_path>/.github/instructions/wiki-conventions.instructions.md` and the naming convention `snake_case.md`.
5. Optionally update `wiki/overview.md` if the source materially changes the vault's general understanding (new entities, revised counts, new open decisions). Use file-edit tools directly.
6. For each page created or modified, apply `wiki-update-index` with `vault_path=<...>` and the appropriate `section` (Entities, Concepts, Sources, Analysis, or domain-specific).
7. Apply `wiki-append-log` with `vault_path=<...>`, `kind=ingest`, `summary=<source title>`, `touched_pages=<comma-separated list>`.

A single source may touch 5–15 pages. That is expected.

## Batch workflow

1. Enumerate all sources under `source_path` (recursive).
2. Order chronologically: prefer each source's `date` frontmatter field if present, else filesystem `mtime`. Oldest first. This ensures knowledge builds in the order it was produced and contradictions surface naturally as newer sources arrive.
3. Process each source with the single-source workflow above, in order.
4. After all sources are processed, apply `wiki-lint-check` with `vault_path=<...>`, `format=md`, and `scope=pages:<comma-separated>` on the union of touched pages. Present the report to the user.
5. Apply `wiki-append-log` with `vault_path=<...>`, `kind=batch-ingest`, `summary=<N> sources from <path>`, `touched_pages=<union>`.

## Output

For single-source mode: brief summary of created/updated pages, contradictions flagged.

For batch mode: the full changeset plus the lint report from step 4.

## Constraints

- **Never write into `raw/`.** The user's source of truth is immutable.
- **Never invent facts.** Every wiki write must trace back to a source in `raw/` or to already-cited wiki pages.
- If any composed skill returns `already_exists`, `not_found`, or a failure, surface it to the user and stop — do not force-overwrite.
- **Follow conventions** in `<vault_path>/.github/instructions/wiki-conventions.instructions.md` for frontmatter, naming, wikilinks, callouts.

## Gotchas

- The 8 atomic wiki-* skills this workflow composes have `disable-model-invocation: true` — they are hidden from auto-invocation and picker but callable by explicit name (as done here). If you (as model) need to reference one of them outside this skill, you must name it explicitly.
- Step 4 uses file-edit tools directly (not a skill) because generic page content editing is per-vault work, not a shared primitive. The atomic wiki-write-* skills are single-purpose (create a source page, create an analysis page, add to index, append to log) — none handle "arbitrary edit to an existing entity/concept page".
