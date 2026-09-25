---
name: wiki-init
description: Create (scaffold) a new LLM Wiki vault, Karpathy pattern, in a folder the user names - or upgrade an existing one with missing files. Runs the bundled deterministic scaffold.py, then writes project-specific seed questions. Use only when the user explicitly asks to create, initialize, scaffold or upgrade an LLM Wiki; never as a side effect of another task. Trigger keywords - 'create a new llm wiki', 'new wiki vault', 'scaffold a wiki', 'initialize a wiki in', 'upgrade my wiki vault', '/wiki-init'.
argument-hint: "[<path>] [--type <research|development|reading|personal|business|learning|hobby>] [--fiction|--nonfiction] [--name \"<n>\"] [--desc \"<d>\"] [--lang <italian|english>] [--force|--upgrade] [--seed <path>]"
disable-model-invocation: true
---

# wiki-init

Scaffold a new LLM Wiki vault. The deterministic work (directories, template copy, placeholder substitution, state detection) is done by `scaffold.py`; your job is limited to parsing intent, collecting missing parameters, running the script, and writing the little natural-language content the script cannot produce (seed questions; optional domain notes on agents). Same contract as the VS Code `/new-llm-wiki` prompt ([ADR-0002](https://github.com/AntonioBilotta/Llm-Wiki-Scaffolder/blob/main/docs/decisions/0002-user-level-prompt-not-skill.md), [ADR-0003](https://github.com/AntonioBilotta/Llm-Wiki-Scaffolder/blob/main/docs/decisions/0003-deterministic-scaffold-llm-fill.md)), runtime-neutral.

Follow the sections in order. Do not skip.

## 1 — Invocation grammar

```
wiki-init [<path>] [options]

  --type <t>                research | development | reading | personal | business | learning | hobby
  --fiction | --nonfiction  (required when --type reading)
  --name "<n>"              Project name
  --desc "<d>"              One-line description
  --lang <italian|english>  Wiki content language
  --raw-folders "a,b"       Override raw/ subfolders
  --extra-wiki-folders "a,b"  Override extra wiki/ subfolders
  --with-agents | --minimal Include / omit .github/agents/ (default depends on type)
  --force                   Overwrite an existing vault (destructive)
  --upgrade                 Only add missing files; never overwrite
  --seed <path>             Copy one starter source into raw/<domain-default>/
  --help                    Print scaffold.py usage and stop
```

Values not given inline are collected in section 3.

## 2 — Locate the scaffolder

Use the first that exists (`<skill-dir>` is the directory containing this SKILL.md; Claude Code shows it as the skill's base directory):

1. **Bundled** — `<skill-dir>/scripts/scaffold.py` with `<skill-dir>/templates/`. The installers and `bin/package_skills.py` copy both into the skill. Always pass `--templates "<skill-dir>/templates"` with this one.
2. **Installed** — `%APPDATA%\llm-wiki\bin\scaffold.py` on Windows, `~/.config/llm-wiki/bin/scaffold.py` elsewhere. It finds its templates on its own.
3. Neither → tell the user to run `bin/install.sh` (or `bin\install.ps1` on Windows) from a clone of llm-wiki-scaffolder, and stop.

Run it with `python3` (on Windows `python` or `py -3` if `python3` is not on PATH). Below, `SCAFFOLD` means the full command: interpreter + script path + `--templates` when bundled.

**Where the vault is created.** Run the script on the machine where the vault must live, so the paths it records are real. If your shell cannot reach the target folder (for example a cloud session linked to the user's computer, where the target is a connected folder), run the script in your own environment into a temporary folder, copy the whole tree into the target folder, then replace the `**Path:**` value in `AGENTS.md` and `.github/copilot-instructions.md` with the target folder's real path. Never create a vault outside a folder the user named.

**Help**: if the request contains `--help` or `-h`, run `SCAFFOLD --help`, print the output verbatim, and stop.

## 3 — Parameters (ask only for what is missing)

1. **Parse inline args**: `path`, `type` (+ `fiction`/`nonfiction` for `reading`), `name`, `desc`, `lang`, `force`, `upgrade`, `seed`, `raw-folders`, `extra-wiki-folders`, `with-agents`/`minimal`.
2. **Detect vault state** if a path is known: `SCAFFOLD --detect-only --path "<path>"`. Read the JSON: `state` (`absent` | `existing_llm_wiki` | `existing_non_wiki`) and `domain_type_hint` (a base type or `null`).
3. **Existing wiki** (`state == existing_llm_wiki`, no `--force`/`--upgrade`): ask whether to **Upgrade** (add missing files only — recommended), **Force** (overwrite everything — destructive) or **Cancel**.
4. **Ask for the missing values in one round**, with your runtime's question tool (`AskUserQuestion` in Claude, `vscode_askQuestions` in VS Code Copilot; otherwise one plain-text message listing the questions):
   - **Vault path** — free text; suggest `<a folder the user works in>/<slug of name>`.
   - **Project name** — free text.
   - **Domain type** — `research`, `development`, `reading`, `personal`, `business`, `learning`, `hobby`; mark `domain_type_hint` as recommended when set.
   - **Reading subvariant** (only for `reading`) — `fiction` | `nonfiction`.
   - **Domain description** — one sentence.
   - **Wiki content language** — `italian` | `english`.
   Phrase the questions in the language the user is writing in.
5. **Validate**: every required value must be present. If the user cancelled, stop.

## 4 — Run the scaffold (deterministic)

```
SCAFFOLD --path "<vault_path>" --name "<project_name>" --type <type> [--fiction|--nonfiction] \
         --desc "<domain_description>" --lang <language> \
         [--with-agents|--minimal] [--force|--upgrade] [--seed "<seed_path>"] --json-out
```

- **Upgrade safety**: in `--upgrade` mode, run the same command with `--dry-run` first, show the files that would be created (`files_created`), and get confirmation — unless the user already confirmed in section 3.
- **Force safety**: `--force` overwrites. Only use it after an explicit confirmation in this conversation.
- Parse stdout as JSON. On a non-zero exit code or `status != "ok"`, show the error and stop. Do not attempt recovery.

## 5 — LLM-only fills (after the scaffold)

Do only these; nothing else.

### 5a — Suggested first questions (always, except `--upgrade` on a vault whose overview already has them)

Replace the italic placeholder line under `## Suggested first questions` in `<vault_path>/wiki/overview.md` with 4–5 bullet questions:
- specific to `project_name` and `domain_description`, not generic domain templates;
- answerable from the wiki after ingesting 1–2 sources, without web search;
- written in the wiki content language.

### 5b — Domain notes on agents (only these cases, only if the agent files exist)

Append a `## Domain notes` section (under 6 lines) to the listed file. Do not modify workflow steps, hard rules or frontmatter.

| internal type | File | Note |
|---|---|---|
| `reading_fiction` | `.github/agents/wiki-reader.agent.md` | Answer spoiler-safe: never volunteer information from chapters newer than those ingested; if the answer needs a later chapter, say so. |
| `reading_fiction` | `.github/agents/wiki-maintainer.agent.md` | Keep character/theme pages restricted to what is knowable at that chapter; use `> [!warning] Retcon:` when a later chapter overturns an earlier fact. |
| `development` | `.github/agents/wiki-maintainer.agent.md` | When a source proposes or resolves an architectural decision, create/update a page under `wiki/decisions/` in ADR format (Context, Decision, Consequences). Requirements get stable IDs (`REQ-###`) in file name and frontmatter. |
| `personal` | `.github/agents/wiki-maintainer.agent.md` | Prefer descriptive language over diagnostic labels; do not extrapolate diagnoses; redact third-party names without consent. |
| `business` | `.github/agents/wiki-maintainer.agent.md` | Redact sensitive customer identifiers; reference attendees as `[[people/<name>]]`; keep employees' personal details out of the wiki. |

## 6 — Final output

A compact block; do not narrate the steps.

```
Created LLM wiki at <vault_path> (mode: <mode>).

  raw/     <raw folders> + assets/
  wiki/    entities/ concepts/ <extra folders> sources/ analysis/ + index.md log.md overview.md
  .github/ copilot-instructions.md, conventions, pattern doc[, agents/]
  AGENTS.md, CLAUDE.md, .gitignore
  Files created: N · overwritten: M · skipped: K

Next steps:
  1. Put a first source under raw/<default>/ and run  /wiki-ingest raw/<default>/<file>
     (if --seed was used: /wiki-ingest <seed_path_final>)
  2. Ask questions:  /wiki-query "<question>"
  3. Health-check periodically:  /wiki-lint
  Claude Code: open a session in <vault_path> (CLAUDE.md loads the vault path).
  Obsidian: open <vault_path> as a vault.

Suggested first questions (in wiki/overview.md):
  - ...
```

Do not start an ingest yourself, even when `--seed` was passed.

## Hard rules (Karpathy pattern)

- **Never write into `raw/`** other than the optional `--seed` copy made by the script.
- **Never write into `wiki/` content folders** (`entities/`, `concepts/`, `sources/`, `analysis/`, extra folders) at scaffold time. They stay empty until the first `wiki-ingest`.
- **Signposts stay minimal.** Do not add content to `.github/copilot-instructions.md`, `AGENTS.md` or `CLAUDE.md`, except fixing the `**Path:**` value as described in section 2. New conventions go in `.github/instructions/wiki-conventions.instructions.md`.
- **The three roles are fixed.** Do not create new agents or change their workflows.
