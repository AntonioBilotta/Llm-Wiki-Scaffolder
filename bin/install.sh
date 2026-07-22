#!/usr/bin/env bash
# install.sh — install llm-wiki-scaffolder into user-level locations.
#
#   - Templates and script → ~/.config/llm-wiki/
#   - VS Code slash command prompt → VS Code user prompts folder
#     (macOS: ~/Library/Application Support/Code/User/prompts)
#     (Linux: ~/.config/Code/User/prompts)
#
# Idempotent. Safe to re-run for updates.

set -euo pipefail

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

ACTION="install"
INSIDERS=false
SKIP_PROMPT=false

show_help() {
    cat <<'EOF'
Usage: ./bin/install.sh [options]

Options:
  --uninstall       Remove installed files (does not touch this repo)
  --insiders        Target VS Code Insiders instead of stable
  --no-prompt       Skip copying the VS Code user prompt
  --help, -h        Show this help

Installed paths (default):
  ~/.config/llm-wiki/bin/scaffold.py
  ~/.config/llm-wiki/templates/
  <VS Code user prompts folder>/new-llm-wiki.prompt.md

Re-run to update. Templates are synced with rsync --delete, so the runtime
copy always matches the repo. Local edits to the runtime templates will
be lost — edit the repo copy and re-run.
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        --uninstall) ACTION="uninstall" ;;
        --insiders) INSIDERS=true ;;
        --no-prompt) SKIP_PROMPT=true ;;
        --help|-h) show_help; exit 0 ;;
        *) echo "error: unknown option: $1" >&2; show_help >&2; exit 1 ;;
    esac
    shift
done

# ---------------------------------------------------------------------------
# Locate repo and prerequisites
# ---------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ ! -f "$REPO_ROOT/bin/scaffold.py" ]; then
    echo "error: cannot locate scaffold.py at $REPO_ROOT/bin/scaffold.py" >&2
    echo "hint:  run this script from inside a clone of the llm-wiki-scaffolder repo." >&2
    exit 1
fi

for cmd in python3 rsync; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "error: required command not found: $cmd" >&2
        exit 1
    fi
done

# ---------------------------------------------------------------------------
# Resolve VS Code user prompts folder
# ---------------------------------------------------------------------------

detect_vscode_prompts_dir() {
    local os_name
    os_name="$(uname -s)"
    local base flavor
    if [ "$INSIDERS" = "true" ]; then
        flavor="Code - Insiders"
    else
        flavor="Code"
    fi
    case "$os_name" in
        Darwin)
            base="$HOME/Library/Application Support/$flavor/User/prompts"
            ;;
        Linux)
            base="$HOME/.config/$flavor/User/prompts"
            ;;
        *)
            echo "error: unsupported OS: $os_name (macOS and Linux only)" >&2
            exit 1
            ;;
    esac
    printf '%s' "$base"
}

VSCODE_PROMPTS_DIR="$(detect_vscode_prompts_dir)"

# ---------------------------------------------------------------------------
# Target paths
# ---------------------------------------------------------------------------

INSTALL_ROOT="$HOME/.config/llm-wiki"
INSTALL_BIN="$INSTALL_ROOT/bin"
INSTALL_TEMPLATES="$INSTALL_ROOT/templates"
INSTALL_SCAFFOLD="$INSTALL_BIN/scaffold.py"
INSTALL_PROMPT="$VSCODE_PROMPTS_DIR/new-llm-wiki.prompt.md"
# Legacy: prior versions installed the scaffold prompt as new_llm_wiki_vault.prompt.md.
# Kept here so install and uninstall clean up the old filename on machines that had
# a previous install (per ADR-0002 Erratum: naming update).
LEGACY_INSTALL_PROMPT="$VSCODE_PROMPTS_DIR/new_llm_wiki_vault.prompt.md"

# ---------------------------------------------------------------------------
# Uninstall
# ---------------------------------------------------------------------------

if [ "$ACTION" = "uninstall" ]; then
    echo "Uninstalling llm-wiki-scaffolder..."
    removed=0
    for target in "$INSTALL_SCAFFOLD" "$INSTALL_PROMPT" "$LEGACY_INSTALL_PROMPT"; do
        if [ -f "$target" ]; then
            rm -f -- "$target"
            echo "  removed: $target"
            removed=$((removed + 1))
        fi
    done
    if [ -d "$INSTALL_TEMPLATES" ]; then
        rm -rf -- "$INSTALL_TEMPLATES"
        echo "  removed: $INSTALL_TEMPLATES/"
        removed=$((removed + 1))
    fi
    # Prune ~/.config/llm-wiki/ and ~/.config/llm-wiki/bin/ if empty.
    rmdir "$INSTALL_BIN" 2>/dev/null || true
    rmdir "$INSTALL_ROOT" 2>/dev/null || true
    if [ "$removed" -eq 0 ]; then
        echo "  nothing to remove."
    fi
    echo "Uninstall complete."
    exit 0
fi

# ---------------------------------------------------------------------------
# Install
# ---------------------------------------------------------------------------

echo "Installing llm-wiki-scaffolder from $REPO_ROOT"
echo "  scaffold:  $INSTALL_SCAFFOLD"
echo "  templates: $INSTALL_TEMPLATES/"
if [ "$SKIP_PROMPT" = "false" ]; then
    echo "  prompt:    $INSTALL_PROMPT"
fi
echo ""

mkdir -p -- "$INSTALL_BIN" "$INSTALL_TEMPLATES"

# Templates: rsync so removed template files also disappear from install.
# Exclude OS junk and any hidden dotfiles that shouldn't reach a scaffolded vault.
rsync -a --delete \
    --exclude='.DS_Store' --exclude='Thumbs.db' --exclude='.git*' \
    "$REPO_ROOT/templates/" "$INSTALL_TEMPLATES/"

# Script: install with executable bit.
install -m 0755 "$REPO_ROOT/bin/scaffold.py" "$INSTALL_SCAFFOLD"

# Prompt: copy to VS Code user prompts folder.
if [ "$SKIP_PROMPT" = "false" ]; then
    if [ ! -f "$REPO_ROOT/prompts/new-llm-wiki.prompt.md" ]; then
        echo "error: missing prompt file at $REPO_ROOT/prompts/new-llm-wiki.prompt.md" >&2
        exit 1
    fi
    mkdir -p -- "$VSCODE_PROMPTS_DIR"
    # Remove legacy prompt file if present (renamed 2026-07 per ADR-0002 Erratum).
    if [ -f "$LEGACY_INSTALL_PROMPT" ]; then
        rm -f -- "$LEGACY_INSTALL_PROMPT"
        echo "  removed legacy prompt: $LEGACY_INSTALL_PROMPT"
    fi
    install -m 0644 "$REPO_ROOT/prompts/new-llm-wiki.prompt.md" "$INSTALL_PROMPT"
fi

# ---------------------------------------------------------------------------
# Sanity check
# ---------------------------------------------------------------------------

echo ""
echo "Verifying install..."
if ! "$INSTALL_SCAFFOLD" --help >/dev/null 2>&1; then
    echo "error: sanity check failed — scaffold.py --help did not run cleanly." >&2
    echo "       Try: python3 $INSTALL_SCAFFOLD --help" >&2
    exit 1
fi
echo "  scaffold.py --help ... OK"

# ---------------------------------------------------------------------------
# Final summary
# ---------------------------------------------------------------------------

echo ""
echo "Install complete."
echo ""
echo "Next steps:"
if [ "$SKIP_PROMPT" = "false" ]; then
    echo "  1. Reload VS Code:  Cmd/Ctrl+Shift+P → 'Developer: Reload Window'"
    echo "  2. In any workspace, in Copilot chat:"
    echo "       /new-llm-wiki --help"
    echo "     (or invoke with args to create a vault directly)"
else
    echo "  Run:  $INSTALL_SCAFFOLD --help"
fi
echo ""
echo "Uninstall:  $SCRIPT_DIR/install.sh --uninstall"
