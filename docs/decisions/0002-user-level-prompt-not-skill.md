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

## Erratum (2026-07)

The Context section of this ADR states that Copilot skills are *"workspace-scoped only"* with *"no user-level equivalent"* and treats this as the primary reason to reject the skill format. Per current VS Code documentation ([Use Agent Skills in VS Code](https://code.visualstudio.com/docs/agent-customization/agent-skills)), this is inaccurate: personal skills at user profile level are supported at `~/.copilot/skills/`, `~/.claude/skills/`, and `~/.agents/skills/`. Whether this was always the case or the platform added support after this ADR was written is unclear from the docs; either way, the stated fact is wrong.

Related inaccuracies in the same section: skills support `argument-hint`, `user-invocable`, and `disable-model-invocation` frontmatter fields, meaning a skill can be configured to behave equivalently to a manually-invoked slash-command with typed arguments — removing the "autonomous invocation risk" as a hard blocker.

**The decision to use a prompt file for `/new_llm_wiki_vault` still stands**, on the following unchanged grounds:

- The prompt file is the simplest artifact for the job. No bundled scripts, no `references/`, no autonomous-invocation control needed — a skill would be a heavier abstraction for equivalent behavior.
- No delegation to a role agent is involved (there is no vault-side agent yet at scaffold time), so the `agent:` frontmatter advantage relevant to [ADR-0007](0007-ingest-lint-remain-prompts.md) does not apply here — but neither does any skill-specific advantage.

The "Alternatives considered" list should be read with this correction: user-level Copilot skills are a technically viable alternative that was not evaluated at the time. They remain unadopted on the grounds above rather than on impossibility.
- **VS Code extension** — rejected; huge development cost, and prompts already do the job. Noted in [README.md](../../README.md).
