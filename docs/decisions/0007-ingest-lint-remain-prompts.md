# ADR-0007: `/wiki-ingest` and `/wiki-lint` stay prompts, not skills

## Status
Accepted (2026-07)

## Context

VS Code Copilot supports two formats for custom LLM capabilities:

1. **Prompt files** (`.prompt.md`) — explicit invocation via `/name`, structured `argument-hint`, delegation via `agent:` frontmatter.
2. **Skills** (`SKILL.md` + `references/` bundling) — autonomous invocation from `description` matching, progressive disclosure of on-demand asset files.

`/wiki-ingest` and `/wiki-lint` currently live as workspace-level `.prompt.md` files inside each scaffolded vault. Since they are already workspace-scoped, the distribution argument that ruled out skills for `/new_llm_wiki_vault` ([ADR-0002](0002-user-level-prompt-not-skill.md)) does **not** apply here — a conversion to skill format would be cost-neutral on the install side.

So the real question is: does autonomous invocation + `references/` modularity buy enough to justify swapping the format?

## Decision

**Neither prompt is converted to a skill.** Both `/wiki-ingest` and `/wiki-lint` remain `.prompt.md` files.

The `references/` modularity pattern (moving long-form assets to on-demand files) is **adopted separately** as an internal refactoring tool when files grow large — without switching format. Trigger: any single agent or prompt file exceeds ~200 lines, or a new domain type would make an existing table unwieldy.

## Consequences

**Positive**
- `argument-hint: "<path under raw/>"` remains for `/wiki-ingest` — the source path is a required, structured parameter that benefits from typed input.
- Explicit-invocation semantics preserved: `/wiki-ingest` unambiguously means "enter the canonical INGEST workflow and log it as `## [date] ingest | ...`". Autonomous invocation would blur this.
- Side-effects of lint (auto-repair frontmatter, add `> [!warning] Stale:` callouts) require user consent. A skill firing autonomously on a fuzzy signal would surprise users with unexpected edits.
- Delegation via `agent:` frontmatter (`agent: "wiki-maintainer"`, `agent: "wiki-auditor"`) is clean and deterministic. In skill format, it becomes prose inside SKILL.md — slightly less rigid.
- No cross-model behavior variance: slash-commands work identically across model providers; autonomous skill invocation depends on model-specific tuning.

**Negative**
- Users must remember to invoke `/wiki-lint` periodically; no automatic nudge. Acceptable — periodic maintenance is a user discipline, not something the tool should trigger unilaterally.
- No progressive disclosure of workflow assets. Acceptable at current file sizes; revisit if any agent/prompt file exceeds ~200 lines.

**Neutral**
- If autonomous-nudge behavior becomes valuable for lint, the right addition is an **ancillary** skill whose only job is to detect lint-worthy conditions (e.g. "N ingests since last lint pass") and suggest running `/wiki-lint`. It would not execute the lint itself, preserving user consent while gaining the nudge.

## Alternatives considered

- **Convert both to skills** — rejected. Loses `argument-hint`, loses ritual clarity, introduces autonomous-invocation surprise on writing operations.
- **Convert `/wiki-lint` only** (since it has no required argument) — rejected. Side-effects still require consent; the value of autonomy is weaker than the value of explicit-invocation discipline.
- **Adopt `references/` modularity now, without format switch** — accepted in principle, applied on-demand rather than eagerly. Candidates flagged in [README.md](../../README.md) "Future ideas": domain notes table, per-domain conventions, per-domain checklists.
- **Ancillary "lint nudge" skill alongside `/wiki-lint`** — deferred. Add if users report forgetting to lint. No signal yet.

## Erratum (2026-07)

Several factual claims in this ADR are inaccurate per current VS Code documentation ([Use Agent Skills in VS Code](https://code.visualstudio.com/docs/agent-customization/agent-skills)):

- The Consequences section lists *"`argument-hint: '<path under raw/>'` remains for `/wiki-ingest`"* as a positive of prompt files, implying skills do not support this. **Skills also support `argument-hint`** as a frontmatter field. This is not a differentiator.
- The "Alternatives considered" entry *"Convert both to skills — rejected. Loses `argument-hint`"* is likewise wrong on that specific point.
- The concerns about autonomous invocation on writing operations are **mitigable** by setting `disable-model-invocation: true` in the skill frontmatter, which forces manual `/`-invocation only.
- The Context section frames prompts as "workspace-level" as-is. Since [ADR-0009](0009-evaluate-user-level-vault-operational-customizations.md) proposes moving them to user-level, this framing is transitional. User-level skill installation is also supported (`~/.copilot/skills/`) and was not acknowledged.

**The decision to keep `/wiki-ingest` and `/wiki-lint` as prompt files still stands**, on the following narrower grounds that are unaffected by the corrections:

- Prompt files delegate to a role agent via `agent:` frontmatter — a first-class, deterministic mechanism. Skills express delegation in prose within `SKILL.md`, which is functionally equivalent but less rigid. This is the primary remaining reason.
- The verb/subject model documented in [ADR-0005](0005-prompt-vs-agent-invocation.md) maps naturally onto prompt-per-verb + agent-per-role. Keeping prompts preserves that mapping.
- The `references/` modularity benefit of skills remains real and is available independently of a format switch, as already noted in the Decision section.
