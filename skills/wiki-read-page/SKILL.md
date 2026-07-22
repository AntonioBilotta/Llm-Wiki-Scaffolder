---
name: wiki-read-page
description: Read a specific LLM Wiki page and return its structured content — YAML frontmatter parsed into fields, body as markdown, and extracted `[[wikilinks]]`. Use after `wiki-search` identifies a relevant page, when following a cross-reference from another page, when the user references a wiki page by name, or when a downstream skill needs the page's content or metadata. Trigger keywords - 'read the wiki page for X', 'show me the entity Y', 'what does the concept page say about Z', 'load the wiki analysis of W'.
argument-hint: "page=<name without .md> [vault_path=<absolute path>]"
---

# wiki-read-page

Load a wiki page's frontmatter and body for downstream reasoning.

## Algorithm

1. **Resolve `vault_path`** (from `vault_path` argument, required — read from the workspace's `.github/copilot-instructions.md` under `## Vault / **Path:**`).

2. **Locate the file.** The `page` argument omits the `.md` extension and typically omits the folder — search inside `<vault_path>/wiki/**/*.md` for a match:
   - Try in priority order: `wiki/entities/`, `wiki/concepts/`, `wiki/sources/`, `wiki/analysis/`, then any domain-specific content folders (e.g. `wiki/decisions/`, `wiki/characters/`).
   - If the caller passes `page=folder/name`, honor that exact path.
   - If exactly one match is found, return it. If none, return `found: false`. If multiple, return the canonical one (first match by priority) and flag the ambiguity.

3. **Read** the file. Split YAML frontmatter (between the first two `---` fences) from the body.

4. **Parse** frontmatter fields: `type`, `creation_date`, `update_date`, `related_sources`, `tags`, plus any domain-specific fields (`id`, `characters`, `context`, `decision`, `consequences`, etc.).

5. **Extract** all `[[wikilinks]]` from the body (unique, preserving first-occurrence order).

## Return value

```yaml
found: true
page: <name>
path: <absolute path>
frontmatter:
  type: <value>
  creation_date: <value>
  update_date: <value>
  related_sources: [<list>]
  tags: [<list>]
  # any additional domain-specific fields
body: <markdown as-is>
wikilinks: [<list of unique link targets>]
```

Or `found: false, page: <name>, tried_paths: [<list>]` if the page does not exist.

## Constraints

- **Read-only.** Never modify the page.
- **Do not follow wikilinks recursively** — the caller decides which to drill into.
- If frontmatter is malformed (missing closing fence, invalid YAML), return the raw content with an additional `frontmatter_error: <detail>` field. Do not attempt to repair.

## Gotchas

- The `page` argument omits the `.md` extension. If the caller passes `foo.md`, strip it silently rather than failing.
- Ambiguity is possible if the same page name exists in multiple folders (e.g. `entities/foo` and `concepts/foo`). The skill returns the one with highest priority folder and includes `ambiguous_paths: [...]` in the response.
- The wikilinks extractor is a regex over `[[name]]` patterns and does not resolve aliases or nested links. Alias-form `[[target|display]]` returns `target`.
- Frontmatter parsing is intentionally lenient: if a field is present but malformed, it appears in the result as the raw string. Frontmatter integrity checks are the auditor's job, not this skill's.
