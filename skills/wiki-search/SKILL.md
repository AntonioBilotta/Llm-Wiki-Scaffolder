---
name: wiki-search
description: Search an LLM Wiki vault's page index for pages matching a query. Use when the user asks a question about content in a wiki they maintain, wants to look up a topic, find pages related to an entity or concept, discover what is already documented, or when another skill (e.g. OpenSpec) needs to check if a topic is covered before writing. Reads `wiki/index.md` and ranks matches by page name, summary, and section relevance. Trigger keywords - 'search the wiki', 'find pages about', 'is X documented', 'what does the wiki say about', 'look up in wiki', 'check wiki for'.
argument-hint: "query=<terms> [vault_path=<absolute path>] [limit=<int, default 10>]"
user-invocable: false
---

# wiki-search

Return a ranked list of wiki pages relevant to a query, by scanning the vault's `index.md`.

## Algorithm

1. **Resolve `vault_path`** (required):
   - Use the `vault_path` argument if provided by the caller.
   - Otherwise, refuse and instruct the caller to provide it. The vault path is authoritative in the workspace's `.github/copilot-instructions.md` under the `## Vault / **Path:**` field (see [ADR-0010](https://github.com/AntonioBilotta/Llm-Wiki-Scaffolder/blob/main/docs/decisions/0010-eliminate-wiki-detect-vault.md)).

2. **Read** `<vault_path>/wiki/index.md`.

3. **Parse** the index into `(section, page_link, summary, date)` tuples. The index is organized by section headings (`## Entities`, `## Concepts`, `## Sources`, `## Analysis`, plus any domain-specific sections). Each item is a bullet list line of the form `- [[page]] — summary · YYYY-MM-DD`.

4. **Score** each tuple against `<query>`:
   - Page link name matches (highest weight)
   - Summary text matches (medium weight)
   - Section heading matches (low weight, unless the query mentions the type explicitly, e.g. `entity foo`)

5. **Return** the top `limit` results (default 10), sorted by score descending, ties broken alphabetically by page name.

## Return value

```yaml
results:
  - page: <page name without .md>
    section: <index section>
    summary: <one-line summary from index>
    date: <YYYY-MM-DD or null>
    score: <0.0-1.0>
```

Empty list if no matches.

## Constraints

- **Read-only.** Never modify the index or any page.
- If `wiki/index.md` does not exist, return an empty result set with a `note` field explaining that the index is missing.
- If the vault is a fresh scaffold with an empty index, return an empty list and suggest ingesting sources first.

## Gotchas

- Query matching is case-insensitive and tokenized on whitespace. Exact phrase matching is not supported — quote your query in the argument, but the skill still tokenizes.
- Ranking is heuristic (weights: page name > summary > section heading). Very short queries (1–2 chars) produce noisy results; encourage the user to be more specific.
- The skill only reads `wiki/index.md`. Pages that exist on disk but are missing from the index are invisible — that is a known coverage gap that `wiki-lint-check` flags separately.
- Empty result is not an error — a fresh vault legitimately has nothing to search yet.
