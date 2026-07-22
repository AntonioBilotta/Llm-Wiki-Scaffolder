# ADR-0009: Evaluate migrating vault operational customizations to user-level

## Status
Executed (2026-07) — Phase A/B/C/C+/C++/C+++ shipped, validated end-to-end via `/wiki-ingest` on the dev-second-brain pilot vault.

## Erratum (2026-07, post-pilot correction)

The original text of this ADR (below) repeatedly claimed that agents provide **"platform-enforced tool restriction"** by listing user-level skills in their `tools:` frontmatter (e.g. reader's `tools:` excluding `wiki-write-source-page`). This claim is **incorrect**.

VS Code Copilot's `tools:` frontmatter is an allowlist of **toolset names** (`codebase`, `search`, `editFiles`, `runCommands`, `agent`, …) or namespaced tool IDs (`search/codebase`, `edit/editFiles`, `execute/runInTerminal`, `read/terminalLastCommand`, …). It does NOT accept skill names. Skills are a different mechanism — `SKILL.md` files auto-loaded as instructions when their `description` matches the current task semantically; they are playbooks, not endpoints.

Consequence: our Phase C agent templates (and the initially deployed vault agents) listed skill names in `tools:`, which VS Code silently dropped, effectively leaving the agents **unrestricted** — the opposite of the intent. An intermediate Phase C++ fix using individual tool IDs (`read_file`, `create_file`, `run_in_terminal`) partially worked in VS Code Agent Mode but failed in Copilot CLI where several IDs were silently dropped.

**Final correction (Phase C+++, validated end-to-end via `/wiki-ingest` pilot):**

- Agent templates now use canonical toolset names in the **namespaced form** (`category/name`), consistently across all 3 agents:
  - **reader**: `tools: ['search/codebase', 'search', 'execute/getTerminalOutput', 'execute/runInTerminal', 'read/terminalLastCommand', 'read/terminalSelection']` — deliberately no `edit/editFiles` → runtime-enforced read-only for wiki content; archival writes go through skill Python scripts via the terminal toolsets.
  - **maintainer**: `tools: ['search/codebase', 'search', 'edit/editFiles', 'execute/getTerminalOutput', 'execute/runInTerminal', 'read/terminalLastCommand', 'read/terminalSelection', 'agent']` + `agents: [wiki-auditor]` — `agent` toolset in `tools:` is REQUIRED (per docs) for subagent dispatch, in addition to the top-level `agents:` field.
  - **auditor**: `tools: ['search/codebase', 'search', 'edit/editFiles', 'execute/getTerminalOutput', 'execute/runInTerminal', 'read/terminalLastCommand', 'read/terminalSelection']` — has `edit/editFiles` for callouts + frontmatter auto-repair; "no create new pages" restriction stays prompt-body only (toolset granularity cannot express "edit but not create").
- Both short form (`'codebase', 'editFiles', 'runCommands'`) and namespaced form (`'search/codebase', 'edit/editFiles', 'execute/runInTerminal'`) are accepted by VS Code Agent Mode. We chose the namespaced form uniformly for clarity (explicit category prefix) and to sidestep a deprecation warning observed on the short form in some VS Code builds.
- Skills are referenced in agent bodies via "apply the `X` skill" wording — not "invoke `X`" — to reflect the playbook semantics.
- **Runtime caveat**: `/wiki-*` prompts (having no `tools:` field of their own) inherit the current chat mode's toolset. Running `/wiki-ingest` in **Ask Mode** or **Copilot CLI without proper permissions** = no write tools regardless of what `@wiki-maintainer`'s frontmatter says. INGEST/LINT workflows require **Agent Mode**.
- **UX trade-off observed in pilot**: user-level skill Python scripts (under `~/.agents/skills/*/scripts/`) trigger Copilot CLI permission prompts each invocation (path-outside-workspace + terminal command + create-file in new subdirs). Once "always allow" is granted per pattern the friction disappears, but first-run UX is noisy. This is the cost of the composability + blast-radius safety this ADR chose.

The **conclusion of ADR-0009 stands**: Model D + Variant α remains the chosen architecture. Only the enforcement mechanism claim needed correction. Toolset-name allowlisting gives us the runtime-enforced read-only vs write distinction that Model D depends on.

## Context

Today, when `/new-llm-wiki` scaffolds a new vault, it materializes the full set of operational customization files inside the vault's `.github/` directory:

```
<vault>/.github/
├── copilot-instructions.md
├── instructions/wiki-conventions.instructions.md
├── agents/wiki-{reader,maintainer,auditor}.agent.md
└── prompts/wiki-{ingest,lint}.prompt.md
```

Each file receives placeholder substitution (`{{PROJECT_NAME}}`, `{{DOMAIN_TYPE}}`, `{{LANGUAGE}}`, `{{DOMAIN_SPECIFIC_CONVENTIONS}}`, `{{DOMAIN_EXTRA_TYPES}}`) at scaffold time. The result is a self-contained, portable vault — but with two structural costs:

1. **Template drift across vaults.** When the templates evolve, older vaults keep the old versions until the user runs `--upgrade` explicitly on each one. The `--upgrade` mode exists precisely because of this problem.
2. **Duplication of essentially-generic content.** The operational agents (reader/maintainer/auditor) and prompts (`/wiki-ingest`, `/wiki-lint`) contain almost no vault-specific information — only `{{PROJECT_NAME}}` interpolation. The vast majority of every file is identical across every scaffolded vault.

An alternative architecture — one hinted at by observation and confirmed by research (see below) — is to **install some or all of the operational files at user level** so that the vault-invariant parts are shared across every vault, while vault-specific parts remain in-place. Multiple concrete splits are possible; the Decision section below chooses one after evaluating them against the concrete pain point that triggered the ADR.

Additional driver (surfaced during discussion): the project is used in **VS Code multi-root workspaces alongside other tools that operate via Copilot skills** (e.g. OpenSpec). Those tools need to invoke wiki operations programmatically from folders where the wiki vault is not the active workspace. The current all-vault-level architecture makes this hard: agents and prompts in one folder's `.github/` are not visible to Copilot CLI running in another folder.

Before committing to (or rejecting) this migration, we need to answer two questions:

1. **Is the pattern reliable?** Do major AI-coding platforms support user-level customizations with reliable precedence and concatenation semantics?
2. **Do the trade-offs favor the migration for this project?** In particular: portability, cross-editor bridge, `applyTo` scope, and the migration cost itself.

## Decision

**Adopt Model D as the target architecture, staged behind a pilot.**

Model D splits customizations along three independent layers, each self-contained and functional without the others:

1. **Skills at user-level** (`~/.copilot/skills/`, `~/.claude/skills/`, `~/.agents/skills/`) — atomic capabilities (search, read-page, summarize-source, write-analysis, append-log, update-index, detect-vault). No knowledge of role, no multi-step workflow. Portable across VS Code chat, Copilot CLI, cloud agent, and callable from third-party skills such as OpenSpec.

2. **Prompts at user-level** (VS Code User prompts folder) — verb rituals (`/wiki-ingest`, `/wiki-lint`, `/new_llm_wiki`). **Self-contained**: no `agent:` frontmatter, no delegation to vault-level artifacts. The prompt body orchestrates user-level skills directly. This is the critical design choice that removes cross-workspace dependencies — if the prompt delegated to a vault-level agent, the whole point of moving to user-level would be defeated because the prompt would fail whenever run outside a vault workspace.

3. **Agents at vault-level** (`.github/agents/`, **optional**) — role personas with `{{PROJECT_NAME}}` interpolated and domain notes appended. Their `tools:` list includes user-level skills plus platform primitives. They compose user-level skills (Variant α) into more disciplined workflows with domain-specific guardrails (spoiler-safe reading, ADR format for development, redact PII for business/personal). Interactive-first via `@mention` in VS Code chat.

**Composition style (α chosen):** vault-level agents orchestrate the same user-level skills that prompts do. The workflow logic lives in the skills. Agents add tool restriction (platform-enforced via `tools:` frontmatter) and domain notes as role personality. This eliminates duplication between prompt and agent bodies — both are thin orchestrators over the same skill layer.

This ADR does *not* immediately restructure the templates. It records the design and a staged rollout plan: pilot on one existing vault, measure the residual concerns, then decide whether to generalize.

If the pilot confirms the benefits without unacceptable degradation, a follow-up ADR-0010 will document the concrete migration steps and mark this ADR's decision as executed. If the pilot reveals blocking issues, ADR-0010 will document the rejection with the observed evidence.

Until the pilot completes, the current architecture (all files at vault level, `--upgrade` mode active) remains the shipping default.

## Evidence: the pattern is canonical

Three primary sources — the official documentation of the three most-used AI coding platforms — converge on exactly this design.

### VS Code Copilot

From [Customize agent behavior in Visual Studio Code](https://code.visualstudio.com/docs/copilot/copilot-customization) and [Adding repository custom instructions](https://docs.github.com/en/copilot/customizing-copilot/adding-repository-custom-instructions-for-github-copilot):

- All customization types (`.instructions.md`, `.prompt.md`, `.agent.md`, `SKILL.md`, hooks) support both **user scope** and **workspace scope**. The Agent Customizations editor manages both.
- Precedence, verbatim: *"Personal instructions take the highest priority. Repository instructions come next, and then organization instructions are prioritized last. However, all sets of relevant instructions are provided to Copilot."* Merged, not overridden.
- Monorepo pattern: `chat.useCustomizationsInParentRepositories` walks up the folder tree to the `.git` root and collects customizations from every level, concatenated into context.

### Claude Code

From [How Claude remembers your project](https://code.claude.com/docs/en/memory):

Load order (broadest → most specific, all concatenated):

| Scope | Location | Documentation quote |
|---|---|---|
| Managed policy | `/Library/Application Support/ClaudeCode/CLAUDE.md` (macOS) | Organization-wide instructions |
| **User instructions** | **`~/.claude/CLAUDE.md`** | **"Personal preferences for all projects"** |
| **User rules** | **`~/.claude/rules/*.md`** | **"Personal rules … apply to every project on your machine"** |
| Project instructions | `./CLAUDE.md` or `./.claude/CLAUDE.md` | "Team-shared instructions for the project" |
| Local instructions | `./CLAUDE.local.md` | "Personal project-specific preferences" (gitignored) |

Directly relevant quotes:

- *"All discovered files are concatenated into context rather than overriding each other."*
- *"The `.claude/rules/` directory supports symlinks, so you can maintain a shared set of rules and link them into multiple projects."*
- *"To share personal instructions across worktrees, import a file from your home directory instead: `@~/.claude/my-project-instructions.md`."* — the `@import` syntax is designed for exactly this hybrid use case.

The Claude Code architecture is **essentially the target architecture of this ADR**, with different filenames.

### Cursor

From [Rules](https://cursor.com/docs/context/rules):

Four rule scopes, with explicit precedence:

- **User Rules** — global preferences, apply across all projects
- **Project Rules** — `.cursor/rules/*.mdc`, version-controlled per project
- **Team Rules** — dashboard-managed, cross-project
- **AGENTS.md** — markdown-only alternative, supports nested `AGENTS.md` in subdirectories with parent-child precedence

Verbatim: *"Team Rules → Project Rules → User Rules. All applicable rules are merged; earlier sources take precedence when guidance conflicts."*

### Synthesis

All three platforms:

1. Support user-scope and workspace-scope customizations simultaneously.
2. Concatenate them into the model context; do not force a binary choice.
3. Define an explicit precedence for conflict resolution.
4. Actively recommend the split (Claude Code's docs make this the *default* onboarding path).

The pattern the user proposed is therefore not exotic — it is the canonical architecture endorsed by the three main platforms.

## Target architecture (Model D)

### Layer 1 — Skills user-level (atomic capabilities)

Installed to `~/.copilot/skills/`, `~/.claude/skills/`, `~/.agents/skills/` by `install.sh` / `install.ps1`. Portable across all Copilot surfaces via the [Agent Skills open standard](https://agentskills.io/).

| Skill | Type | Purpose |
|---|---|---|
| `wiki-detect-vault` | read | Detect if cwd contains an LLM Wiki vault; auto-invokable via description matching |
| `wiki-search` | read | Search `wiki/index.md`, return relevant pages |
| `wiki-read-page` | read | Read a wiki page with frontmatter |
| `wiki-summarize-source` | read/output | Produce structured summary of a `raw/` source (no writes) |
| `wiki-write-source-page` | write single-file | Create `wiki/sources/<name>.md` |
| `wiki-write-analysis` | write single-file | Create `wiki/analysis/<title>.md` |
| `wiki-update-index` | write single-file | Update `wiki/index.md` |
| `wiki-append-log` | write single-file | Append to `wiki/log.md` |
| `wiki-lint-check` | read | Run 7-step audit checks, return report |

Write skills default to `disable-model-invocation: true` (must be explicitly orchestrated by a prompt, agent, or another skill). Read skills default to autonomous invocation via description matching. Each skill accepts an absolute vault path or defers to `wiki-detect-vault` for resolution.

### Layer 2 — Prompts user-level (verbs, self-contained)

Installed to VS Code User prompts folder by `install.sh` / `install.ps1`. **Do not delegate to agents.**

- `/new_llm_wiki` — scaffolder (unchanged from today)
- `/wiki-ingest <path>` — body orchestrates `wiki-summarize-source` → `wiki-write-source-page` → cross-reference updates → `wiki-update-index` → `wiki-append-log`. In folder mode, chronological ordering + final `wiki-lint-check` invocation.
- `/wiki-lint` — body orchestrates `wiki-lint-check` and applies unambiguous frontmatter repairs via the platform `edit` tool.

### Layer 3 — Agents vault-level (optional role guardrails)

Remain in `.github/agents/` **only when the domain warrants stricter guardrails**. Their `tools:` include user-level skills + `edit` + `agent` (for subagent invocation). Body composes the same skills as prompts, but adds:

- Role personality with `{{PROJECT_NAME}}` interpolation (unchanged from today)
- Domain notes appended by scaffolder for `reading_fiction`, `development`, `personal`, `business` (unchanged from today)
- Tool restriction platform-enforced (e.g. reader's `tools:` excludes `wiki-write-source-page` and other maintainer capabilities)
- Subagent composition: maintainer invokes auditor at end of batch (unchanged from today)

### Vault filesystem layout (Model D)

```
<vault>/
├── raw/                             # unchanged
├── wiki/                            # unchanged
├── .github/
│   ├── copilot-instructions.md      # signpost (unchanged), documents install.sh dependency
│   ├── instructions/
│   │   └── wiki-conventions.instructions.md   # unchanged, vault-level, applyTo unchanged
│   └── agents/                      # optional, only if --with-agents or sensitive domain
│       └── wiki-{reader,maintainer,auditor}.agent.md
├── AGENTS.md                        # unchanged, cross-editor bridge
└── .gitignore                       # unchanged
```

No `.github/prompts/` — prompts come from user-level install. `--upgrade` mode continues to handle updates to vault-level agents and conventions.

## Emergent properties

1. **Cross-surface uniformity.** VS Code chat and Copilot CLI have identical baseline capability via the user-level layers. VS Code chat additionally gets the role experience when agents are present in the current workspace folder.

2. **Composability with external skills.** OpenSpec (or any third-party skill) invokes `wiki-search`, `wiki-read-page`, `wiki-write-analysis` via description matching or explicit reference. Zero knowledge of the wiki's agent layer required.

3. **Zero prompt→agent cross-workspace dependency.** Removing `agent:` frontmatter from prompts eliminates the fragility of "prompt in openspec/ folder tries to call agent in llm-wiki/ folder". Prompts stand on their own.

4. **Agents become an opt-in strictness layer.** A minimal vault (`--minimal` scaffold, or `hobby` / `learning` domains by default) omits agents entirely: operations run through user-level prompt+skill with standard guardrails. Sensitive domains (`business`, `personal`) include agents by default for the extra tool restriction and domain notes.

5. **Graceful degradation for vault clone.** A vault cloned by someone without user-level skills installed still opens: `.github/copilot-instructions.md` documents the one-time install. If agents are present, they reference skills that fail cleanly rather than corrupting state.

## Trade-offs to validate in the pilot

Model D shrinks the pilot's scope compared to the earlier Model C proposal. Most of the original concerns either become non-issues or invert in Model D's favor. Two residual concerns remain non-trivial:

### 1. Skill dependency of vault-level agents (α composition)

Agents orchestrate user-level skills rather than containing workflow inline. **A vault cloned onto a machine without skills installed will see agents whose workflow references non-existent skills.**

**Mitigation:** `.github/copilot-instructions.md` signpost documents the one-time install (`bin/install.sh` or `bin/install.ps1`). The installer becomes the canonical bootstrapping step for full functionality.

**Pilot must measure:** whether "vault-clone without install" is a real user path in practice, or a theoretical concern. If real, add an `install-vault-local.sh` fallback that copies user-level skills into a vault-local location as a documented degraded mode.

### 2. Skills lack platform-enforced tool restriction

User-level skills do not have a `tools:` frontmatter equivalent to custom agents. A skill that is *supposed to* be read-only relies on textual instructions in `SKILL.md` rather than platform rejection. If the model misinterprets, damage is possible.

**Mitigation:** design write skills as *single-file, targeted* (`wiki-write-source-page` writes exactly one path; `wiki-append-log` only appends to one file). The blast radius of a misbehaving skill is capped at one file. Additionally, agents (where present) provide platform-enforced restriction by omitting write skills from the reader's `tools:` list.

**Pilot must measure:** whether any skill in practice performs unexpected writes; whether reliance on textual constraint is acceptable given the blast radius.

### 3. Cross-editor `AGENTS.md` bridge

**Under Model D:** agents stay vault-level (when present), so `AGENTS.md` continues to duplicate their content for Codex/Aider/Cursor as today. Cross-editor tools do not benefit from user-level Copilot skills (they don't consume the standard), but they can consume vault-level agents.

**Not a real change** vs today. This item is closed unless the pilot reveals that non-Copilot users want composability with wiki operations from their host's own tooling.

### 4. `applyTo` scope of `wiki-conventions.instructions.md`

**Under Model D:** instructions stay vault-level with `applyTo: "wiki/**,raw/**"` unchanged. **Not a change** vs today. Model C's marker-file requirement is avoided entirely. This item is closed.

### 5. Discoverability for contributors

**Under Model D:** contributors reading the vault see optional agents (when present) + signpost documenting where skills come from. Better than Model C's "vault sees only the manifest" outcome. This item is closed.

## Consequences (if adopted after pilot)

**Positive**
- **Composability with third-party skills** (OpenSpec, others) via the skill layer. Solves the concrete pain point that triggered this ADR.
- **Cross-surface uniformity.** `/wiki-ingest` works identically in VS Code chat and Copilot CLI from any folder. Skills work identically across Copilot in VS Code, Copilot CLI, and cloud agent.
- **Agents become an opt-in strictness layer.** Vault authors choose whether to add them based on domain sensitivity, rather than being forced into the current one-size-fits-all model.
- **Prompt→agent cross-workspace fragility eliminated.** Prompts self-contained.
- **Vault template still meaningful.** Agents remain vault-level when present; cross-editor bridge (`AGENTS.md`) largely unchanged. Retrocompatibility with today's ecosystem is high.
- **Migration is incremental.** Skills and user-level prompts are additive; vault-level prompts can be deprecated with a soft transition rather than a breaking change.

**Negative**
- **User-level install required for full functionality.** Cloning a vault alone is no longer sufficient; `install.sh` / `install.ps1` becomes a bootstrap step. Today the install is required for scaffolding — with Model D it becomes a prerequisite for vault operations as well.
- **Skills lack platform-enforced tool restriction.** Mitigated by single-file blast radius and by agent layer where present, but the theoretical risk exists.
- **Some duplication of orchestration logic between prompt and agent bodies.** Both invoke the same skills; agents add role personality and tool restriction. The workflow logic itself is in the skills, so the duplicated part is thin.

**Neutral**
- `--upgrade` mode remains relevant for vault-level agent updates (which continue to receive domain notes evolution over time), just less critical since the bulk of updates now happen via user-level `install.sh` re-run.

## Alternatives considered

- **Status quo** (all files at vault level, `--upgrade` handles drift) — currently shipping. Simple mental model, zero external dependencies for a cloned vault. Loses on DRY and, decisively, on cross-tool composability with skill-based third parties.

- **Model C: three-layer user-level split with vault manifest** — the earlier iteration of this ADR proposed installing skill+prompt+agent all user-level, with a vault-level `.wiki-vault.yaml` manifest holding project-specific parameters. **Rejected in favor of Model D** because: (a) required refactoring every agent template to be placeholder-free and to read from a new manifest format; (b) required a marker-file mechanism (`.wiki-vault` + special glob) to scope `applyTo` correctly; (c) required prompts to delegate to user-level agents via `agent:` frontmatter, and if any prompt were run in a context where the user-level agent were not available, the whole workflow would fail — reintroducing the cross-workspace dependency the ADR set out to remove; (d) discoverability regressed sharply (vault becomes just a manifest). Model D achieves the same composability wins with substantially less refactor and no manifest.

- **Model A: skill-only migration** — all operations become skills, agents disappear entirely. Rejected: loses platform-enforced tool restriction (critical for the maintainer's write-heavy workflow), loses role/persona semantics established in [ADR-0004](0004-three-fixed-roles.md).

- **Model B: hybrid without pilot** — ship both vault-level and user-level in parallel with precedence-based shadowing. Rejected: doubles surface area with no clear benefit, complicates the mental model.

- **Adopt only skills at user-level, keep prompts and agents vault-level** — skills would compose with OpenSpec but `/wiki-ingest` would still require per-vault install, negating half the win of moving to user-level. Rejected.

- **Variant β of Model D: thick agent with workflow inline** — vault-level agents contain the full 8-step INGEST workflow inline (as today), user-level skills exist as a separate capability API only for external composition. Pro: vault clone self-contained without skills. Con: duplication of workflow logic between agents (inline) and prompts (which would still need to orchestrate skills). **Rejected in favor of Variant α** for DRY — workflow logic lives in one place (the skills), both prompt and agent are thin orchestrators.

- **Move to Claude Code as primary host and adopt `@import` syntax natively** — out of scope; would re-host the entire project.

## Follow-up (planned)

- **Pilot scope** — one existing vault (candidate: an active `development` or `research` domain vault). Timebox: 2–3 weeks of active use. Acceptance criteria:
  1. **Composability**: OpenSpec skill invokes `wiki-search` and `wiki-write-analysis` from Copilot CLI in a sibling folder, with correct results and no user friction.
  2. **Cross-surface**: `/wiki-ingest raw/foo.md` produces identical vault state whether invoked from VS Code chat (vault folder active) or Copilot CLI (any folder, absolute path).
  3. **Graceful degradation**: cloning the vault on a machine without skills installed produces a working "read-only" state (`.github/copilot-instructions.md` signpost visible); running `install.sh` afterward reaches full parity.
  4. **Blast radius**: no skill performs a write outside its documented target path across the pilot period.

- **Implementation checklist** (executed only if pilot criteria are met):
  - Author 9 skill files (see Layer 1 table) under `templates/skills/`.
  - Author 2 user-level prompts (`wiki-ingest.prompt.md`, `wiki-lint.prompt.md`) that orchestrate skills; no `agent:` frontmatter.
  - Extend `install.sh` and `install.ps1` to install skills and user-level prompts alongside `/new_llm_wiki`.
  - Update `scaffold.py` to omit `.github/prompts/` from new vaults; add `--with-agents` / `--minimal` scaffold flags; keep `--upgrade` for agent updates.
  - Retrocompatibility path: existing vaults with `.github/prompts/` keep working (workspace-level shadows user-level with same effect).
  - Update [ARCHITECTURE.md](../../ARCHITECTURE.md) and [README.md](../../README.md).

- **ADR-0010** — post-pilot decision: approved with concrete plan (mark this ADR as Executed) or rejected with observed evidence (this ADR stays Proposed indefinitely or is closed as Rejected).

- **ADR-0011+** — as needed for sub-decisions (e.g. per-domain default for `--with-agents` vs `--minimal`, specific SKILL.md signatures, `install-vault-local.sh` fallback design).

## References

- [VS Code Copilot customization overview](https://code.visualstudio.com/docs/copilot/copilot-customization)
- [Use Agent Skills in VS Code](https://code.visualstudio.com/docs/agent-customization/agent-skills)
- [Custom agents in VS Code](https://code.visualstudio.com/docs/agent-customization/custom-agents)
- [Use prompt files in VS Code](https://code.visualstudio.com/docs/agent-customization/prompt-files)
- [Agent Skills open standard](https://agentskills.io/)
- [GitHub Copilot: Adding repository custom instructions](https://docs.github.com/en/copilot/customizing-copilot/adding-repository-custom-instructions-for-github-copilot)
- [Claude Code: How Claude remembers your project](https://code.claude.com/docs/en/memory)
- [Cursor: Rules](https://cursor.com/docs/context/rules)
- Related ADRs: [ADR-0002](0002-user-level-prompt-not-skill.md) (only the scaffold command is user-level today — this ADR widens that scope to skills and other prompts), [ADR-0007](0007-ingest-lint-remain-prompts.md) (prompts vs skills for ingest/lint — prompts remain, now composing user-level skills), [ADR-0004](0004-three-fixed-roles.md) (three fixed roles — preserved as optional agent layer in Model D)
