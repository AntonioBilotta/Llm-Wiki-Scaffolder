# llm-wiki-scaffolder

Deterministic scaffolder for **LLM Wiki** vaults following the [Karpathy pattern](templates/karpathy_llm_wiki_pattern.md). Installs user-level GitHub Copilot artifacts — the `/new-llm-wiki` scaffold prompt and 11 skills at `~/.copilot/skills/`, `~/.claude/skills/`, and `~/.agents/skills/` (3 orchestration skills exposed as `/wiki-ingest`, `/wiki-lint`, `/wiki-query` + 8 hidden atomic primitives they compose) — backed by a stdlib-only Python script.

An LLM Wiki is a persistent, LLM-maintained knowledge base: `raw/` holds immutable sources, `wiki/` holds LLM-owned markdown (entities, concepts, sources, analysis, plus domain-specific folders), and the LLM keeps the wiki up-to-date as new sources are added. Under the Model D architecture ([ADR-0009](docs/decisions/0009-evaluate-user-level-vault-operational-customizations.md)) refined by [ADR-0012](docs/decisions/0012-orchestration-skills-and-agent-delegation.md), the four verb rituals (`/wiki-ingest`, `/wiki-lint`, `/wiki-query` — all orchestration skills — and `/new-llm-wiki` — the scaffold prompt) plus 8 atomic wiki-* skills live at user level and work from any workspace; vault-level agents (`@wiki-reader`, `@wiki-maintainer`, `@wiki-auditor`) are optional per-domain (opt-in for `business` and `personal` domains, opt-out via `--minimal` or opt-in via `--with-agents` for others) and delegate to the orchestration skills.

For the design rationale and the deterministic/LLM boundary, see [ARCHITECTURE.md](ARCHITECTURE.md); individual design decisions are recorded as ADRs under [docs/decisions/](docs/decisions/).

## Install

### macOS / Linux

```bash
git clone https://github.com/<owner>/llm-wiki-scaffolder ~/llm-wiki-scaffolder
cd ~/llm-wiki-scaffolder
./bin/install.sh
```

Prerequisites: Python 3.8+, `rsync`, `git`, VS Code with GitHub Copilot Chat.

### Windows

```powershell
git clone https://github.com/<owner>/llm-wiki-scaffolder $env:USERPROFILE\llm-wiki-scaffolder
cd $env:USERPROFILE\llm-wiki-scaffolder
.\bin\install.ps1
```

Prerequisites: Python 3.8+, `git`, VS Code with GitHub Copilot Chat.

---

Then reload the VS Code window (`Cmd/Ctrl+Shift+P → Developer: Reload Window`). The commands `/new-llm-wiki`, `/wiki-ingest`, `/wiki-lint`, `/wiki-query` are now available in Copilot Chat from **any** workspace.

> **Agent Mode required.** `/wiki-ingest` and `/wiki-lint` need write access + terminal execution to run the skill Python scripts. Set the Copilot chat mode to **Agent** (not Ask). See the [ADR-0009 erratum](docs/decisions/0009-evaluate-user-level-vault-operational-customizations.md#erratum-2026-07-post-pilot-correction) for details on the tool-restriction model.

### VS Code Insiders

**macOS / Linux:**
```bash
./bin/install.sh --insiders
```

**Windows:**
```powershell
.\bin\install.ps1 -Insiders
```

## Usage

In Copilot Chat, from any workspace:

```
/new-llm-wiki                                 # full wizard
/new-llm-wiki --help                          # print script usage and stop
/new-llm-wiki ~/Vaults/my-vault               # path + wizard for the rest
/new-llm-wiki ~/Vaults/lotr --type reading --fiction \
    --name "LOTR" --desc "Reading Tolkien" --lang english
```

The prompt orchestrates a deterministic Python script for filesystem work and only itself writes 4–5 project-specific seed questions into `wiki/overview.md`.

### Direct CLI use (without VS Code)

The scaffolder also runs standalone:

**macOS / Linux:**
```bash
~/.config/llm-wiki/bin/scaffold.py --help
~/.config/llm-wiki/bin/scaffold.py \
    --path ~/vaults/proj --name "MyProj" --type development \
    --desc "SaaS auth service" --lang english
```

**Windows:** (use `py` if the Python launcher is installed, otherwise `python`)
```powershell
py $env:APPDATA\llm-wiki\bin\scaffold.py --help
py $env:APPDATA\llm-wiki\bin\scaffold.py `
    --path C:\Vaults\proj --name "MyProj" --type development `
    --desc "SaaS auth service" --lang english
```

Useful for scripting, CI, or when Copilot is not available.

## Update

**macOS / Linux:**
```bash
cd ~/llm-wiki-scaffolder
git pull
./bin/install.sh
```

**Windows:**
```powershell
cd $env:USERPROFILE\llm-wiki-scaffolder
git pull
.\bin\install.ps1
```

Idempotent: templates are synced (`rsync --delete` on Unix, `Copy-Item` on Windows), the script and prompt are re-installed. No user state in the install directory is preserved between runs — edit the repo, not the runtime copy.

## Uninstall

**macOS / Linux:**
```bash
./bin/install.sh --uninstall
```

**Windows:**
```powershell
.\bin\install.ps1 -Uninstall
```

Removes installed files and the VS Code user prompt. Vaults created with the scaffolder are untouched.

## What gets created in a vault

```
<vault>/
    raw/                     # user-owned, immutable
        assets/
        <domain subfolders>/
    wiki/                    # LLM-owned
        entities/            # empty at scaffold; populated on /wiki-ingest
        concepts/            # empty at scaffold
        sources/             # empty at scaffold
        analysis/            # empty at scaffold
        <extra subfolders>/  # empty at scaffold
        index.md             # content-oriented catalog
        log.md               # chronological, append-only
        overview.md          # domain-adapted, with "Suggested first questions"
    .github/
        copilot-instructions.md         # minimal signpost (Model D)
        karpathy_llm_wiki_pattern.md    # pinned copy of the pattern doc
        instructions/wiki-conventions.instructions.md
        agents/wiki-{reader,maintainer,auditor}.agent.md   # OPTIONAL per domain
    AGENTS.md                # multi-assistant bridge (Codex, OpenCode, Aider, Cursor)
    .gitignore
```

**Vault-level prompts are NOT scaffolded under Model D** — the `/wiki-ingest`, `/wiki-lint`, `/wiki-query` slash-commands are installed at user level and work from any workspace containing an LLM Wiki vault. The vault path is read from the auto-loaded `.github/copilot-instructions.md` (`## Vault / **Path:**` field), which the scaffolder writes at vault creation time — see [ADR-0010](docs/decisions/0010-eliminate-wiki-detect-vault.md).

**Agents are optional per domain**: `business` and `personal` include them by default (stricter roles for sensitive data), `research`/`development`/`reading`/`learning`/`hobby` do not. Override with `--with-agents` or `--minimal` at scaffold time.

Content folders (`wiki/entities/`, `wiki/concepts/`, `wiki/sources/`, `wiki/analysis/`, extra folders) stay empty on scaffold. They are populated by the maintainer role on the first `/wiki-ingest`. This preserves the Karpathy invariant that the wiki is *compounded* from sources, not pre-filled.

## Domain types

| Type | Extra wiki/ | Extra page types |
|---|---|---|
| `research` | `findings/`, `open_questions/` | `finding`, `hypothesis` |
| `development` | `decisions/`, `requirements/` | `decision`, `requirement` |
| `reading --fiction` | `characters/`, `themes/` | `character`, `theme` |
| `reading --nonfiction` | `authors/`, `arguments/` | `author`, `argument` |
| `personal` | `goals/`, `patterns/`, `reflections/` | `goal`, `pattern`, `reflection` |
| `business` | `processes/`, `people/`, `initiatives/` | `process`, `initiative` |
| `learning` | `topics/`, `flashcards/` | `topic`, `exercise` |
| `hobby` | — | — (define your own) |

Override defaults with `--raw-folders "a,b,c"` and `--extra-wiki-folders "a,b,c"`.

## Modes

- **fresh**: target path is absent or empty. Full scaffold.
- **`--force`**: overwrite an existing wiki. Destructive.
- **`--upgrade`**: fill only missing files in `.github/`. Never touches `wiki/`, `raw/`, `AGENTS.md`, `.gitignore`. Use this when the template evolves and you want to bring an existing vault up-to-date without disturbing its content. Refuses to run if the vault's original `--type` differs from the one you pass (guard added post-pilot); use `--force-retype` to intentionally re-type a vault.
- **`--with-agents`**: include vault-level `@wiki-{reader,maintainer,auditor}` agents even when the domain default omits them.
- **`--minimal`**: exclude vault-level agents even when the domain default includes them.
- **`--force-retype`**: bypass the `--upgrade` type-mismatch guard (destructive: adds different `raw/`+`wiki/` subfolders).

## Working with the vault

Once scaffolded, a vault exposes 4 user-level slash-commands and (optionally) 3 vault-level role agents. Full rationale in [ADR-0005](docs/decisions/0005-prompt-vs-agent-invocation.md), [ADR-0009](docs/decisions/0009-evaluate-user-level-vault-operational-customizations.md), and [ADR-0012](docs/decisions/0012-orchestration-skills-and-agent-delegation.md); quick reference:

| Situation | Tool | Level | Kind |
|---|---|---|---|
| Add *this* source to the wiki | `/wiki-ingest <path>` | user (works from any workspace) | orchestration skill |
| Run periodic health check | `/wiki-lint` | user | orchestration skill |
| Ask a one-shot question against the wiki | `/wiki-query "<question>"` | user | orchestration skill |
| Scaffold a new vault | `/new-llm-wiki` | user | prompt (pre-vault, no vault context to inherit) |
| Discuss before writing; multi-turn maintenance | `@wiki-maintainer` | vault (if agents included) | delegates to `wiki-ingest` |
| Audit only *these* pages / *this* aspect | `@wiki-auditor` | vault (if agents included) | delegates to `wiki-lint` |
| Multi-turn Q&A with role personality | `@wiki-reader` | vault (if agents included) | delegates to `wiki-query` |

**Three-layer architecture** (per ADR-0012):
- **Atomic skills** (hidden from `/` picker via `user-invocable: false`): 8 composable primitives — `wiki-search`, `wiki-read-page`, `wiki-summarize-source`, `wiki-write-source-page`, `wiki-write-analysis`, `wiki-update-index`, `wiki-append-log`, `wiki-lint-check`.
- **Orchestration skills** (visible in `/` picker): `wiki-ingest`, `wiki-lint`, `wiki-query` — each composes the atomic skills into the canonical INGEST / LINT / QUERY workflow.
- **Agents** (optional, vault-level): 3 role-scoped agents that delegate to the orchestration skills and add domain personality (spoiler-safe reading, PII redaction, ADR format, etc.).

**Prompt = verb, agent = subject.** Slash-commands are one-shot rituals with `argument-hint` and log entries (`## [date] ingest \| ...` / `## [date] lint \| ...` / `## [date] query \| ...`). Mentions are role-based conversations for multi-turn or negotiated work — they add vault-specific domain personality on top of the same underlying skills.

## Future ideas

Open directions considered and deferred. Not roadmap commitments — just parking notes so we don't rediscover the same trade-offs later.

### Skill token optimization

Under Model D each `/wiki-*` workflow loads multiple `SKILL.md` bodies into context (~4000 tokens per `/wiki-query`). Optimizations (`LLM_WIKI_ACTIVE_VAULT` env var, `disable-model-invocation: true` on `wiki-detect-vault`, progressive-disclosure `references/` split) are analyzed and ranked in [ADR-0011](docs/decisions/0011-skill-token-optimization-strategies.md), deferred until pilot data justifies action.

### Sidecar `references/` modularity (in the current prompt)

Even without switching to skill format, we can steal the skill pattern of moving long-form content into on-demand files that the LLM reads when needed. Candidates in the current prompts:

- Detailed per-domain conventions → `~/.config/llm-wiki/references/domain_conventions.md`
- Any future per-domain checklist or long-form guidance

Trigger: do this when a prompt exceeds ~300 lines or when adding a new domain makes the tables unwieldy.

### One-liner install (`curl | bash`)

Currently install is `git clone + ./bin/install.sh`. A `install-remote.sh` published at a stable URL would let users skip the clone:

```
curl -fsSL https://<host>/install-remote.sh | bash
```

Trade-off: `curl | bash` is a common security anti-pattern from the user's perspective (running remote code sight-unseen). If we add it, we document the clone-first alternative in the same README for users who want to review the code first.

### Distribution alternatives

- **PyPI package** (`uv tool install llm-wiki-scaffolder`) — clean, but freezes templates into the package (breaks the "edit template, re-install, iterate" fast loop) and doesn't handle the Copilot prompt file. Deferred until user base grows enough to justify PyPI account + versioning.
- **Homebrew tap** — over-engineered for a personal-scale tool. Not planned.
- **VS Code Extension** — huge development cost, unnecessary since prompts and skills already do the job. Not planned.

Related: [ADR-0001](docs/decisions/0001-python-stdlib-only.md) explains why the current stdlib-only design blocks the PyPI path in particular.


## License

MIT — see [LICENSE](LICENSE).
