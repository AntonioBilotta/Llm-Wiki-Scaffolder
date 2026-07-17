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
