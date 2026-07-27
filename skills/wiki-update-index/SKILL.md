---
name: wiki-update-index
description: Add or update an entry in `wiki/index.md` under a specified section — Entities, Concepts, Sources, Analysis, or any domain-specific section. Writes exactly one file (the index) via a bundled Python script. Use after creating or modifying a wiki page to keep the catalog current. Not directly invocable — orchestrated by ingest, lint, and archive workflows.
argument-hint: "section=<section name> page=<page name without .md> summary=<one-line description> [vault_path=<absolute path>]"
user-invocable: false
---

# wiki-update-index

Insert or replace a page's line under a specified section of `<vault_path>/wiki/index.md`. Blast radius: exactly this one file.

## Invocation

Run the bundled script via the platform terminal tool:

```bash
python3 scripts/update_index.py \
  --vault-path "<absolute vault path>" \
  --section "Entities" \
  --page "entity_name_without_md" \
  --summary "one-line description"
```

Parse stdout as JSON. If the target section does not exist, the script appends it at the end of the file. If an entry for `--page` already exists in the section, it is replaced (not duplicated). Check `action` (`inserted` or `replaced`) to know what happened.

## Algorithm

1. **Resolve `vault_path`** (from `vault_path` argument, required — read from the workspace's `.github/copilot-instructions.md` under `## Vault / **Path:**`).

2. **Read** `<vault_path>/wiki/index.md`. If it does not exist, create it with a minimal frontmatter block (`type: index`, `update_date: <today>`) plus a `# Index` heading, then continue.

3. **Locate the section** matching `<section>`:
   - Match `## <section>` case-insensitively.
   - Standard sections: `Entities`, `Concepts`, `Sources`, `Analysis`, plus any domain-specific sections the vault has configured.

4. **If the section does not exist**, create it by appending `## <section>` at the end of the file.

5. **Drop the `_(no entries yet)_` placeholder** if present inside the section (added by the scaffolder to keep empty sections visually meaningful).

6. **Within the section**, locate any existing line for `<page>`:
   - A line starting with `- [[<page>]]`.
   - If found, **replace** the line with the new entry (updated summary, today's date).
   - If not found, **append** the new entry at the end of the section (before any trailing blank line).

7. **New entry format:**
   ```
   - [[<page>]] — <summary> · <today YYYY-MM-DD>
   ```

8. **Bump `update_date`** in the file's frontmatter to today if that field is present.

9. **Write back** the whole file. Only `index.md` is touched.

## Return value

```yaml
updated: true
path: <absolute path>
action: "inserted" | "replaced"
section: <section name, as it appears in the file>
```

Or `updated: false, reason: <string>` on failure.

## Constraints

- **Single-file write** on `<vault_path>/wiki/index.md`.
- **Preserve** unrelated sections and entries exactly (byte-identical outside the section touched).
- **Do not modify** page content anywhere else — this skill only updates the catalog.
- If the section name provided does not match any existing section and is not a standard one, create it rather than failing.

## Gotchas

- Section matching is case-insensitive but the section is written with the exact capitalization passed in `--section`. Prefer canonical capitalization (`Entities`, not `entities` or `ENTITIES`).
- Entries are appended in insertion order (not sorted alphabetically) for deterministic behavior. If you want the index sorted, run a separate pass with the platform `edit` tool.
- The `_(no entries yet)_` placeholder is only removed inside the section being updated — other empty sections retain theirs until they receive their first entry.
- The script always exits 0. `updated: false` in the JSON is the failure signal.
- If `wiki/index.md` does not exist, the script creates it with frontmatter + `# Index` heading. Subsequent invocations preserve everything except the `update_date` line, which is bumped to today.
