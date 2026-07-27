---
name: wiki-write-source-page
description: Create a new page under `wiki/sources/` from a structured summary (typically produced by `wiki-summarize-source`). Writes exactly one file via a bundled Python script for deterministic, atomic behavior. Refuses to overwrite existing source pages. Use as part of an ingest workflow, after `wiki-summarize-source` and before cross-reference updates. Not directly invocable by the user — orchestrated by `/wiki-ingest`.
argument-hint: "summary=<json from wiki-summarize-source> [related_sources=<comma-separated>] [tags=<comma-separated>] [vault_path=<absolute path>]"
user-invocable: false
---

# wiki-write-source-page

Create `<vault_path>/wiki/sources/<slug>.md` with the provided summary. Blast radius: exactly this one file.

## Invocation

Run the bundled script via the platform terminal tool:

```bash
python3 scripts/write_source_page.py \
  --vault-path "<absolute vault path>" \
  --summary-json '<compact JSON string>' \
  [--related-sources "src_a,src_b"] \
  [--tags "tag1,tag2"]
```

Parse stdout as JSON. The script (stdlib only, ~140 lines) implements the algorithm below deterministically. Check the `created` field in the JSON — exit code is always 0.

`--related-sources` and `--tags` are optional. By default both frontmatter fields are emitted as empty lists (`[]`) — populated later by the ingest orchestrator via file-edit tools as cross-references are discovered. Pass them at creation only when the summary already knows the relations.

## Algorithm

1. **Resolve `vault_path`** (from `vault_path` argument, required — read from the workspace's `.github/copilot-instructions.md` under `## Vault / **Path:**`).

2. **Parse `summary`** — a JSON structure matching the return shape of `wiki-summarize-source` (passed via `--summary-json`, parsed with `json.loads`; YAML is not accepted).

3. **Compute the target filename:**
   - Snake_case slug from `summary.title` (lowercase, non-alphanumeric → underscore, collapse runs, strip leading/trailing underscores).
   - Target path: `<vault_path>/wiki/sources/<slug>.md`.
   - If the target file already exists, refuse to overwrite. Return `created: false, reason: "already_exists", existing_path: <path>` and stop.

4. **Compose the page body:**

   ```markdown
   ---
   type: source
   creation_date: <today YYYY-MM-DD>
   update_date: <today YYYY-MM-DD>
   source_date: <summary.date>       # only if summary.date is set
   related_sources: [<from --related-sources, or [] if omitted>]
   tags: [<from --tags, or [] if omitted>]
   ---

   # <title>

   - **Provenance**: `<raw_path>` [· [original](<original_url>) if provided]
   - **Date**: <summary.date>          # only if summary.date is set

   ## Summary

   - <key_point_1>
   - <key_point_2>
   - ...

   ## Entities

   - [[<snake_case_entity_1>]]
   - [[<snake_case_entity_2>]]

   ## Concepts

   - [[<snake_case_concept_1>]]
   - [[<snake_case_concept_2>]]

   [For each domain item type present in summary.domain_items (excluding 'entities'/'concepts'):]

   ## <Type Title Cased>

   - [[<snake_case_item_1>]]
   - [[<snake_case_item_2>]]
   ```

   Omit sections that would be empty. `source_date` in frontmatter preserves the source's publication date separately from ingest date; used by wiki-lint-check stale detection. The script normalizes `summary.date` to a pure `YYYY-MM-DD` string (accepts `YYYY-MM-DD` and full ISO `YYYY-MM-DDTHH:MM:SS[Z|±HH:MM]`, extracting the date component). Unparseable values (e.g. `"May 2024"`, `"2024/05/10"`) are dropped from the frontmatter — they would otherwise break the lint stale-check sort by mixing `str`/`datetime.date`/`datetime.datetime` — but are kept verbatim in the body's `- **Date**:` line for human readability, with a warning surfaced in the return JSON.

5. **Write** the file. Return the absolute path and a copy of what was written.

## Return value

```yaml
created: true
path: <absolute path>
page: <slug>
body: <the written content, for auditability>
warnings: [<string>, ...]   # optional, only present when non-fatal issues occurred
```

Or `created: false, reason: <string>` on failure (already exists, invalid summary, write error).

Current `warnings` values include `source_date_not_iso: ...` (date could not be parsed as ISO and was dropped from frontmatter), `source_date_not_string: ...` (non-string value), `key_points_not_list: ...` / `entities_not_list: ...` / `concepts_not_list: ...` (top-level summary field with wrong type, coerced to `[]`), `provenance_not_dict: ...` (provenance object arrived as non-dict, coerced to `{}`), and `domain_items_not_dict: ...` / `domain_items.<type>_not_list: ...` (per-bucket type errors, that bucket is skipped).

## Constraints

- **Single-file write.** Writes exactly one path under `<vault_path>/wiki/sources/`. Never touches any other file.
- **Never overwrite** an existing source page. Refusal is a return value, not an exception.
- **Follow the vault's frontmatter conventions** as documented in `<vault_path>/.github/instructions/wiki-conventions.instructions.md`. If those conventions add fields, include them with default values.

## Gotchas

- The invocation assumes CWD is the skill directory. If the CWD differs at runtime, prefix the script path with the absolute skill path (typically `~/.copilot/skills/wiki-write-source-page/scripts/write_source_page.py` after install).
- Shell-escape the `--summary-json` argument carefully. Nested quotes or special characters in `key_points` or `title` can break the shell. For complex summaries, write to a temp file and pass via `--summary-json "$(cat /tmp/summary.json)"`.
- The script exits 0 even on refusal to overwrite — check the `created` field in the JSON, not the shell exit code.
- To *update* an existing source page (not create), use the platform `edit` tool directly. This skill only creates.
- **No cross-section dedup.** A term appearing in both `summary.entities` and `summary.concepts` (or in an additional `domain_items` bucket like `characters`) produces one wikilink per section — e.g. `[[frodo]]` under both `## Entities` and `## Characters`. This is intentional: it reflects the taxonomic distinction the summarizer made. If your domain treats an item as strictly one type, ensure the summary places it in only one bucket.
- **Defensive coercion.** If a summary field with an expected list type (`key_points`, `entities`, `concepts`, or a `domain_items` bucket) or the top-level `provenance` object arrives with the wrong Python type (e.g. a string instead of a list), the field is silently coerced to an empty default and a `<field>_not_list` / `provenance_not_dict` warning is surfaced in the return JSON. The page is still written, minus the offending section — orchestrators should inspect `warnings` before considering the ingest complete.
