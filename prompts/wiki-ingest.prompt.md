---
description: "Ingest a source (single file or a folder) from `raw/` into the LLM Wiki. Composes user-level skills (`wiki-summarize-source`, `wiki-write-source-page`, `wiki-update-index`, `wiki-append-log`). Folder mode batches all sources in chronological order and runs a lint pass at the end. Self-contained — does not delegate to a vault-level agent."
argument-hint: "<path under raw/, e.g. raw/specs/auth.md or raw/specs/>"
---

Ingest the source at `${input:source_path}` into the LLM Wiki. Follow the workflow below. Do not delegate to a vault-level agent — this prompt is self-contained via user-level skills.

## Preflight

1. Invoke the `wiki-detect-vault` skill to resolve the target vault. If a vault-level `@wiki-maintainer` agent is active in the current workspace, it may intercept this prompt to apply its domain guardrails; follow the agent's instructions if that happens. Otherwise proceed with the workflow below.
2. Determine mode from `${input:source_path}`:
   - Single file → **single-source mode** (steps below).
   - Folder → **batch mode** (see section further down).

## Single-source workflow

1. Invoke `wiki-summarize-source` with `source_path=${input:source_path}` (relative to the vault root; the skill resolves it under `<vault_path>/raw/`).
2. Briefly discuss the summary with the user: which entities/concepts to emphasize, whether to skip anything. Skip discussion only if the user has already given explicit direction.
3. Invoke `wiki-write-source-page` with the summary. It creates `wiki/sources/<slug>.md` and refuses to overwrite an existing source page.
4. For each entity/concept/domain item listed by the summary, invoke `wiki-read-page` to check whether the corresponding page already exists.
   - **Exists**: update the page with the new information the source contributes — cite the new source via `[[wikilink]]`, bump `update_date` to today, flag any contradiction with a `> [!warning] Contradiction: <detail>` callout. Use the platform `edit` tool for content changes (no skill exists for generic page content editing — this is per-vault content work).
   - **Missing**: create the page with the platform `edit` tool, using the frontmatter conventions from `<vault_path>/.github/instructions/wiki-conventions.instructions.md` and the naming convention `snake_case.md`.
5. Optionally update `wiki/overview.md` if the source materially changes the vault's general understanding (new entities, revised counts, new open decisions). Use `edit` directly.
6. For each page created or modified, invoke `wiki-update-index` with the appropriate `section` (Entities, Concepts, Sources, or domain-specific).
7. Invoke `wiki-append-log` with `kind=ingest`, `summary=<source title>`, `touched_pages=<comma-separated list>`.

A single source may touch 5–15 pages. That is expected.

## Batch mode

1. Enumerate all sources under `${input:source_path}` (recursive).
2. Order chronologically: prefer each source's `date` frontmatter field if present, else filesystem `mtime`. Oldest first. This ensures knowledge builds in the order it was produced and contradictions surface naturally as newer sources arrive.
3. Process each source with the single-source workflow above, in order.
4. After all sources are processed, invoke `wiki-lint-check` with `format=md` on the touched pages (`scope=pages:<comma-separated>`) and present the report to the user.
5. Invoke `wiki-append-log` with `kind=batch-ingest`, `summary=<N> sources from <path>`, `touched_pages=<union>`.

## Output

For single-source mode: brief summary of created/updated pages, contradictions flagged.

For batch mode: the full changeset plus the lint report from step 4.

## Constraints

- **Never write into `raw/`.** The user's source of truth is immutable.
- **Never invent facts.** Every wiki write must trace back to a source in `raw/` or to already-cited wiki pages.
- If any skill returns `already_exists`, `not_found`, or a failure, surface it to the user and stop — do not force-overwrite.
- **Follow conventions** in `<vault_path>/.github/instructions/wiki-conventions.instructions.md` for frontmatter, naming, wikilinks, callouts.
