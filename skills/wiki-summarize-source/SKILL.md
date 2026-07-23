---
name: wiki-summarize-source
description: Read a source file in a vault's `raw/` directory and produce a structured summary — title, provenance, key points, entities, concepts, and domain items the source touches. Output-only, does NOT write to the wiki. Use as the first step of an ingest workflow, or whenever the user wants to preview what a raw source contains before adding it to the wiki, or when producing a structured breakdown of a document for downstream processing. Trigger keywords - 'summarize this source', 'preview the raw file', 'what is in this document', 'break down this article for the wiki', 'analyze this source before ingesting'.
argument-hint: "source_path=<path to file under raw/> [vault_path=<absolute path>]"
user-invocable: false
---

# wiki-summarize-source

Produce a structured summary of a raw source, ready to be consumed by ingest orchestration. This skill does not write to the wiki — it only reads and returns.

## Algorithm

1. **Resolve `vault_path`** (from `vault_path` argument, required — read from the workspace's `.github/copilot-instructions.md` under `## Vault / **Path:**`).

2. **Locate the source** at `<vault_path>/<source_path>` (or `<source_path>` if absolute).
   - Text/Markdown/HTML files: read directly.
   - PDFs, images, or other binaries: use platform tools to extract text where possible. If extraction is not possible, return `unsupported: true` with a `reason`.

3. **Extract fields:**
   - **`title`**: first `# heading` in the source, or the filename (stripped of extension and normalized) if no heading exists.
   - **`provenance.raw_path`**: absolute path under `<vault_path>/raw/`.
   - **`provenance.original_url`**: value of `source_url`, `url`, or `link` in source frontmatter, if any; else `null`.
   - **`date`**: value of `date` in source frontmatter if present; else filesystem `mtime` formatted as `YYYY-MM-DD`.
   - **`key_points`**: 3–7 bulleted takeaways, each a complete sentence, extracted from the source's main claims. Prefer the source's own wording; do not synthesize claims the source does not make.
   - **`entities`**: proper nouns — organizations, products, people, places — likely to warrant a wiki entity page. Extract only names the source explicitly mentions.
   - **`concepts`**: recurring themes, technical concepts, ideas the source elaborates on. Same "explicit-mention only" rule.
   - **`domain_items`**: instances of domain-specific types the vault has configured (decisions, requirements, characters, themes, findings, hypotheses, authors, arguments, goals, patterns, reflections, processes, initiatives, topics — check `<vault_path>/.github/instructions/wiki-conventions.instructions.md` for the enabled types). Keyed by type name.

4. **Duplicate check.** Before returning, list files in `<vault_path>/wiki/sources/`. If any existing source page has the same normalized title or references the same `original_url`, add `duplicate_of: <existing page name>` to the return value. The caller decides whether to skip or proceed.

## Return value

```yaml
title: <string>
provenance:
  raw_path: <absolute path>
  original_url: <string or null>
date: <YYYY-MM-DD>
key_points: [<string>, ...]
entities: [<name>, ...]
concepts: [<name>, ...]
domain_items:
  <type>: [<name>, ...]     # e.g. decisions: [auth_migration_v2]
duplicate_of: <existing page name>   # optional, only if a duplicate was detected
```

## Constraints

- **Output-only, no writes.** This skill never modifies any file — it returns a summary for a downstream skill (typically `wiki-write-source-page`) to consume.
- **Never invent** entities, concepts, or facts. Extract only what is explicit in the source.
- **Do not read wiki pages** — this skill is scoped to the source alone. Cross-reference discovery is the ingest orchestrator's job.

## Gotchas

- PDFs, images, and other non-text sources require platform text-extraction tools. If extraction fails or is unavailable, the skill returns `unsupported: true` with a reason; the caller should either provide a pre-extracted markdown version or skip.
- Duplicate detection matches on normalized title or `original_url`. Two sources with the same content but different titles and URLs are NOT detected as duplicates. Manual review recommended for suspected near-duplicates.
- Entity/concept extraction is bounded by what the source explicitly mentions. Do not expect the skill to infer entities not named in the text.
- Very short sources (<200 words) may not produce enough `key_points` to hit the 3–7 target. The skill returns fewer rather than padding with weak points.
