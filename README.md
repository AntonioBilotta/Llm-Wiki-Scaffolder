# llm-wiki-scaffolder

Deterministic scaffolder for **LLM Wiki** vaults following the [Karpathy pattern](templates/karpathy_llm_wiki_pattern.md). Installs a user-level slash-command (`/new-llm-wiki`) for GitHub Copilot Chat in VS Code, backed by a stdlib-only Python script.

An LLM Wiki is a persistent, LLM-maintained knowledge base: `raw/` holds immutable sources, `wiki/` holds LLM-owned markdown (entities, concepts, sources, analysis, plus domain-specific folders), and the LLM keeps the wiki up-to-date as new sources are added. Three commands drive it: `/wiki-ingest`, `/wiki-lint`, `@wiki-reader`.

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

Then reload the VS Code window (`Cmd/Ctrl+Shift+P → Developer: Reload Window`). The command `/new-llm-wiki` is now available in Copilot Chat from **any** workspace.

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
        copilot-instructions.md         # minimal signpost
        karpathy_llm_wiki_pattern.md    # pinned copy of the pattern doc
        instructions/wiki-conventions.instructions.md
        agents/wiki-{reader,maintainer,auditor}.agent.md
        prompts/wiki-{ingest,lint}.prompt.md
    AGENTS.md                # multi-assistant bridge (Codex, OpenCode, Aider, Cursor)
    .gitignore
```

Content folders (`wiki/entities/`, `wiki/concepts/`, `wiki/sources/`, `wiki/analysis/`, extra folders) stay empty on scaffold. They are populated by `@wiki-maintainer` on the first `/wiki-ingest`. This preserves the Karpathy invariant that the wiki is *compounded* from sources, not pre-filled.

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
- **`--upgrade`**: fill only missing files in `.github/`. Never touches `wiki/`, `raw/`, `AGENTS.md`, `.gitignore`. Use this when the template evolves and you want to bring an existing vault up-to-date without disturbing its content.

## Working with the vault

Once scaffolded, a vault exposes two slash-commands and three role agents. Full rationale in [ADR-0005](docs/decisions/0005-prompt-vs-agent-invocation.md); quick reference:

| Situation | Tool |
|---|---|
| Add *this* source to the wiki | `/wiki-ingest <path>` |
| Run periodic health check | `/wiki-lint` |
| Discuss before writing; non-ingest maintenance op | `@wiki-maintainer` |
| Audit only *these* pages / *this* aspect | `@wiki-auditor` |
| Ask a question against the wiki | `@wiki-reader` |

**Prompt = verb, agent = subject.** Slash-commands are canonical, one-shot rituals with `argument-hint` and log entries (`## [date] ingest \| ...` / `## [date] lint \| ...`). Mentions are role-based conversations, used off the canonical path.

## Future ideas

Open directions considered and deferred. Not roadmap commitments — just parking notes so we don't rediscover the same trade-offs later.

### Skill wrapper (Copilot workspace-level, and/or Claude Code user-level)

Both VS Code Copilot and Claude Code support the `SKILL.md` format with bundled `references/` assets and autonomous invocation (LLM decides to invoke based on the skill's `description`, no explicit slash command needed).

- **Copilot skills** live at `.github/skills/<name>/` or `.claude/skills/<name>/` and are **workspace-scoped only** — no user-level equivalent. Adopting for Copilot would trade the current "install once, use everywhere" flow for per-workspace copies. Not worth it unless we also automate per-workspace sync.
- **Claude Code skills** live at `~/.claude/skills/<name>/` and **are user-level**. Adding a Claude skill alongside the Copilot prompt would give autonomous invocation on that host with a ~150-line wrapper that delegates to the same `scaffold.py`. Only useful if we start using Claude Code as an alternative surface.

For now the Copilot prompt covers the primary use case. Revisit if the prompt grows past ~400 lines or if we adopt Claude Code routinely.

See [ADR-0002](docs/decisions/0002-user-level-prompt-not-skill.md) for the scaffold command choice and [ADR-0007](docs/decisions/0007-ingest-lint-remain-prompts.md) for why `/wiki-ingest` and `/wiki-lint` stay prompts too.

### Sidecar `references/` modularity (in the current prompt)

Even without switching to skill format, we can steal the skill pattern of moving long-form content into on-demand files that the LLM reads when needed. Candidates in the current prompt:

- The "Domain notes" table (Section 5b) → `~/.config/llm-wiki/references/domain_notes.md`
- Detailed per-domain conventions → `~/.config/llm-wiki/references/domain_conventions.md`
- Any future per-domain checklist or long-form guidance

Trigger: do this when the prompt exceeds ~300 lines or when adding a new domain makes the tables unwieldy. Cross-referenced from [ADR-0007](docs/decisions/0007-ingest-lint-remain-prompts.md).

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
