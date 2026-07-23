---
name: wiki-write-source-page
description: Create a new page under `wiki/sources/` from a structured summary (typically produced by `wiki-summarize-source`). Writes exactly one file via a bundled Python script for deterministic, atomic behavior. Refuses to overwrite existing source pages. Use as part of an ingest workflow, after `wiki-summarize-source` and before cross-reference updates. Not directly invocable by the user — orchestrated by `/wiki-ingest`.
argument-hint: "summary=<yaml or json from wiki-summarize-source> [vault_path=<absolute path>]"
user-invocable: false
---

# wiki-write-source-page

Create `<vault_path>/wiki/sources/<slug>.md` with the provided summary. Blast radius: exactly this one file.

## Invocation

Run the bundled script via the platform terminal tool:

```bash
python3 scripts/write_source_page.py \
  --vault-path "<absolute vault path>" \
  --summary-json '<compact JSON string>'
```

Parse stdout as JSON. The script (stdlib only, ~140 lines) implements the algorithm below deterministically. Check the `created` field in the JSON — exit code is always 0.

## Algorithm

1. **Resolve `vault_path`** (from `vault_path` argument, required — read from the workspace's `.github/copilot-instructions.md` under `## Vault / **Path:**`).

2. **Parse `summary`** — a YAML or JSON structure matching the return shape of `wiki-summarize-source`.

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
   related_sources: []
   tags: []
   ---

   # <title>

   **Provenance**: `<raw_path>`
   [If original_url is provided] · [original](<original_url>)
   **Date**: <date>

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

   [For each domain item type present in summary.domain_items:]

   ## <Type capitalized>

   - [[<snake_case_item_1>]]
   - [[<snake_case_item_2>]]
   ```

   Omit sections that would be empty.

5. **Write** the file. Return the absolute path and a copy of what was written.

## Return value

```yaml
created: true
path: <absolute path>
page: <slug>
body: <the written content, for auditability>
```

Or `created: false, reason: <string>` on failure (already exists, invalid summary, write error).

## Constraints

- **Single-file write.** Writes exactly one path under `<vault_path>/wiki/sources/`. Never touches any other file.
- **Never overwrite** an existing source page. Refusal is a return value, not an exception.
- **Follow the vault's frontmatter conventions** as documented in `<vault_path>/.github/instructions/wiki-conventions.instructions.md`. If those conventions add fields, include them with default values.

## Gotchas

- The invocation assumes CWD is the skill directory. If the CWD differs at runtime, prefix the script path with the absolute skill path (typically `~/.copilot/skills/wiki-write-source-page/scripts/write_source_page.py` after install).
- Shell-escape the `--summary-json` argument carefully. Nested quotes or special characters in `key_points` or `title` can break the shell. For complex summaries, write to a temp file and pass via `--summary-json "$(cat /tmp/summary.json)"`.
- The script exits 0 even on refusal to overwrite — check the `created` field in the JSON, not the shell exit code.
- To *update* an existing source page (not create), use the platform `edit` tool directly. This skill only creates.
