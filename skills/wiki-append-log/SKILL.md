---
name: wiki-append-log
description: Append a dated entry to `wiki/log.md` recording an ingest, query, lint, batch, or other wiki operation. Writes exactly one file (append-only) via a bundled Python script. Use at the end of every operational workflow to preserve the chronological log per the Karpathy pattern. Standardized format keeps the log greppable with `grep '^## \['`. Not directly invocable — every wiki workflow ends with this.
argument-hint: "kind=<ingest|query|lint|batch-ingest|other> summary=<one-line description> [touched_pages=<comma-separated wiki page names>] [vault_path=<absolute path>]"
disable-model-invocation: true
---

# wiki-append-log

Append a standardized entry to `<vault_path>/wiki/log.md`. Append-only. Blast radius: exactly this one file.

## Invocation

Run the bundled script via the platform terminal tool:

```bash
python3 scripts/append_log.py \
  --vault-path "<absolute vault path>" \
  --kind "ingest" \
  --summary "Source Title" \
  --touched-pages "page_a,page_b"
```

Parse stdout as JSON. The script enforces that `--kind` is a single lowercase word (letters, digits, hyphens) so the log stays greppable. Pages in `--touched-pages` are wrapped in `[[]]` automatically — pass bare names.

## Algorithm

1. **Resolve `vault_path`** (from `vault_path` argument, required — read from the workspace's `.github/copilot-instructions.md` under `## Vault / **Path:**`).

2. **Ensure the log file exists.** If `<vault_path>/wiki/log.md` is absent, create it with a `# Log` heading. If present, preserve its content exactly.

3. **Compose the entry:**

   ```

   ## [<today YYYY-MM-DD>] <kind> | <summary>
   ```

   If `touched_pages` is non-empty, add a second line:

   ```
   Touched pages: [[page_a]], [[page_b]], ...
   ```

4. **Append** to the file. Preserve trailing newlines; if the file already ends with a newline, add a blank line before the new entry for readability.

## Return value

```yaml
appended: true
path: <absolute path>
line_prefix: "## [<date>] <kind> | ..."
```

## Constraints

- **Append-only.** Never modify existing log lines. Never insert in the middle.
- **`kind` must be a single word** (no spaces) so that the log stays greppable: `grep "^## \[" log.md`.
- **Never** touch any file other than `wiki/log.md`.

## Gotchas

- `--kind` is validated as `^[a-z][a-z0-9-]*$`. Spaces, uppercase, and punctuation are rejected — use `batch-ingest`, not `batch ingest` or `Batch Ingest`.
- `--touched-pages` receives bare page names (no `.md`, no `[[]]` wrapping). The script wraps them. Passing `[[foo_bar]]` produces `[[[[foo_bar]]]]` in the log.
- The script always exits 0. Check the `appended` field for the outcome.
- If `wiki/log.md` does not exist, the script creates it with a `# Log` heading. Subsequent invocations preserve it.
- Multiple appends on the same day are fine — each entry gets its own `## [YYYY-MM-DD] ...` heading and can be grepped by date.
