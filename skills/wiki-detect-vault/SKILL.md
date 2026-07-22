---
name: wiki-detect-vault
description: Detect which LLM Wiki vault to operate on. Walks the current working directory upward looking for `.github/copilot-instructions.md` with the 'LLM Wiki' marker; in VS Code multi-root workspaces, also scans every workspace folder. Returns the absolute vault path and project name. If zero or multiple vaults are found, asks the user to disambiguate. Use before any other wiki-* skill when the vault path is not already known. Trigger keywords - 'which vault', 'find my wiki', 'detect the wiki', 'the wiki in this workspace', 'my LLM wiki'.
argument-hint: "[start_dir=<absolute path>]"
---

# wiki-detect-vault

Resolve the target LLM Wiki vault. Return a single vault definition, or ask the user to select if the situation is ambiguous.

## Algorithm

1. **Determine `start_dir`.**
   - If `start_dir=<path>` argument was provided, use it.
   - Else, use the current working directory.

2. **Walk upward** from `start_dir` toward the filesystem root. At each directory `D`, check whether both of these hold:
   - `D/.github/copilot-instructions.md` exists.
   - Its content contains the literal string `LLM Wiki` on any line.

   If yes, record `D` as a candidate vault.

3. **Scan VS Code workspace folders** (if applicable): in a multi-root workspace, also check each other workspace folder for the same marker at its root. Skip this step in CLI-only contexts where the workspace layout is not exposed.

4. **Deduplicate** candidates by canonical absolute path.

5. **Branch on candidate count.**
   - **Zero** — ask the user: *"No LLM Wiki vault detected from `<start_dir>`. Please provide the absolute path to your vault."* Validate that `.github/copilot-instructions.md` with the `LLM Wiki` marker exists at the path the user provides; if not, ask again.
   - **Exactly one** — return that vault directly. No user interaction.
   - **Two or more** — present the list to the user and ask which vault to operate on. Return the chosen one.

## Return value

```yaml
vault_path: <absolute path to vault root>
project_name: <extracted from the first "# ... LLM Wiki" heading in copilot-instructions.md; empty string if not extractable>
```

## Constraints

- **Read-only.** Never modify any file.
- **Never fabricate** a vault path. If none is detected, always ask.
- **Never silently pick** a vault when multiple candidates exist — always disambiguate with the user.

## Gotchas

- The upward walk stops at the filesystem root. On a very deep working directory, this is still bounded (typically <20 iterations).
- Multi-root workspace scanning requires access to VS Code's workspace API and is not always available (e.g. in Copilot CLI outside a VS Code session, only the cwd walk applies).
- The `LLM Wiki` marker is matched literally on any line of `copilot-instructions.md`. A file that happens to contain the phrase in an unrelated context could produce a false positive — rare but possible.
- The project name is extracted from the first `# ... LLM Wiki` heading in `copilot-instructions.md`. If the signpost format changes, name extraction may return an empty string; downstream skills should tolerate this.
