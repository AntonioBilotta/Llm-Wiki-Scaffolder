---
name: wiki-lint
description: "Health-check the LLM Wiki — contradictions, orphans, missing cross-references, stale claims, coverage gaps, frontmatter integrity, source fidelity (numbers, dates and quotes grepped back in raw files). Composes the wiki-lint-check skill (twice: MD for human report + JSON for auto-repair parsing) and wiki-append-log. Applies unambiguous frontmatter repairs; flags everything else for user approval. Trigger keywords - 'lint the wiki', 'check wiki health', 'audit the wiki', 'find contradictions in the wiki', '/wiki-lint', 'run a health check on the wiki'."
argument-hint: "[scope=vault | scope=pages:<comma-separated>]"
---

# wiki-lint

Run a full LINT pass on the LLM Wiki. Composes user-level atomic wiki-* skills; does not delegate to a vault-level agent (but respects one if active — see step 1).

## Workflow

1. **Resolve `vault_path`** — first match wins, no upward filesystem walk: (1) the `vault_path` argument; (2) the `**Path:**` field under `## Vault` in the signpost already in context — `.github/copilot-instructions.md` (VS Code Copilot) or `AGENTS.md` (via the vault's `CLAUDE.md` in Claude Code; Codex, Cursor, Aider) — falling back to the directory containing that signpost if the absolute path does not exist in this environment; (3) the folder the user named or the current working directory, if it contains `wiki/` and an `AGENTS.md` or `.github/copilot-instructions.md` mentioning "LLM Wiki"; (4) otherwise ask the user (list the candidates if several vaults are in context). Full rule: `wiki-ingest` Preflight step 1.
   Then read `<vault_path>/.github/instructions/wiki-conventions.instructions.md` unless your runtime auto-loaded it (VS Code Copilot does; Claude Code and others do not).
   If a vault-level `@wiki-auditor` agent is active in the current chat, it may take precedence to apply its domain guardrails; follow it if so. Otherwise proceed with the steps below.

2. Apply `wiki-lint-check` with `vault_path=<from step 1>`, `format=md`, and any `scope` provided as argument. Present the human-readable report to the user.

3. Apply `wiki-lint-check` a second time with `vault_path=<...>` and default JSON output (same scope). Parse the JSON, focusing on `findings.frontmatter` entries marked `auto_repairable: true`.

4. For each auto-repairable finding, apply the `proposed_fix` using file-edit tools. Repair only frontmatter metadata — never edit page content in a lint pass.

5. For every other finding (contradictions, orphans, missing cross-refs, stale claims, missing pages, knowledge gaps, non-trivial frontmatter issues, source-fidelity mismatches, evidence errors, unreferenced raw files), surface them to the user in the report — do NOT act on them. Fidelity mismatches are never auto-repaired: a wrong number is fixed by the maintainer against the raw file, not by lint. These require user approval and typically fall under the maintainer's scope, not the auditor's.

6. Apply `wiki-append-log` with `vault_path=<...>`, `kind=lint`, `summary=<N> contradictions, <N> orphans, <N> stale, <N> fidelity, <N> evidence errors, auto-repaired <N> frontmatter`.

## Output format

- The Markdown Lint Report from step 2 (as returned by `wiki-lint-check`).
- Below it, a **Repairs applied** section listing each auto-fix (page name + field + old value → new value).
- A **Pending user approval** section listing every non-auto-repairable finding with page name(s) and proposed action.

## Constraints

- **Auto-repair only** findings the skill explicitly marks `auto_repairable: true`. Never guess a repair.
- **Never delete files.** Duplicates, orphans, and obsolete pages are flagged for user approval, not removed automatically.
- **Never edit page content** — only frontmatter metadata, and only when unambiguous. Adding `> [!warning] Contradiction:` or `> [!warning] Stale:` callouts is allowed as meta-annotation, not content editing.
- **Every action is logged** via `wiki-append-log`.

## Gotchas

- The atomic `wiki-lint-check` and `wiki-append-log` skills this workflow composes have `user-invocable: false` — hidden from the `/` menu but callable by explicit name from this orchestrator.
- Step 4 uses file-edit tools directly (not a skill) because frontmatter auto-repair is a targeted single-file operation and doesn't warrant its own atomic skill.
