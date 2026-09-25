---
name: wiki-ingest
description: Ingest a source (single file or folder) from `raw/` into the LLM Wiki. Composes atomic wiki-* skills (`wiki-summarize-source`, `wiki-search`, `wiki-write-source-page`, `wiki-update-index`, `wiki-append-log`, and `wiki-lint-check` in batch mode) into the canonical INGEST workflow, with a triage step that can stop on sources adding no new material. Handles single-source and batch (folder) modes with chronological ordering. Trigger keywords - 'ingest this source', 'ingest raw/', 'add source to wiki', 'process this into the wiki', '/wiki-ingest', 'add to knowledge base'.
argument-hint: "source_path=<path under raw/, e.g. raw/specs/auth.md or raw/specs/> [vault_path=<absolute path>]"
---

# wiki-ingest

Ingest a source (single file or folder) from `raw/` into the LLM Wiki following the canonical INGEST workflow. Composes user-level atomic wiki-* skills; does not delegate to a vault-level agent (but respects one if active — see step 3 of Preflight).

## Preflight

1. **Resolve `vault_path`** — first match wins; never walk up the filesystem looking for vaults ([ADR-0010](https://github.com/AntonioBilotta/Llm-Wiki-Scaffolder/blob/main/docs/decisions/0010-eliminate-wiki-detect-vault.md)):
   1. The `vault_path` argument, if the caller passed one.
   2. The `**Path:**` field under `## Vault` in the vault signpost already in your context: `.github/copilot-instructions.md` (auto-loaded by VS Code Copilot) or `AGENTS.md` (imported by the vault's `CLAUDE.md` in Claude Code; read directly by Codex, Cursor, Aider). If that absolute path does not exist in the current environment (vault opened from another machine, a mounted folder, a cloud session), use the directory that contains the signpost instead — `AGENTS.md` sits at the vault root, `copilot-instructions.md` in `<root>/.github/`.
   3. The folder the user named, or the current working directory, **if it is a vault root**: it contains `wiki/` and an `AGENTS.md` or `.github/copilot-instructions.md` mentioning "LLM Wiki".
   4. Otherwise stop and ask the user for the vault path. If several vaults are in context (multi-root workspace), list them and ask which one.
2. **Load the conventions.** Read `<vault_path>/.github/instructions/wiki-conventions.instructions.md` unless your runtime already auto-loaded it (VS Code Copilot does for `wiki/**` and `raw/**`; Claude Code and other runtimes do not). Every write in this workflow follows it, including its **Source fidelity** rule.
3. **Determine mode** from `source_path`:
   - Single file → **single-source workflow** (below).
   - Folder → **batch workflow** (below).
4. **Agent interaction**: if a vault-level `@wiki-maintainer` agent is active in the current chat, it may take precedence to apply domain-specific guardrails (ADR format for `development`, spoiler-safe for `reading`, PII redaction for `business`/`personal`, etc.). Follow the agent's instructions if that happens. Otherwise proceed with generic behavior below.

## Single-source workflow

1. Apply `wiki-summarize-source` with `vault_path=<from preflight>` and `source_path=<from args>` (relative to the vault root; the skill resolves it under `<vault_path>/raw/`).
2. **Triage** — decide what the source adds before writing anything:
   - Apply `wiki-search` with `vault_path=<...>` and `query=<the summary's entities, concepts, key terms, plus their synonyms and abbreviations>`. It searches both the index and the full text of the wiki. Read the top matches with `wiki-read-page`.
   - State one **disposition**, with a one-line reason:
     - **New** — the source introduces entities/concepts/claims the wiki does not hold.
     - **Update** — it adds detail to pages that already exist.
     - **Disputed** — it contradicts something the wiki states (may combine with New or Update).
     - **No material** — it adds nothing beyond what the wiki already holds (a near-copy, a thinner restatement, a source already ingested under another name). Exclusive: cannot combine with the others.
   - If `summary.duplicate_of` is set, the summarizer matched an existing source page by title or URL: treat it as strong evidence for **No material** (or **Update** if the source is a newer revision).
   - Present the summary and the disposition to the user: which entities/concepts to emphasize, whether to skip anything. Skip the discussion only if the user has already given explicit direction; in batch mode, apply the disposition without asking and list it in the final report.
   - **No material → stop here.** Keep the raw file (it is immutable), do not create a source page, do not touch the index. Apply `wiki-append-log` with `kind=ingest` and `summary=no material: <vault-relative raw path, e.g. raw/specs/auth.md>` — this exact prefix is how `wiki-lint-check` excludes the file from its unreferenced-raw inventory. Report and end the workflow.
3. Apply `wiki-write-source-page` with `vault_path=<...>` and the summary from step 1. It creates `wiki/sources/<slug>.md` and refuses to overwrite an existing source page.
4. **Update or create the affected pages.** The candidates are every entity/concept/domain item listed by the summary **plus** every page the triage search found making a claim this source confirms, extends or contradicts (the cascade: do not rely on the summary alone). For each candidate, apply `wiki-read-page` with `vault_path=<...>` and `page=<name>`.
   - **Exists**: update the page with what the source contributes — cite the new source via `[[wikilink]]` and add it to `related_sources`, bump `update_date` to today. When the source contradicts an existing claim, keep the old claim and flag it with `> [!warning] Contradiction: <detail>`; when it supersedes it, use `> [!warning] Stale: <detail>`. Never silently rewrite history. Use file-edit tools for content changes (no atomic skill exists for generic page content editing — this is per-vault content work).
   - **Missing**: create the page with the file-create tool, using the frontmatter conventions and the `snake_case.md` naming, with the source in `related_sources`.
   - **Source fidelity (grounding).** Before writing any number, date or direct quote on any page, locate it in the raw file (read or search it) and copy it exactly as written — if the source says `42K`, write `42K`, not `42,000`. For a derived value (sum, delta, count you computed), show its components so each one can be found in the raw file. If you cannot locate a value, drop it or state it without precision. `wiki-lint-check` verifies this mechanically afterwards.
5. Optionally update `wiki/overview.md` if the source materially changes the vault's general understanding (new entities, revised counts, new open decisions). Use file-edit tools directly.
6. For each page created or modified, apply `wiki-update-index` with `vault_path=<...>` and the appropriate `section` (Entities, Concepts, Sources, Analysis, or domain-specific).
7. Apply `wiki-append-log` with `vault_path=<...>`, `kind=ingest`, `summary=<source title> (<disposition>)`, `touched_pages=<comma-separated list>`.

A single source may touch 5–15 pages. That is expected.

## Batch workflow

1. Enumerate all sources under `source_path` (recursive).
2. Order chronologically: prefer each source's `date` frontmatter field if present, else filesystem `mtime`. Oldest first. This ensures knowledge builds in the order it was produced and contradictions surface naturally as newer sources arrive.
3. Process each source with the single-source workflow above, in order — one at a time, never in parallel: the index, the log and the cascade updates are shared state.
4. After all sources are processed, apply `wiki-lint-check` with `vault_path=<...>`, `format=md`, and `scope=pages:<comma-separated>` on the union of touched pages. Present the report to the user.
5. Apply `wiki-append-log` with `vault_path=<...>`, `kind=batch-ingest`, `summary=<N> sources from <path>`, `touched_pages=<union>`.

## Output

For single-source mode: the disposition, then a brief summary of created/updated pages and contradictions flagged (or, for No material, the one-line reason).

For batch mode: the disposition of each source, the full changeset, and the lint report from step 4.

## Constraints

- **Never write into `raw/`.** The user's source of truth is immutable.
- **Never invent facts.** Every wiki write must trace back to a source in `raw/` or to already-cited wiki pages. Numbers, dates and quotes follow the source-fidelity rule in step 4.
- If any composed skill returns `already_exists`, `not_found`, or a failure, surface it to the user and stop — do not force-overwrite.
- **Follow conventions** in `<vault_path>/.github/instructions/wiki-conventions.instructions.md` for frontmatter, naming, wikilinks, callouts.

## Gotchas

- The 8 atomic wiki-* skills this workflow composes have `user-invocable: false` — hidden from the `/` menu (VS Code Copilot, Claude Code) but callable by explicit name, as done here.
- **No material is a valid outcome**, not a failure. Do not force an article out of a thin source.
- Step 4 uses file-edit tools directly (not a skill) because generic page content editing is per-vault work, not a shared primitive. The atomic wiki-write-* skills are single-purpose (create a source page, create an analysis page, add to index, append to log) — none handle "arbitrary edit to an existing entity/concept page".
