---
description: "Run a full health-check on the LLM Wiki: contradictions, orphans, missing cross-references, stale claims, coverage gaps, frontmatter integrity. Produces a Lint Report and applies unambiguous frontmatter repairs. Self-contained via user-level skills — does not delegate to a vault-level agent."
argument-hint: "[scope=vault | scope=pages:<comma-separated>]"
---

Run a full LINT pass on the LLM Wiki. Compose user-level skills — do not delegate to a vault-level agent.

## Workflow

1. Invoke `wiki-detect-vault` to resolve the target vault. If a vault-level `@wiki-auditor` agent is active, it may intercept this prompt to apply its domain guardrails; follow it if so. Otherwise proceed with the steps below.

2. Invoke `wiki-lint-check` with `format=md` and any `${input:scope}` provided. Present the human-readable report to the user.

3. Invoke `wiki-lint-check` a second time with default JSON output (same scope). Parse the JSON, focusing on `findings.frontmatter` entries marked `auto_repairable: true`.

4. For each auto-repairable finding, apply the `proposed_fix` using the platform `edit` tool. Repair only frontmatter metadata — never edit page content in a lint pass.

5. For every other finding (contradictions, orphans, missing cross-refs, stale claims, missing pages, knowledge gaps, non-trivial frontmatter issues), surface them to the user in the report — do NOT act on them. These require user approval and typically fall under the maintainer's scope, not the auditor's.

6. Invoke `wiki-append-log` with `kind=lint`, `summary=<N> contradictions, <N> orphans, <N> stale, auto-repaired <N> frontmatter`.

## Output format

- The Markdown Lint Report from step 2 (as returned by `wiki-lint-check`).
- Below it, a **Repairs applied** section listing each auto-fix (page name + field + old value → new value).
- A **Pending user approval** section listing every non-auto-repairable finding with page name(s) and proposed action.

## Constraints

- **Auto-repair only** findings the skill explicitly marks `auto_repairable: true`. Never guess a repair.
- **Never delete files.** Duplicates, orphans, and obsolete pages are flagged for user approval, not removed automatically.
- **Never edit page content** — only frontmatter metadata, and only when unambiguous. Adding `> [!warning] Contradiction:` or `> [!warning] Stale:` callouts is allowed as meta-annotation, not content editing.
- **Every action is logged** via `wiki-append-log`.
