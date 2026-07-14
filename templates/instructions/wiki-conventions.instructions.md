---
description: "Conventions for files in the LLM Wiki (`wiki/`) and sources in `raw/`. Covers YAML frontmatter, snake_case naming, Obsidian syntax (wikilinks, callouts), cross-reference discipline, and the `raw/` immutability rule. Auto-loaded when working on any file under wiki/** or raw/**."
applyTo: "wiki/**,raw/**"
---

# LLM Wiki — Conventions

These conventions apply to every file inside `wiki/` (LLM-maintained markdown) and `raw/` (immutable sources). They are auto-loaded by VS Code Copilot when working on matching files.

## Fundamental rule

**Never modify anything under `raw/`.** It is the user's immutable source of truth. Read from `raw/`; write only to `wiki/`.

## Wiki page format

Every page under `wiki/` (except `index.md` and `log.md`) must start with YAML frontmatter:

```yaml
---
type: entity | concept | source | analysis | {{DOMAIN_EXTRA_TYPES}}
creation_date: YYYY-MM-DD
update_date: YYYY-MM-DD
related_sources: []        # list of links to pages in wiki/sources/
tags: []
---
```

`index.md` uses `type: index`; `log.md` has no frontmatter (append-only chronological log); `overview.md` uses `type: overview`.

## Naming

- Use `snake_case` for all file names. Examples: `entity_name.md`, `key_concept.md`, `authentication_flow.md`.
- Use lowercase for tags and folder names.

## Obsidian conventions

- Internal links: `[[file_name]]` (no `.md` extension).
- Callouts: `> [!note]`, `> [!warning]`, `> [!important]`, `> [!tip]`.
- Contradictions between sources: `> [!warning] Contradiction: <detail>` on the affected page.
- Stale claims flagged by lint: `> [!warning] Stale: <detail>`.
- Images: place in `raw/assets/`, reference as `![[raw/assets/image_name.png]]`.
- Code blocks: use a language tag when possible (e.g. ` ```yaml `, ` ```bash `). Do not embed secrets, credentials, or API keys.

## Cross-reference discipline

- Always cite the source when writing a factual statement on a wiki page (link to the corresponding `wiki/sources/<name>` page).
- When updating a piece of data, check whether other pages report the same and update them together.
- When creating a page, add an entry to the appropriate section of `wiki/index.md` and append a line to `wiki/log.md`.

## Domain conventions

{{DOMAIN_SPECIFIC_CONVENTIONS}}

## No ad-hoc changes

Modify `wiki/` **only** through the defined roles:

- `@wiki-maintainer` for INGEST (adding sources, updating derived pages).
- `@wiki-reader` for QUERY (may archive substantive answers in `wiki/analysis/`).
- `@wiki-auditor` for LINT (may repair frontmatter; may not edit page content).

Every change must be tracked in `wiki/log.md`. Do not fix small errors in passing — flag them for the next lint pass.

## Language

Write all wiki content in {{LANGUAGE}}.
