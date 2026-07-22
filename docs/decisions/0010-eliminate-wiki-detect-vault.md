# ADR-0010: Eliminate wiki-detect-vault; use auto-loaded copilot-instructions.md as authoritative source for `vault_path`

## Status
Accepted (2026-07)

## Context

Under Model D ([ADR-0009](0009-evaluate-user-level-vault-operational-customizations.md)) the initial skill catalog included `wiki-detect-vault` — a "pure reasoning" skill whose job was to walk up from CWD looking for a `.github/copilot-instructions.md` file marked as an LLM Wiki, handle multi-root workspace disambiguation, and return an absolute `vault_path` for the caller to pass to subsequent skills.

Post-pilot analysis exposed problems:

1. **Token cost.** The `wiki-detect-vault` SKILL.md was ~1500-2000 tokens loaded on every workflow invocation. Documented in [ADR-0011](0011-skill-token-optimization-strategies.md).
2. **Ecosystem mismatch.** A survey of consolidated user-level skill/CLI patterns showed no analog:
   - **OpenSpec** (`@fission-ai/openspec`, 62k stars) resolves the target from CWD via its CLI — no walk, no marker detection.
   - **Anthropic Agent Skills gallery** (163k stars): all documented skills take an explicit path argument (e.g. *"Use the PDF skill to extract the form fields from `path/to/some-file.pdf`"*). No skill in the gallery does ancestor-walk detection.
   - **Claude Code, git, npm, uv, cargo, kubectl, aws-cli, etc.** — all use either CWD-anchored + config file, or explicit `--target` flag. None speculatively walk in search of workspace markers.
3. **Stateless-skills principle.** The [Anthropic Agent Skills spec](https://agentskills.io) is explicit that skills are stateless functions of their arguments. A "detection" skill that walks the filesystem, consults workspace-folder APIs, and asks the user to disambiguate is fundamentally at odds with this principle — it is a stateful side-effect wrapped in a skill interface.
4. **VS Code already provides the mechanism.** The scaffolder writes `.github/copilot-instructions.md` at vault creation time, and this file is **auto-loaded** by VS Code Copilot whenever the model operates in that workspace. Adding one `## Vault / **Path:**` field to that file makes the vault path "pre-loaded in context" for free.

## Decision

**Delete the `wiki-detect-vault` skill. Adopt the pattern where `vault_path` is authoritative in the workspace's auto-loaded `.github/copilot-instructions.md`.**

Concretely:

- `templates/copilot-instructions.md` gains a `## Vault` section:
  ```markdown
  ## Vault
  - **Path:** `{{VAULT_PATH}}`
  - **Type:** `{{DOMAIN_TYPE}}`
  ```
- `bin/scaffold.py` gains `{{VAULT_PATH}}` in its substitution mapping, filled with `vault.resolve()` (absolute path).
- The 3 user-level prompts (`/wiki-ingest`, `/wiki-lint`, `/wiki-query`) and the 3 optional vault-level agents (`@wiki-reader`, `@wiki-maintainer`, `@wiki-auditor`) resolve `vault_path` from the auto-loaded instructions at step 1 of their workflow — no skill invocation needed.
- The 8 remaining wiki-* skills continue to receive `vault_path` as an explicit argument from the caller (unchanged from before).
- `bin/install.sh` / `install.ps1` gain legacy cleanup: remove `~/.copilot/skills/wiki-detect-vault/` (and mirrors in `~/.claude/skills/`, `~/.agents/skills/`) if present from a previous install.

## Consequences

**Positive:**

- **-1 skill** (9 → 8). Simpler catalog, less to document.
- **~2000 tokens saved per `/wiki-*` workflow invocation** (the wiki-detect-vault body is no longer loaded).
- **Zero detection cost.** The path is in the always-loaded instructions; the model reads it directly.
- **Aligned with consolidated ecosystem pattern** (OpenSpec, Anthropic skills gallery, CLI conventions).
- **Aligned with stateless-skills principle** (Anthropic Agent Skills spec).
- **Simpler mental model**: "vault path is a fact about the workspace, documented in copilot-instructions.md, not a computation to run".
- **Supersedes most of ADR-0011**: the primary detection optimization is achieved architecturally (skill removal) instead of via env var + progressive disclosure.

**Negative:**

- **Lost use case: cross-workspace random invocation.** A user editing files in a random workspace with no wiki loaded cannot `/wiki-query "..."` and have the tool walk their filesystem to find a vault. Mitigation: (a) most users open the vault workspace directly or use multi-root; (b) explicit `--vault=<path>` flag can be added to slash commands if the use case turns out to matter in practice.
- **Multi-root with multiple vaults still ambiguous** — but this was ambiguous under the previous approach too; the disambiguation logic just moves from the skill body to the prompt body.
- **Existing vaults need one-time manual update.** `--upgrade` does not overwrite existing `.github/copilot-instructions.md` (that would clobber user-added content). Deployed vaults need the `## Vault` block added manually. Documented in the README migration note.

## Migration

For existing vaults scaffolded before this ADR:

1. Manually add the following block to `<vault>/.github/copilot-instructions.md`, near the top (right after the intro paragraph):
   ```markdown
   ## Vault
   - **Path:** `<absolute path to the vault root>`
   - **Type:** `<domain type, e.g. learning>`
   ```
2. Re-run `bash bin/install.sh` (or `install.ps1` on Windows) to install the updated skills, remove `wiki-detect-vault` from `~/.copilot/skills/` (and mirrors), and install the updated prompts.
3. If the vault has agent files (`.github/agents/wiki-*.agent.md`), delete them and re-run `scaffold.py --upgrade --with-agents` to regenerate from the updated templates.

## Alternatives considered

**A. Keep `wiki-detect-vault`, add `disable-model-invocation: true` + progressive-disclosure `references/` split (from ADR-0011 optimization 1+3).** Rejected: still loads ~500 tokens per invocation, still requires "detection" logic that is stateful side-effect masquerading as a skill.

**B. Keep `wiki-detect-vault`, add `LLM_WIKI_ACTIVE_VAULT` env var + `~/.config/llm-wiki/vaults.yaml` (from ADR-0011 optimization 1).** Rejected: introduces new configuration surface for a problem VS Code already solves via auto-loaded instructions.

**C. Refactor to CLI+CWD pattern (OpenSpec-style: `llm-wiki` CLI installed via pipx/npm).** Deferred: significant refactor (breaks ADR-0001 stdlib-only distribution), loses cross-workspace calling, and the current pattern with auto-loaded instructions solves the immediate problem without requiring CLI redistribution. Revisit if the pattern proves insufficient at multi-vault scale.

## References

- [ADR-0009](0009-evaluate-user-level-vault-operational-customizations.md) — Model D architecture, original wiki-detect-vault design
- [ADR-0011](0011-skill-token-optimization-strategies.md) — Skill token optimization strategies (now superseded by this ADR)
- [Anthropic Agent Skills spec](https://agentskills.io) — stateless-skills principle
- [Fission-AI/OpenSpec](https://github.com/Fission-AI/OpenSpec) — reference for CWD-anchored pattern (alternative C)
- [anthropics/skills](https://github.com/anthropics/skills) — reference for explicit-path-arg pattern
