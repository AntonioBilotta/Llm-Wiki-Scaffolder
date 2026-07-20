#Requires -Version 5.1
<#
.SYNOPSIS
    Install llm-wiki-scaffolder on Windows.

.DESCRIPTION
    - Templates and script → %APPDATA%\llm-wiki\
    - VS Code slash command prompt → VS Code user prompts folder
      (%APPDATA%\Code\User\prompts or %APPDATA%\Code - Insiders\User\prompts)

    Idempotent. Safe to re-run for updates.

.PARAMETER Uninstall
    Remove installed files (does not touch this repo or created vaults).

.PARAMETER Insiders
    Target VS Code Insiders instead of stable.

.PARAMETER NoPrompt
    Skip copying the VS Code user prompt.

.EXAMPLE
    .\bin\install.ps1
    # Full install to default locations

.EXAMPLE
    .\bin\install.ps1 -Insiders
    # Install for VS Code Insiders

.EXAMPLE
    .\bin\install.ps1 -Uninstall
    # Remove installed files
#>

[CmdletBinding()]
param(
    [switch]$Uninstall,
    [switch]$Insiders,
    [switch]$NoPrompt
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Locate repo and prerequisites
# ---------------------------------------------------------------------------

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir

$ScaffoldPy = Join-Path $RepoRoot "bin\scaffold.py"
if (-not (Test-Path $ScaffoldPy)) {
    Write-Error "Cannot locate scaffold.py at $ScaffoldPy`nRun this script from inside a clone of the llm-wiki-scaffolder repo."
    exit 1
}

# Check for Python
$PythonCmd = $null
foreach ($cmd in @("python3", "python", "py")) {
    try {
        $null = & $cmd --version 2>&1
        $PythonCmd = $cmd
        break
    } catch {
        continue
    }
}
if (-not $PythonCmd) {
    Write-Error "Python 3 is required but not found in PATH.`nInstall Python 3.8+ from https://python.org or via 'winget install Python.Python.3.11'"
    exit 1
}

# ---------------------------------------------------------------------------
# Resolve VS Code user prompts folder
# ---------------------------------------------------------------------------

function Get-VSCodePromptsDir {
    $flavor = if ($Insiders) { "Code - Insiders" } else { "Code" }
    $candidate = Join-Path $env:APPDATA "$flavor\User\prompts"
    $parentDir = Split-Path -Parent $candidate
    
    if (-not (Test-Path $parentDir)) {
        # Try the other variant as fallback
        $altFlavor = if ($Insiders) { "Code" } else { "Code - Insiders" }
        $altCandidate = Join-Path $env:APPDATA "$altFlavor\User\prompts"
        $altParent = Split-Path -Parent $altCandidate
        if (Test-Path $altParent) {
            Write-Warning "VS Code $flavor not found, using $altFlavor instead."
            return $altCandidate
        }
        Write-Error "VS Code installation not found.`nExpected: $parentDir`nInstall VS Code from https://code.visualstudio.com"
        exit 1
    }
    return $candidate
}

$VSCodePromptsDir = Get-VSCodePromptsDir

# ---------------------------------------------------------------------------
# Target paths
# ---------------------------------------------------------------------------

$InstallRoot = Join-Path $env:APPDATA "llm-wiki"
$InstallBin = Join-Path $InstallRoot "bin"
$InstallTemplates = Join-Path $InstallRoot "templates"
$InstallScaffold = Join-Path $InstallBin "scaffold.py"
$InstallPrompt = Join-Path $VSCodePromptsDir "new_llm_wiki_vault.prompt.md"

# ---------------------------------------------------------------------------
# Uninstall
# ---------------------------------------------------------------------------

if ($Uninstall) {
    Write-Host "Uninstalling llm-wiki-scaffolder..."
    $removed = 0

    foreach ($target in @($InstallScaffold, $InstallPrompt)) {
        if (Test-Path $target) {
            Remove-Item -Force $target
            Write-Host "  removed: $target"
            $removed++
        }
    }

    if (Test-Path $InstallTemplates) {
        Remove-Item -Recurse -Force $InstallTemplates
        Write-Host "  removed: $InstallTemplates\"
        $removed++
    }

    # Prune empty directories
    if ((Test-Path $InstallBin) -and @(Get-ChildItem $InstallBin).Count -eq 0) {
        Remove-Item $InstallBin
    }
    if ((Test-Path $InstallRoot) -and @(Get-ChildItem $InstallRoot).Count -eq 0) {
        Remove-Item $InstallRoot
    }

    if ($removed -eq 0) {
        Write-Host "  nothing to remove."
    }
    Write-Host "Uninstall complete."
    exit 0
}

# ---------------------------------------------------------------------------
# Install
# ---------------------------------------------------------------------------

Write-Host "Installing llm-wiki-scaffolder from $RepoRoot"
Write-Host "  scaffold:  $InstallScaffold"
Write-Host "  templates: $InstallTemplates\"
if (-not $NoPrompt) {
    Write-Host "  prompt:    $InstallPrompt"
}
Write-Host ""

# Create directories
New-Item -ItemType Directory -Force -Path $InstallBin | Out-Null
New-Item -ItemType Directory -Force -Path $InstallTemplates | Out-Null

# Templates: sync (remove old, copy new) — equivalent to rsync --delete
# First remove existing templates to ensure clean state
if (Test-Path $InstallTemplates) {
    Get-ChildItem $InstallTemplates -Recurse | Remove-Item -Recurse -Force
}

# Copy templates, excluding OS junk
$TemplatesSource = Join-Path $RepoRoot "templates"
Get-ChildItem $TemplatesSource -Recurse | 
    Where-Object { $_.Name -notin @('.DS_Store', 'Thumbs.db') -and $_.Name -notlike '.git*' } |
    ForEach-Object {
        $relativePath = $_.FullName.Substring($TemplatesSource.Length + 1)
        $destPath = Join-Path $InstallTemplates $relativePath
        if ($_.PSIsContainer) {
            New-Item -ItemType Directory -Force -Path $destPath | Out-Null
        } else {
            $destDir = Split-Path -Parent $destPath
            if (-not (Test-Path $destDir)) {
                New-Item -ItemType Directory -Force -Path $destDir | Out-Null
            }
            Copy-Item -Force $_.FullName $destPath
        }
    }

# Script: copy scaffold.py
Copy-Item -Force $ScaffoldPy $InstallScaffold

# Prompt: copy to VS Code user prompts folder
if (-not $NoPrompt) {
    $PromptSource = Join-Path $RepoRoot "prompts\new_llm_wiki_vault.prompt.md"
    if (-not (Test-Path $PromptSource)) {
        Write-Error "Missing prompt file at $PromptSource"
        exit 1
    }
    New-Item -ItemType Directory -Force -Path $VSCodePromptsDir | Out-Null
    Copy-Item -Force $PromptSource $InstallPrompt
}

# ---------------------------------------------------------------------------
# Sanity check
# ---------------------------------------------------------------------------

Write-Host ""
Write-Host "Verifying install..."

try {
    $helpOutput = & $PythonCmd $InstallScaffold --help 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "scaffold.py --help failed"
    }
    Write-Host "  scaffold.py --help: OK" -ForegroundColor Green
} catch {
    Write-Error "Sanity check failed: scaffold.py --help did not exit cleanly.`n$_"
    exit 1
}

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------

Write-Host ""
Write-Host "Installation complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Reload VS Code window (Ctrl+Shift+P -> Developer: Reload Window)"
Write-Host "  2. In Copilot Chat, type: /new_llm_wiki_vault"
Write-Host ""
Write-Host "Installed paths:"
Write-Host "  $InstallRoot\"
Write-Host "  $InstallPrompt"
