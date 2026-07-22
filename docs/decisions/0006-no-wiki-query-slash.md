# ADR-0006: No `/wiki-query` slash-command; `@wiki-reader` stays a mention

## Status
Accepted (2026-07)

## Context

The Karpathy pattern defines three canonical operations: **Ingest / Query / Lint**. In the current design, two are exposed as slash-commands (`/wiki-ingest`, `/wiki-lint`) and one as a mention (`@wiki-reader`). This asymmetry raises the question: should we add `/wiki-query` for symmetry and discoverability?

Arguments in favor of adding it:
- Symmetry with the three Karpathy verbs.
- Discoverability via the slash-picker.
- Ability to encode flags like `--archive` (force archival), `--format table|slides` (output shape).

Arguments against:
- Queries are inherently conversational; a slash-command implies one-shot invocation.
- `@participant` is the VS Code Copilot idiom for role-based chat.
- A thin wrapper adds a file to maintain across template upgrades for no semantic gain.

## Decision

**Do not add `/wiki-query`.** `@wiki-reader "..."` remains the query invocation. The reader agent already supports the "archive substantive answers" step (step 4 of its QUERY workflow), conditioned on user approval.

If a genuine need for a compulsory-archival query emerges, the right answer is a **narrower** slash-command like `/wiki-archive "<question>"` — semantically distinct from a plain query — rather than a generic `/wiki-query` wrapper.

## Consequences

**Positive**
- No redundant thin-wrapper prompt file to keep in sync.
- The mention preserves the conversational nature of queries: the reader can ask clarifying questions, propose archival, refine the answer across turns.
- The distinction between the three verbs is preserved semantically: ingest and lint are one-shot rituals with structured input/output; query is a dialogue.
- Leaves room for a more valuable future slash-command (`/wiki-archive`) whose only job is to skip the "propose archival + wait for approval" step and always write to `wiki/analysis/` — a genuine ritual compression.

**Negative**
- Breaks the "3 slash-commands for 3 Karpathy verbs" symmetry. Some users may initially look for `/wiki-query` and not find it. Mitigated by clear documentation in [README.md](../../README.md) and [ARCHITECTURE.md](../../ARCHITECTURE.md).
- No `argument-hint` guidance for query input. Acceptable — queries are free-form and don't benefit from typed hints the way `<path>` does for ingest.

**Neutral**
- If usage evolves to routinely require force-archival, revisit and add `/wiki-archive` (not `/wiki-query`).

## Alternatives considered

- **Add `/wiki-query "<question>"` as a symmetric wrapper** — rejected. Provides no capability the mention doesn't already have; adds a maintained file; dilutes the "prompt = one-shot ritual" signal.
- **Add `/wiki-query --archive "<question>"`, `--format table`, etc.** — deferred. Interesting only if users routinely need those flags. Current usage doesn't demonstrate the need.
- **Add `/wiki-archive "<question>"` (compulsory-archival variant)** — deferred, not rejected. Genuinely distinct from the mention (skips approval), aligned with the Karpathy "compound explorations back into the wiki" idea. Add if the archival step feels like recurring friction.
- **Rename `@wiki-reader` to something more inviting** — out of scope for this ADR; the name aligns with the "reader/maintainer/auditor" role naming ([ADR-0004](0004-three-fixed-roles.md)).

## Erratum (2026-07)

The Context and Decision sections of this ADR reflect the pre-[ADR-0009](0009-evaluate-user-level-vault-operational-customizations.md) architecture, in which prompts delegated to vault-level agents via `agent:` frontmatter. Under that constraint, `/wiki-query` would have been a thin wrapper reintroducing cross-workspace fragility — the argument against it held.

Under **Model D** (formalized in ADR-0009), prompts are self-contained user-level orchestrators of skills, with no `agent:` delegation. This changes the trade-off:

- **Cross-surface use** (Copilot CLI, third-party skills like OpenSpec composing wiki operations) benefits from a one-shot programmatic entry point that does not require a vault workspace to be active.
- **The Ingest/Query/Lint symmetry closes cleanly** — 2 of 3 slash-commands (`/wiki-ingest`, `/wiki-lint`) already existed under Model D; the missing 3rd was Query.
- `@wiki-reader` remains as vault-level agent for interactive conversational use with domain guardrails (spoiler-safe reading, PII redaction, ADR format). It is **not** replaced.

**Decision update**: `/wiki-query` is added as a **user-level prompt** — self-contained, orchestrates skills directly, no agent delegation. It coexists with `@wiki-reader`:

- `/wiki-query <question> [--archive]` — one-shot orchestrator, cross-surface, generic behavior. Lives at [prompts/wiki-query.prompt.md](../../prompts/wiki-query.prompt.md).
- `@wiki-reader` — vault-level agent (optional per Model D `--with-agents`), interactive, applies domain notes and tool restriction.

The original rejection of *"`/wiki-query` as a thin wrapper delegating to an agent"* **still stands** — that specific antipattern would still reintroduce cross-workspace dependency. The new `/wiki-query` avoids it by orchestrating skills directly.

Status remains `Accepted`, with the Decision widened per the above.
