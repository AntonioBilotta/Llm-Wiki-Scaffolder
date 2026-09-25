---
name: wiki-query
description: Query the LLM Wiki and get an answer with `[[wikilink]]` citations. Composes wiki-search, wiki-read-page, and synthesis. Optionally archives the answer via wiki-write-analysis + wiki-update-index + wiki-append-log if `--archive` is passed or if the user approves. Use for one-shot programmatic queries against the wiki. Trigger keywords - 'query the wiki', 'ask the wiki', 'what does the wiki say about', 'search my knowledge base', 'answer from wiki', '/wiki-query'.
argument-hint: "<question> [--archive]"
---

# wiki-query

Answer the user's question using the LLM Wiki as source of truth. Composes user-level atomic wiki-* skills; does not delegate to a vault-level agent (but respects one if active — see step 1).

## Workflow

1. **Resolve `vault_path`** — first match wins, no upward filesystem walk: (1) the `vault_path` argument; (2) the `**Path:**` field under `## Vault` in the signpost already in context — `.github/copilot-instructions.md` (VS Code Copilot) or `AGENTS.md` (via the vault's `CLAUDE.md` in Claude Code; Codex, Cursor, Aider) — falling back to the directory containing that signpost if the absolute path does not exist in this environment; (3) the folder the user named or the current working directory, if it contains `wiki/` and an `AGENTS.md` or `.github/copilot-instructions.md` mentioning "LLM Wiki"; (4) otherwise ask the user (list the candidates if several vaults are in context). Full rule: `wiki-ingest` Preflight step 1.
   Then read `<vault_path>/.github/instructions/wiki-conventions.instructions.md` unless your runtime auto-loaded it (VS Code Copilot does; Claude Code and others do not).
   If a vault-level `@wiki-reader` agent is active in the current chat, it may take precedence to apply its domain guardrails; follow it if so.

2. **Find relevant pages**: apply the `wiki-search` skill with `vault_path=<from step 1>` and `query=<key terms extracted from the user's question, plus their synonyms and abbreviations>`.

3. **Read pages**: for each relevant match from step 2 (top 3–7, depending on scores), apply the `wiki-read-page` skill with `vault_path=<from step 1>` and `page=<name>`. Follow `[[wikilinks]]` from the returned bodies to drill down when necessary for sufficient context.

4. **Synthesize the answer** with inline `[[page_name]]` citations for every factual claim. If sources contradict, surface the contradiction and cite both pages. If the wiki is thin on the topic, say so and suggest concrete sources that would strengthen coverage. Never claim the wiki has nothing on a topic unless `wiki-search` came back empty on **both** its index pass and its full-text pass — and say that you searched both. Pages found only by full text (`in_index: false`) are valid sources for the answer; mention that they are missing from the index.

5. **Archive (opt-in)**: skip this step for short-form or definitional answers. For substantive analyses, comparisons, or newly derived syntheses, propose archival:
   - If the user included `--archive` in the invocation arguments, proceed without asking.
   - Otherwise, present the proposed title + content + related sources to the user and wait for explicit approval.

   Upon approval or `--archive` flag, apply in sequence:
   - `wiki-write-analysis` with `vault_path=<...>`, `title=<derived from question>`, `content=<synthesized answer verbatim, no frontmatter, no H1>`, `related_sources=<comma-separated wiki source page names cited>`, optional `tags`.
   - `wiki-update-index` with `vault_path=<...>`, `section=Analysis`, `page=<slug returned by write-analysis>`, `summary=<one-line description>`.
   - `wiki-append-log` with `vault_path=<...>`, `kind=query`, `summary=<question summary>`, `touched_pages=<slug from archival>`.

## Constraints

- **Never invent facts.** If the answer is not in the wiki or in cited raw sources, say so explicitly.
- **Cite always.** Every factual claim in the answer must reference a wiki page via `[[page_name]]`.
- **Do not modify `raw/`** ever. Use the platform file-read tool to inspect a raw source only when a wiki page explicitly points to it and you need to verify a detail.
- **Generic behavior only.** This skill does not apply vault-specific domain guardrails. For interactive queries with role personality (spoiler-safe reading for fiction, PII redaction for business, ADR format for development), use `@wiki-reader` in the vault's chat instead — where present, the vault-level agent adds those constraints on top of the same skill layer.

## Output

Focused answer with inline `[[page_name]]` citations. Do not restate the question at length. If archival was executed (step 5), report the created page slug on a final line: `Archived to: [[<slug>]]`.

## Gotchas

- The atomic `wiki-search`, `wiki-read-page`, `wiki-write-analysis`, `wiki-update-index`, `wiki-append-log` skills this workflow composes have `user-invocable: false` — hidden from the `/` menu but callable by explicit name from this orchestrator.
- Short-form answers (definitional lookups, factual one-liners) do not need archival — skip step 5 entirely.
