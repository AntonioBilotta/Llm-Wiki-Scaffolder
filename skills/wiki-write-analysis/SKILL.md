---
name: wiki-write-analysis
description: Archive a substantive analysis, comparison, or derived synthesis as a new page under `wiki/analysis/` (Karpathy pattern - 'good answers can be filed back into the wiki'). Use when the user wants to preserve a wiki-based answer, save an exploration, archive a synthesis for future reference, or when a wiki-reader identifies an answer worth compounding into the knowledge base. Writes exactly one file via a bundled Python script; refuses to overwrite. Trigger keywords - 'archive this analysis', 'save this to the wiki', 'file this answer', 'preserve this synthesis'.
argument-hint: "title=<string> content=<markdown> related_sources=<list of wiki source page names> [tags=<list>] [vault_path=<absolute path>]"
user-invocable: false
---

# wiki-write-analysis

Create `<vault_path>/wiki/analysis/<slug>.md` with the provided content. Blast radius: exactly this one file.

## Invocation

Run the bundled script via the platform terminal tool:

```bash
python3 scripts/write_analysis.py \
  --vault-path "<absolute vault path>" \
  --title "<analysis title>" \
  --content "<markdown body, verbatim>" \
  --related-sources "src_a,src_b" \
  --tags "tag1,tag2"
```

Parse stdout as JSON. The script (stdlib only) writes the file with standard frontmatter and the content passed through verbatim. Check the `created` field — exit code is always 0.

## Algorithm

1. **Resolve `vault_path`** (from `vault_path` argument, required — read from the workspace's `.github/copilot-instructions.md` under `## Vault / **Path:**`).

2. **Compute the target filename:**
   - Snake_case slug from `title`.
   - Target path: `<vault_path>/wiki/analysis/<slug>.md`.
   - If it already exists, refuse: return `created: false, reason: "already_exists"`.

3. **Compose the page:**

   ```markdown
   ---
   type: analysis
   creation_date: <today YYYY-MM-DD>
   update_date: <today YYYY-MM-DD>
   related_sources: [[[source_a]], [[source_b]], ...]
   tags: [<list from argument>]
   ---

   # <title>

   <content, verbatim from argument>
   ```

4. **Write** the file.

## Return value

```yaml
created: true
path: <absolute path>
page: <slug>
```

Or `created: false, reason: <string>`.

## Constraints

- **Single-file write** under `<vault_path>/wiki/analysis/` only.
- **Never overwrite** an existing analysis page.
- **Content is passed through verbatim.** This skill does not re-synthesize, edit, or truncate the provided content — it wraps it in frontmatter and writes it.
- **Follow the vault's frontmatter conventions** as documented in `<vault_path>/.github/instructions/wiki-conventions.instructions.md`.

## Gotchas

- The `--content` argument is passed through verbatim as the page body. Do NOT include YAML frontmatter or an H1 heading in the content — the script wraps both.
- Markdown content can be arbitrarily long. On some shells, extremely long argument values fail with "argument list too long". If you hit this, write the content to `/tmp/analysis-content.md` and pass via `--content "$(cat /tmp/analysis-content.md)"`.
- Shell-escape the content carefully: single-quote wrapping fails on content containing apostrophes; double-quote wrapping requires escaping `$`, `` ` ``, `\`.
- The script exits 0 even on refusal to overwrite — check the `created` field.
- To *update* an existing analysis page, use the platform `edit` tool directly. This skill only creates.
