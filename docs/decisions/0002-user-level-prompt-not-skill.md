# ADR-0002: User-level prompt, not skill, for `/new_llm_wiki_vault`

## Status
Accepted (2026-07)

## Context

The scaffold command (`/new_llm_wiki_vault`) must be available in Copilot Chat *before* the workspace it will operate on exists — its job is to *create* that workspace. This rules out any invocation mechanism scoped to an existing workspace.

VS Code Copilot supports two mechanisms for custom agent capabilities:
1. **Prompt files** (`.prompt.md`) — slash-commands, invocable at both **user level** (`VS Code User/prompts/`) and workspace level (`.github/prompts/`).
2. **Skills** (`SKILL.md` with `references/` bundling) — supports autonomous invocation from `description`, but is **workspace-scoped only** in Copilot (`.github/skills/` or `.claude/skills/`). No user-level equivalent.

Claude Code supports user-level skills at `~/.claude/skills/`, but Claude Code is not the primary target host.

## Decision

`/new_llm_wiki_vault` is distributed as a **user-level VS Code prompt file**, installed by `./bin/install.sh` into the VS Code User prompts folder. It is not packaged as a skill.

## Consequences

**Positive**
- The command is available in *any* workspace, including empty ones and non-git directories — exactly what a scaffolder needs.
- Install-once experience: one `./bin/install.sh` and every future workspace has the command.
- Explicit invocation model: the user knows they are creating a vault when they type `/new_llm_wiki_vault`. No autonomous auto-invocation risk.
- `argument-hint` provides guided input for the vault path parameter.
- Uniform Copilot mechanism, no cross-host adaptation needed for the primary use case.

**Negative**
- No autonomous invocation. A user saying "create a wiki for my Tolkien reading" in chat will not auto-trigger the scaffolder — they must invoke the slash-command explicitly. Acceptable given this is a deliberate, high-impact action (creates a directory tree).
- No `references/` progressive disclosure — the prompt is monolithic. Manageable at current size (~150 lines); revisit if it grows past ~300 lines.

**Neutral**
- Claude Code users do not get autonomous invocation on their host. They can still invoke `scaffold.py` directly from the CLI.

## Alternatives considered

- **Copilot workspace-level skill (`.github/skills/`)** — rejected because the target directory does not yet exist at scaffold time. Would require the user to set up a scratch workspace first, defeating the "install once, use anywhere" model.
- **Copilot workspace-level prompt (`.github/prompts/`)** — same rejection reason.
- **Claude Code user-level skill (`~/.claude/skills/`)** — deferred, not rejected. Adding a Claude skill alongside the Copilot prompt would give autonomous invocation on that host with a ~150-line wrapper that delegates to the same `scaffold.py`. Worth revisiting if Claude Code becomes a routine alternative surface. Noted in [README.md](../../README.md) "Future ideas".
- **VS Code extension** — rejected; huge development cost, and prompts already do the job. Noted in [README.md](../../README.md).
