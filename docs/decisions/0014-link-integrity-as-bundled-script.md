# ADR-0014: Link integrity as a second bundled script in wiki-lint-check

## Status
Accepted (2026-11)

## Context

Obsidian, and every wiki-* skill, resolves a bare `[[name]]` by file name, case-insensitively, across the whole vault. When two pages share a name in different folders (for example `wiki/hats/red_hat.md` and `wiki/agents/red_hat.md`), every bare link to that name is ambiguous: Obsidian silently picks one file, and `check_evidence.py` checks only the first one it finds. `check_evidence.py` already noticed the duplicate (`ambiguous_page_name`), but only as an evidence error, without the files involved or the links affected. No check looked for broken wikilinks: check 7 validates `related_sources`, not links in page bodies.

A real vault (`6-hats-agents/llm-wiki`) had six names duplicated between `hats/` and `agents/`, making 104 links ambiguous, and nothing in the lint report pointed at them.

The new check is mechanical, so it belongs in a script. The question was where the script lives.

## Decision

Add check 9, **link integrity**, to `wiki-lint-check`, implemented as a second read-only, stdlib-only script, `skills/wiki-lint-check/scripts/check_links.py`, next to `check_evidence.py` and with the same interface (`--vault-path`, optional `--pages`, JSON on stdout, always exit 0). It reports `duplicate_basenames` (with the files and the pages linking with a bare name) and `broken_links`. Findings are never auto-repairable: renaming pages or qualifying links with their folder is the maintainer's choice.

## Consequences

- Same invocation on every runtime (VS Code Copilot, Claude Code, claude.ai, Windows): one command line, no shell-specific syntax.
- Unit-tested like `check_evidence.py` (`tests/test_check_links.py`); the repo stays the single source of truth, and `install.sh` / `install.ps1` / `package_skills.py` ship the script without changes, since they copy the whole skill folder.
- `SKILL.md` grows by one short step instead of a full script listing, so the skill costs fewer tokens each time it loads.
- `wiki-lint` needs no change: it consumes the JSON and auto-repairs only frontmatter; the two new keys fall under "needs user approval".
- One more file to keep in sync on claude.ai: the skill must be re-uploaded as an archive, because editing only `SKILL.md` there does not add files.

## Alternatives considered

- **Script embedded in `SKILL.md`** (an appendix run through a bash heredoc). Tried first: it works, but heredocs do not exist in PowerShell, the agent has to copy code exactly, a script containing ``` breaks the Markdown fence around it, and the code cannot be unit-tested. Rejected.
- **Extend `check_evidence.py`.** It already knows about duplicates, but its job is source fidelity; mixing link checks into it would blur its single responsibility and its report shape. Rejected.
- **Check by reasoning only**, as checks 1–7. Duplicate names and broken links are exact set operations over file names; an LLM pass is slower and can miss links on large vaults. Rejected.
