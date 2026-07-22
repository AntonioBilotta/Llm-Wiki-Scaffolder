---
description: "Query the LLM Wiki and get an answer with `[[wikilink]]` citations. Orchestrates wiki-detect-vault, wiki-search, wiki-read-page, and synthesis. Optionally archives the answer via wiki-write-analysis + wiki-update-index + wiki-append-log if `--archive` is passed or if the user approves. Use for one-shot programmatic queries against the wiki (Copilot CLI, cross-tool composition, or when the vault-level `@wiki-reader` agent is not available in the current workspace)."
argument-hint: "<question> [--archive]"
---

Answer the user's question using the LLM Wiki as source of truth.

Question: `${input:question}`

## Workflow

1. **Locate the vault**: invoke the `wiki-detect-vault` skill. Record the returned `vault_path`. If the skill asks to disambiguate (multiple vaults found), pass the response through to the user and wait.

2. **Find relevant pages**: invoke `wiki-search` with `vault_path=<from step 1>` and `query=<key terms extracted from the question>`.

3. **Read pages**: for each relevant match from step 2 (top 3–7, depending on scores), invoke `wiki-read-page` with `vault_path=<from step 1>` and `page=<name>`. Follow `[[wikilinks]]` from the returned bodies to drill down when necessary for sufficient context.

4. **Synthesize the answer** with inline `[[page_name]]` citations for every factual claim. If sources contradict, surface the contradiction and cite both pages. If the wiki is thin on the topic, say so and suggest concrete sources that would strengthen coverage.

5. **Archive (opt-in)**: skip this step for short-form or definitional answers. For substantive analyses, comparisons, or newly derived syntheses, propose archival:
   - If the user included `--archive` in the invocation, proceed without asking.
   - Otherwise, present the proposed title + content + related sources to the user and wait for explicit approval.

   Upon approval or `--archive` flag, invoke in sequence:
   - `wiki-write-analysis` with `title=<derived from question>`, `content=<synthesized answer verbatim, no frontmatter, no H1>`, `related_sources=<comma-separated wiki source page names cited>`, optional `tags`.
   - `wiki-update-index` with `section=Analysis`, `page=<slug returned by write-analysis>`, `summary=<one-line description>`.
   - `wiki-append-log` with `kind=query`, `summary=<question summary>`, `touched-pages=<slug from archival>`.

## Constraints

- **Never invent facts.** If the answer is not in the wiki or in cited raw sources, say so explicitly.
- **Cite always.** Every factual claim in the answer must reference a wiki page via `[[page_name]]`.
- **Do not modify `raw/`** ever. Use the platform `read` tool to inspect a raw source only when a wiki page explicitly points to it and you need to verify a detail.
- **Generic behavior only.** This prompt does not apply vault-specific domain guardrails. For interactive queries with role personality (spoiler-safe reading for fiction, PII redaction for business, ADR format for development), use `@wiki-reader` in the vault's chat instead — where present, the vault-level agent adds those constraints on top of the same skill layer.

## Output

Focused answer with inline `[[page_name]]` citations. Do not restate the question at length. If archival was executed (step 5), report the created page slug on a final line: `Archived to: [[<slug>]]`.
