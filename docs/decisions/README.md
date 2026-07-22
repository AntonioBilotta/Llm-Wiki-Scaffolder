# Architecture Decision Records

Design decisions taken during the evolution of `llm-wiki-scaffolder`, in [MADR](https://adr.github.io/madr/)-style format.

## Conventions

- **Immutable once accepted.** A decision that is later reversed does not edit the old ADR — it creates a new one with `Status: Supersedes ADR-XXXX`, and the old one becomes `Status: Superseded by ADR-YYYY`.
- **Numbered progressively.** Filenames follow `NNNN-kebab-case-title.md`. Numbers are never reused.
- **One decision per file.** If a change bundles multiple decisions, split into multiple ADRs.
- **Small and specific.** An ADR is not a design doc — it captures *one* choice with its alternatives and consequences. Broader architecture goes in [../../ARCHITECTURE.md](../../ARCHITECTURE.md).

## Template

```markdown
# ADR-NNNN: <Short title>

## Status
Proposed | Accepted (YYYY-MM) | Superseded by ADR-XXXX | Deprecated

## Context
The problem, the constraints, the forces at play.

## Decision
The choice made, in one or two sentences.

## Consequences
Positive, negative, neutral outcomes of the decision.

## Alternatives considered
Options rejected, with reasons.
```

## Index

| # | Title | Status |
|---|---|---|
| [0001](0001-python-stdlib-only.md) | Python stdlib only for `scaffold.py` | Accepted |
| [0002](0002-user-level-prompt-not-skill.md) | User-level prompt, not skill, for `/new-llm-wiki` | Accepted |
| [0003](0003-deterministic-scaffold-llm-fill.md) | Deterministic scaffold + LLM semantic fill split | Accepted |
| [0004](0004-three-fixed-roles.md) | Three fixed roles: reader, maintainer, auditor | Accepted |
| [0005](0005-prompt-vs-agent-invocation.md) | Prompt vs agent — invocation model | Accepted |
| [0006](0006-no-wiki-query-slash.md) | No `/wiki-query` slash-command; `@wiki-reader` stays a mention | Accepted |
| [0007](0007-ingest-lint-remain-prompts.md) | `/wiki-ingest` and `/wiki-lint` stay prompts, not skills | Accepted |
| [0008](0008-windows-support.md) | Windows support | Accepted |
| [0009](0009-evaluate-user-level-vault-operational-customizations.md) | Evaluate migrating vault operational customizations to user-level | Executed |
| [0011](0011-skill-token-optimization-strategies.md) | Skill token optimization strategies (deferred) | Proposed |
