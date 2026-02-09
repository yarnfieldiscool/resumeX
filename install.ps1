# resumeX - Cursor Installation Script
# Usage: Run from your PROJECT ROOT directory
#
#   git clone https://github.com/sputnicyoji/resumeX .cursor/skills/resumex
#   .cursor/skills/resumex/install.ps1
#

$ErrorActionPreference = "Stop"

# Detect skill root (where this script lives)
$SkillRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

# Detect project root (3 levels up: .cursor/skills/resumex/)
$ProjectRoot = (Get-Item $SkillRoot).Parent.Parent.Parent.FullName

# Verify we're in the right place
$ExpectedSuffix = [IO.Path]::Combine(".cursor", "skills", "resumex")
$ActualSuffix = $SkillRoot.Substring($ProjectRoot.Length + 1)

if ($ActualSuffix -ne $ExpectedSuffix) {
    Write-Host "[ERROR] Skill must be cloned to .cursor/skills/resumex/" -ForegroundColor Red
    Write-Host "  Expected: <project>/$ExpectedSuffix"
    Write-Host "  Actual:   $SkillRoot"
    Write-Host ""
    Write-Host "Fix: git clone https://github.com/sputnicyoji/resumeX .cursor/skills/resumex"
    exit 1
}

# Create .cursor/rules/ if not exists
$RulesDir = [IO.Path]::Combine($ProjectRoot, ".cursor", "rules")
if (-not (Test-Path $RulesDir)) {
    New-Item -ItemType Directory -Path $RulesDir -Force | Out-Null
    Write-Host "[OK] Created $RulesDir"
}

# Copy .mdc to rules directory
$MdcSource = [IO.Path]::Combine($SkillRoot, "cursor", "resumex.mdc")
$MdcTarget = [IO.Path]::Combine($RulesDir, "resumex.mdc")

if (-not (Test-Path $MdcSource)) {
    Write-Host "[ERROR] .mdc file not found: $MdcSource" -ForegroundColor Red
    exit 1
}

Copy-Item $MdcSource $MdcTarget -Force
Write-Host "[OK] Installed .mdc -> .cursor/rules/resumex.mdc"

# Verify Python available
$PythonCmd = $null
foreach ($cmd in @("python3", "python")) {
    try {
        $null = & $cmd --version 2>&1
        $PythonCmd = $cmd
        break
    } catch {}
}

if ($PythonCmd) {
    Write-Host "[OK] Python found: $PythonCmd"
} else {
    Write-Host "[WARN] Python not found. Pipeline (scripts/pipeline.py) requires Python 3.8+" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Installation Complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "Skill root:  .cursor/skills/resumex/"
Write-Host "Cursor rule: .cursor/rules/resumex.mdc"
Write-Host ""
Write-Host "Usage in Cursor: Ask the AI to extract structured information from any resume."
Write-Host "The rule will be automatically loaded when relevant."
