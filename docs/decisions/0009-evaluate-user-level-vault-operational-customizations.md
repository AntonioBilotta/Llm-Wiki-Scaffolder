# ADR-0009: Evaluate migrating vault operational customizations to user-level

## Status
Proposed (2026-07)

## Context

Today, when `/new_llm_wiki_vault` scaffolds a new vault, it materializes the full set of operational customization files inside the vault's `.github/` directory:

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

An alternative architecture — one hinted at by observation and confirmed by research (see below) — is to **install the generic operational files once at user level**, and keep only the project-specific parameters at vault level. The vault would then contain:

- `raw/` and `wiki/` (unchanged)
- A small manifest (name, domain type, extra folders, extra page types, domain conventions, language) at vault level
- No copies of the operational customizations

The generic customizations at user level would read the manifest at runtime and behave as if they were project-specific.

Before committing to (or rejecting) this migration, we need to answer two questions:

1. **Is the pattern reliable?** Do major AI-coding platforms support user-level customizations with reliable precedence and concatenation semantics?
2. **Do the trade-offs favor the migration for this project?** In particular: portability, cross-editor bridge, `applyTo` scope, and the migration cost itself.

## Decision

**Adopt the "generic at user-level + specific at vault-level" split as the target architecture, but stage the migration behind a pilot.** This ADR does *not* immediately restructure the templates. It records:

- The evidence that the pattern is canonical and well-supported.
- The design shape of the target architecture.
- A staged rollout plan: pilot on one existing vault, measure the real cost of the trade-offs, then decide whether to generalize.

If the pilot confirms the benefits without unacceptable degradation, a follow-up ADR (0010) will document the concrete migration steps and mark this ADR's decision as executed. If the pilot reveals blocking issues, an ADR-0010 will document the rejection with the observed evidence.

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

## Target architecture (design sketch)

If the migration completes successfully, the layout would become:

**User level (`~/.config/llm-wiki/` + VS Code User customization folders), installed once:**

- `bin/scaffold.py` — unchanged
- `bin/manifest_reader.py` or equivalent helper — reads the vault manifest
- Prompts installed to VS Code User prompts folder:
  - `new_llm_wiki.prompt.md` (as today)
  - `wiki-ingest.prompt.md` — *generic*, no `{{PROJECT_NAME}}`
  - `wiki-lint.prompt.md` — *generic*
- Agents installed to VS Code User agents folder:
  - `wiki-reader.agent.md`, `wiki-maintainer.agent.md`, `wiki-auditor.agent.md` — all generic
- Instructions installed to VS Code User instructions folder:
  - `wiki-conventions.instructions.md` — generic, with `applyTo` restricted via a vault-marker mechanism (see Trade-offs)

**Vault level (per-project), scaffolded:**

- `raw/`, `wiki/` — unchanged
- `.wiki-vault` marker file (empty) — signals "this workspace is a scaffolded LLM Wiki" to the user-level `applyTo` patterns
- `.github/wiki-vault.yaml` or equivalent — the manifest:
  ```yaml
  project_name: "MyProject"
  internal_type: "development"
  language: english
  extra_wiki_folders: [decisions, requirements]
  extra_page_types: [decision, requirement]
  domain_conventions: |
    Decisions follow ADR format...
  ```
- `.github/copilot-instructions.md` — minimal signpost (unchanged)
- `AGENTS.md` — cross-editor bridge (see Trade-offs for the strategy)

The generic agents read the manifest at runtime and behave as if project-specific. Placeholder substitution disappears from scaffold time; parameter resolution moves to runtime context injection.

## Trade-offs to validate in the pilot

These are the concerns that could block the migration. The pilot must generate concrete evidence on each.

### 1. Portability of a cloned vault

**Current behavior:** a cloned vault is self-contained. Any developer opening it in Copilot gets the operational agents immediately, because they live in `.github/`.

**After migration:** a cloned vault without the user-level install shows the vault structure but no operational commands. Impact depends on:
- How often vaults are cloned/shared vs single-user.
- Whether we ship an `./install-vault-agents.sh` fallback that copies user-level templates into `.github/` on demand.

**Pilot must measure:** the friction of onboarding a second machine or a collaborator.

### 2. Cross-editor `AGENTS.md` bridge

**Current behavior:** `AGENTS.md` at vault root contains full role instructions readable by Codex/OpenCode/Aider/Cursor without any install.

**After migration:** three options, none ideal:
- (a) `AGENTS.md` continues to duplicate the full instructions (defeats DRY).
- (b) `AGENTS.md` uses Claude-style `@~/.config/llm-wiki/agents/...` imports (only Claude honors this today).
- (c) `AGENTS.md` shrinks to a signpost pointing at the user-level path and assumes install.

**Pilot must decide:** which of (a)/(b)/(c) — or a hybrid (Cursor via nested AGENTS.md, Copilot via user-level, Claude via `@import`) — is acceptable for the user's actual cross-editor usage. If Copilot is the only real target, the question is moot.

### 3. `applyTo` scope leakage

**Current behavior:** `wiki-conventions.instructions.md` uses `applyTo: "wiki/**,raw/**"` — active only inside a scaffolded vault (those paths exist only there).

**After migration:** a user-level `applyTo: "wiki/**,raw/**"` fires on *any* workspace with `wiki/` or `raw/` directories, whether or not it's a scaffolded vault. This is unwanted.

**Mitigation:** introduce a marker file (e.g. `.wiki-vault` in vault root) and change `applyTo` to a pattern that references it — or use `applyTo: "**/.wiki-vault/../**"` if the glob engine supports parent references, or a two-file approach with a workspace-scope shim that re-anchors the user-level rules.

**Pilot must test:** whether the marker+glob mechanism actually restricts scope in practice on VS Code Copilot.

### 4. Discoverability for contributors

**Current behavior:** opening a vault in VS Code shows all operational files under `.github/`. A contributor can grep the workflow, understand what `/wiki-ingest` does, without knowing anything external.

**After migration:** the vault contains only the manifest. A contributor reading the vault sees nothing about the operational workflow — they have to know to look at `~/.config/llm-wiki/`.

**Mitigation:** the vault's `README.md` (or a `.github/README.md`) links explicitly to the user-level install and documents where the agents live.

### 5. Migration cost

- Refactor all placeholder-holding templates into placeholder-free generic files.
- Design and implement the manifest format + reader helper.
- Extend `install.sh` to install prompts, agents, and instructions to the user-level VS Code folders (not just prompts as today).
- Design and implement `scaffold.py --migrate-existing-vault <path>` that reads an existing vault's `.github/` files, extracts the parameters into a manifest, and removes the operational files.
- Update `AGENTS.md` bridge according to the outcome of trade-off #2.
- Rewrite ADR-0002 as `Superseded` or add a companion ADR explaining the widened scope (user-level is now for more than just the scaffold command).
- Update [ARCHITECTURE.md](../../ARCHITECTURE.md) diagram and text.
- Update [README.md](../../README.md).

## Consequences (if adopted after pilot)

**Positive**
- **Single upgrade point.** Improve a template → every vault benefits immediately. `--upgrade` mode disappears from the scaffolder.
- **Zero template drift.** All vaults run the same operational code by construction.
- **Vault leaner.** Only `raw/`, `wiki/`, manifest, signpost — ~5 files vs current ~10.
- **Alignment with industry-canonical pattern** (Claude Code, Copilot, Cursor).
- **New feature-development is faster.** Adding a workflow step to `@wiki-maintainer` no longer requires re-scaffolding vaults.

**Negative**
- **Vault is no longer self-contained.** Cloning requires an install step, or an explicit fallback script.
- **Cross-editor bridge complexity increases** — `AGENTS.md` strategy needs a definitive answer.
- **`applyTo` scoping requires a marker-file mechanism** — one more moving part.
- **Discoverability regresses** for contributors reading only the vault.
- **Migration cost is real** — see checklist above.

**Neutral**
- Users who prefer the current model can be supported by an install-time flag (`--vault-local-templates`) that reverts to embedding everything in `.github/` per vault.

## Alternatives considered

- **Status quo (all files at vault level, `--upgrade` handles drift)** — currently shipping. Simple mental model, zero external dependencies for a cloned vault. Loses on DRY and on upgrade friction as vault count grows.
- **Hybrid without pilot: ship both simultaneously** — installer copies generics to user-level *and* to `.github/`, with vault-level shadowing user-level via precedence. Rejected as bloat: doubles the surface area with no clear benefit.
- **Full immediate migration without pilot** — rejected as risky. The five trade-offs above are all real; committing before measuring at least one of them in production would likely produce an ADR-0010 reversing course.
- **Adopt only for prompts, not agents/instructions** — considered. Loses the biggest wins (DRY on agents is where duplication is largest). Would only remove ~2 files per vault. Not worth the split.
- **Move to Claude Code as primary host and adopt `@import` syntax natively** — out of scope for this ADR. Would resolve trade-off #2 by fiat, but re-hosts the entire project.

## Follow-up (planned)

- **Pilot definition** — pick one existing vault, define acceptance criteria for each of the 5 trade-offs, timebox the pilot (e.g. 2–3 weeks of active use).
- **ADR-0010** — post-pilot decision. Either "migration approved" (with concrete plan) or "migration rejected" (with observed evidence).
- If accepted: **ADR-0011+** as needed for the specific sub-decisions (manifest format, marker-file mechanism, `AGENTS.md` bridge strategy).

## References

- [VS Code Copilot customization overview](https://code.visualstudio.com/docs/copilot/copilot-customization)
- [GitHub Copilot: Adding repository custom instructions](https://docs.github.com/en/copilot/customizing-copilot/adding-repository-custom-instructions-for-github-copilot)
- [Claude Code: How Claude remembers your project](https://code.claude.com/docs/en/memory)
- [Cursor: Rules](https://cursor.com/docs/context/rules)
- Related ADRs: [ADR-0002](0002-user-level-prompt-not-skill.md) (only the scaffold command is user-level today — this ADR proposes widening that scope), [ADR-0007](0007-ingest-lint-remain-prompts.md) (prompts vs skills — orthogonal, both preserved)
