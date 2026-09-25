---
name: wiki-search
description: Search an LLM Wiki vault's page index for pages matching a query. Use when the user asks a question about content in a wiki they maintain, wants to look up a topic, find pages related to an entity or concept, discover what is already documented, or when another skill (e.g. OpenSpec) needs to check if a topic is covered before writing. Two passes - ranks `wiki/index.md` entries by page name, summary and section, then full-text searches every wiki page (with synonyms) so pages missing from the index are still found. Trigger keywords - 'search the wiki', 'find pages about', 'is X documented', 'what does the wiki say about', 'look up in wiki', 'check wiki for'.
argument-hint: "query=<terms> [vault_path=<absolute path>] [limit=<int, default 10>]"
user-invocable: false
---

# wiki-search

Return a ranked list of wiki pages relevant to a query. Two passes: the vault's `index.md` (fast, curated) and a full-text search of every page (catches what the index misses). An empty result means both passes came back empty.

## Algorithm

1. **Resolve `vault_path`** — required argument, passed by the calling workflow. If you are invoked directly without it, resolve it with the rule in step 1 of the `wiki-ingest` Preflight: argument → `## Vault` signpost in context (`.github/copilot-instructions.md` or `AGENTS.md`) → current folder if it is a vault root → ask the user.

2. **Expand the query.** From `<query>` build the term set: the literal terms plus obvious synonyms, abbreviations and alternate spellings (e.g. `k8s` ↔ `kubernetes`, `CDC` ↔ `change data capture`), and the `snake_case` form of multi-word names (page names use it).

3. **Index pass.** Read `<vault_path>/wiki/index.md` and parse it into `(section, page_link, summary, date)` tuples. The index is organized by section headings (`## Entities`, `## Concepts`, `## Sources`, `## Analysis`, plus any domain-specific sections). Each item is a bullet list line of the form `- [[page]] — summary · YYYY-MM-DD`. Score each tuple against the term set:
   - Page link name matches (highest weight)
   - Summary text matches (medium weight)
   - Section heading matches (low weight, unless the query mentions the type explicitly, e.g. `entity foo`)

4. **Full-text pass.** Search the body of every `<vault_path>/wiki/**/*.md` file except `index.md` and `log.md` for the term set, case-insensitive, with the platform search tool (grep/ripgrep or equivalent). For each matching page not already scored in step 3, add a result with `match: full_text`, `in_index: false`, the matching line as `summary`, and a medium-low score (below any page-name match). For pages found by both passes, set `match: both` and raise their score slightly.

5. **Return** the top `limit` results (default 10), sorted by score descending, ties broken alphabetically by page name, together with `searched: [index, full_text]`.

## Return value

```yaml
results:
  - page: <page name without .md>
    section: <index section>
    summary: <one-line summary from index>
    date: <YYYY-MM-DD or null>
    score: <0.0-1.0>
    match: index | full_text | both
    in_index: <bool>
searched: [index, full_text]
```

Empty `results` if neither pass matched. Callers must not report "the wiki has nothing on X" unless both passes ran.

## Constraints

- **Read-only.** Never modify the index or any page.
- If `wiki/index.md` does not exist, skip the index pass, run the full-text pass anyway, and add a `note` field explaining that the index is missing.
- If the vault is a fresh scaffold with an empty index, return an empty list and suggest ingesting sources first.

## Gotchas

- Query matching is case-insensitive and tokenized on whitespace, plus the synonyms from step 2. Exact phrase matching is not supported — quote your query in the argument, but the skill still tokenizes.
- Ranking is heuristic (weights: page name > summary > section heading). Very short queries (1–2 chars) produce noisy results; encourage the user to be more specific.
- Results with `in_index: false` are pages that exist on disk but are missing from the index. They are valid results; the missing index entry is a coverage gap that `wiki-lint-check` flags separately.
- The full-text pass matches words, not meaning. If both passes are empty but the topic seems adjacent to existing pages, say so rather than asserting absence.
- Empty result is not an error — a fresh vault legitimately has nothing to search yet.
- **Delimiter ambiguity in the index bullet.** The canonical bullet is `- [[page]] — summary · YYYY-MM-DD` (em-dash + middle dot). User-supplied summaries can legitimately contain the same characters (e.g. `hobbit — 33 years old`). Any future scripted parser must split with `maxsplit=1` on ` — ` and rsplit with `maxsplit=1` on ` · ` — a greedy split fragments the summary.
