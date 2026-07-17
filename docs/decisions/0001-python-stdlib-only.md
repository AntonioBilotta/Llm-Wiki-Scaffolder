# ADR-0001: Python stdlib only for `scaffold.py`

## Status
Accepted (2026-07)

## Context

The scaffolder must run on any machine with Python 3.8+ available, without a package manager step, virtualenv setup, or additional runtime configuration. It is invoked both:
- as a subprocess from the VS Code Copilot prompt (`/new_llm_wiki_vault`)
- directly from the CLI (`~/.config/llm-wiki/bin/scaffold.py`)

The install path (`./bin/install.sh`) needs to work as a single Bash + rsync flow with no post-install `pip` steps.

## Decision

`scaffold.py` uses only the Python **standard library** (Python 3.8+). No third-party dependencies. No `pyproject.toml`, no `requirements.txt`, no virtualenv activation.

## Consequences

**Positive**
- Zero-dependency install: `./bin/install.sh` finishes in one shot.
- Predictable runtime across macOS and Linux — Python 3.8 is the baseline on all supported distros.
- The script can be run standalone (e.g. from CI, from a shell script, or from another agent host) with no environment prep.
- Editing templates and re-installing is a single-command loop; no dependency resolution ever runs.
- Trivial audit surface: reviewing `scaffold.py` requires no external context.

**Negative**
- No YAML library — the (small amount of) YAML frontmatter is emitted via string templates, not serialized programmatically. Acceptable given the fixed shape of the frontmatter.
- No `rich`/`click` for CLI ergonomics; we hand-roll `argparse` and print plain text. Acceptable given the CLI has ~10 flags.
- Filesystem operations use `shutil` + `pathlib` — slightly more verbose than higher-level abstractions.

**Neutral**
- Feature growth is constrained by "does it need a dependency?" — a natural signal that the script is getting too ambitious and the work should move to templates or to the LLM layer.

## Alternatives considered

- **PyPI package (`uv tool install llm-wiki-scaffolder`)** — clean but freezes templates into the package, breaking the "edit template, re-install, iterate" loop that is core to the development experience. Also does not handle the VS Code prompt file. Deferred until a user base justifies the packaging overhead. Noted in [README.md](../../README.md) "Distribution alternatives".
- **`pyyaml` for frontmatter** — rejected; the emitted frontmatter is trivial and adding one dependency to serialize ~5 fixed fields is not worth breaking the stdlib-only invariant.
- **Node.js implementation** — rejected; Python is more universally pre-installed on developer machines than Node on macOS/Linux, and the target user is developer-adjacent (VS Code + Copilot).
- **Bash-only scaffold** — rejected; state detection, JSON output, and cross-platform path handling become brittle in Bash at this scale.
