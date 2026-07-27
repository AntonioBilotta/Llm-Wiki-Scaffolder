# ADR-0004: Three fixed roles: reader, maintainer, auditor

## Status
Accepted (2026-07)

## Erratum (2026-07, post ADR-0012)

The original text below describes the three roles as **workflow-complete agents** (each agent's body contains the full numbered workflow for its verb: QUERY / INGEST / LINT). Under [ADR-0012](0012-orchestration-skills-and-agent-delegation.md), agents are refactored as **domain-personality layers** on top of user-level orchestration skills (`wiki-query`, `wiki-ingest`, `wiki-lint`):

- The **three roles remain** — the reader/maintainer/auditor distinction, their tools frontmatter, and their runtime enforcement (reader has no `edit/editFiles`; auditor has `edit/editFiles` but prompt-body forbids creating new pages) are unchanged.
- What **changed**: the workflow logic moved from agent body to orchestration skill body. Agent bodies now contain `## Constraints` (domain rules) + `## Delegation` ("apply the wiki-X skill") + `## When to override` (inline escape hatch for domain-specific deviation the skill can't express).
- **Net effect**: same three roles, thinner bodies, workflow in a single source of truth.

The conclusion of ADR-0004 (three fixed roles, no rename per domain) stands unchanged. Only the internal representation of what a role "does" evolved.

## Context

The Karpathy LLM Wiki pattern describes three distinct operations against the wiki:

1. **Ingest** — read a raw source, integrate into the wiki, update cross-references, flag contradictions.
2. **Query** — answer questions using the wiki as source of truth, with citations.
3. **Lint** — health-check the wiki: contradictions, orphans, missing cross-references, stale claims, coverage gaps, frontmatter integrity.

These three operations differ substantially in their **write authority**:
- Ingest: broad write access to `wiki/` (creates entities, updates concepts, appends to log).
- Query: read-only, with a narrow exception for archiving substantive answers to `wiki/analysis/`.
- Lint: no content write; only frontmatter repairs and meta-callout additions (`> [!warning] Contradiction:`).

Bundling all three into one agent risks the "swiss army chatbot" failure mode: an LLM that reads too generously, edits too eagerly, and audits too shallowly because no constraints are context-specific.

## Decision

Three separate agent files, each with tightly scoped constraints:

- **`wiki-reader.agent.md`** — read-only, except may create pages under `wiki/analysis/`.
- **`wiki-maintainer.agent.md`** — writes to `wiki/` only; never touches `raw/`; follows the 8-step INGEST workflow.
- **`wiki-auditor.agent.md`** — may repair unambiguous frontmatter metadata and add meta-callouts inline, but never edits page content and never deletes files unilaterally.

The three roles are **fixed at scaffold time**. The scaffolder does not offer a mechanism to add, remove, or rename roles.

## Consequences

**Positive**
- Constraints are role-specific and mutually consistent. Each agent's `## Constraints` block is short and enforceable.
- Cross-agent invocation is well-defined: `@wiki-maintainer` invokes `@wiki-auditor` as a subagent at the end of a batch-ingest. Roles compose, they don't overlap.
- Predictability across vaults: any user familiar with one scaffolded vault knows exactly what the three roles do in every other scaffolded vault.
- The `AGENTS.md` bridge for non-Copilot assistants (Codex, OpenCode, Aider, Cursor) maps cleanly onto three roles rather than a variable-shape team.
- Maps 1:1 onto the three canonical Karpathy verbs — no impedance mismatch between the pattern documentation and the implementation.

**Negative**
- Vaults with domain-specific needs that would benefit from additional roles (e.g. a "translator" role for multilingual sources, a "citation-formatter" role for academic vaults) must add those manually in that specific vault, not at scaffold time.
- Users who dislike the three-role split cannot opt out via a scaffolder flag — they would have to edit the vault after generation.

**Neutral**
- The tight scoping is the point. If the constraint feels restrictive, that is a design feature, not a bug.

## Alternatives considered

- **Single unified `@wiki` agent** — rejected. Constraints become a laundry list of conditionals ("read-only unless X; may write to Y unless Z"). Hard to enforce, hard to reason about.
- **Configurable role set at scaffold time** (`--roles reader,maintainer,auditor,translator`) — rejected. Introduces cross-vault drift: users would have to check which roles exist in which vault. The tool's value is a *predictable* vault shape.
- **Two roles (reader + writer)** — rejected. Collapses maintainer and auditor into one, losing the distinction between "makes edits based on new sources" and "checks health without changing content". The distinction has proven useful: auditor can safely be invoked periodically without risk of content drift.
- **Four+ roles** — considered and deferred. If a natural fourth role emerges from usage (e.g. a dedicated archival role for `wiki/analysis/`), it can be added later. Currently the archival step is folded into the reader's workflow, which is sufficient.
