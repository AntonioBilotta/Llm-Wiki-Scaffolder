# ADR-0005: Prompt vs agent — invocation model

## Status
Accepted (2026-07)

## Context

The scaffolded vault exposes both `.prompt.md` files (slash-commands: `/wiki-ingest`, `/wiki-lint`) and `.agent.md` files (mentions: `@wiki-reader`, `@wiki-maintainer`, `@wiki-auditor`). This raises the natural question: what is the invocation model? When should a user reach for one versus the other?

Without a clear model, we risk two failure modes:
- Redundant surface area: every agent also has a slash-command wrapper, doubling the artifacts to maintain.
- Confused users: unclear when the slash-command is "the right way" versus a mention.

## Decision

Adopt the **verb/subject** model:

- **Prompt (`.prompt.md`) = verb.** Codifies a canonical operation. Slash-command invocation, `argument-hint` for typed input, explicit ritual, delegates to an agent via `agent:` frontmatter. Used when the user is performing one of the canonical Karpathy operations (Ingest, Lint).
- **Agent (`.agent.md`) = subject.** Codifies a role with constraints, tools, and workflows. Mention-based invocation, conversational, flexible. Used for non-standard maintenance, multi-turn negotiation, targeted subsets of an operation, or role-specific queries.

Concretely:

| Situation | Tool |
|---|---|
| "Add *this* source to the wiki" | `/wiki-ingest <path>` |
| "Run periodic health check" | `/wiki-lint` |
| "Discuss before writing; non-ingest maintenance op" | `@wiki-maintainer` |
| "Audit only *these* pages / *this* aspect" | `@wiki-auditor` |
| "Ask a question against the wiki" | `@wiki-reader` (no slash equivalent — see [ADR-0006](0006-no-wiki-query-slash.md)) |

Rule of thumb: **if the action would be logged as `## [YYYY-MM-DD] ingest \| ...` or `## [YYYY-MM-DD] lint \| ...` in `wiki/log.md`, use the slash-command.** If it's off that canonical path, invoke the agent directly.

## Consequences

**Positive**
- Clear mental model for users, mappable to a one-page rule.
- Slash-commands act as **workflow guardrails**: `/wiki-ingest` guarantees all 8 steps of the INGEST workflow run (including index/log update), which a casual `@wiki-maintainer` mention might skip.
- Agents remain **flexible primitives**: usable outside the canonical operations for ad-hoc tasks.
- Prompt files stay thin (delegation only), agent files stay rich (workflow + constraints). No content duplication.

**Negative**
- Users unfamiliar with the distinction might invoke `@wiki-maintainer` for a standard ingest and get slightly less disciplined execution than `/wiki-ingest` would guarantee. Documented in [README.md](../../README.md) and [ARCHITECTURE.md](../../ARCHITECTURE.md).
- No slash-command for query means the "3 verbs, 3 slash-commands" symmetry is broken (2 slashes + 1 mention). See [ADR-0006](0006-no-wiki-query-slash.md) for why we accept this.

**Neutral**
- The model does not preclude adding a new slash-command later if a genuine ritual emerges (e.g. `/wiki-archive` for compulsory-archival query — flagged as a candidate).

## Alternatives considered

- **Slash-command for every agent (`/wiki-query`, `/wiki-audit`, `/wiki-maintain`)** — rejected. Redundant surface area; most of these would be thin wrappers with no `argument-hint` benefit. Loses the "prompt = ritual" signal. Details for `/wiki-query` specifically in [ADR-0006](0006-no-wiki-query-slash.md).
- **Mentions only, no slash-commands** — rejected. Loses discoverability (slash-picker shows commands; mentions require knowing the name). Loses `argument-hint` for `/wiki-ingest`'s path parameter. Loses the workflow-guardrail effect.
- **Skills replacing prompts** — rejected. See [ADR-0007](0007-ingest-lint-remain-prompts.md).
