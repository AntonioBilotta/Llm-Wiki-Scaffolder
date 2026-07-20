# ADR-0008: Windows support

## Status
Accepted (2026-01)

## Context

The original scaffolder targeted macOS and Linux only:
- `install.sh` relies on `rsync` (rarely available on Windows by default)
- `scaffold.py` hardcoded `~/.config/llm-wiki/` as the templates directory
- VS Code prompts path assumed Unix-style `~/.vscode/` locations

Windows developers with VS Code + Copilot Chat were unable to use the scaffolder without WSL or manual adaptation.

## Decision

Add native Windows support alongside the existing Unix installer:

1. **New PowerShell installer** (`bin/install.ps1`):
   - Uses `Copy-Item -Recurse` instead of `rsync`
   - Targets `%APPDATA%\llm-wiki\` for templates and script
   - Detects VS Code (stable or Insiders) prompts folder at `%APPDATA%\Code\User\prompts\`
   - Supports `-Uninstall` and `-Insiders` flags for parity with Bash installer

2. **Cross-platform path detection in `scaffold.py`**:
   - On `sys.platform == "win32"`: use `%APPDATA%\llm-wiki\templates`
   - Otherwise: use `~/.config/llm-wiki/templates`
   - Falls back gracefully if `APPDATA` is unset

3. **Line-ending management** (`.gitattributes`):
   - `*.sh` → LF (required by Bash)
   - `*.ps1` → CRLF (Windows convention)
   - `*.py` → LF (cross-platform)

4. **Documentation** (`README.md`):
   - Platform-specific install / update / uninstall commands
   - Separate prerequisites (no `rsync` on Windows)

## Consequences

**Positive**
- Windows developers can scaffold LLM Wiki vaults natively without WSL
- No new dependencies on Unix (Bash + rsync remain the install path)
- `scaffold.py` remains stdlib-only — the change is `os.environ` + `sys.platform` checks, already in stdlib
- Clear separation: `install.sh` for Unix, `install.ps1` for Windows

**Negative**
- Two installers to maintain (but they share no code, so divergence is low-risk)
- `.gitattributes` adds minor repo complexity

**Neutral**
- Users on Windows with rsync installed (Git Bash, Cygwin) could in theory run `install.sh` via Bash, but the recommended path is now `install.ps1`

## Alternatives considered

- **WSL-only support** — rejected; many Windows users prefer native tools, and requiring WSL adds friction
- **Single Python installer** — rejected; the Bash/rsync flow is elegant and standard on Unix; rewriting it in Python would add complexity for no Unix benefit
- **PowerShell Core on Unix** — not required; the Bash installer is simpler and more idiomatic on macOS/Linux
