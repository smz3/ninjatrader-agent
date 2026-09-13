<#
.SYNOPSIS
    Copy this repo's NinjaScript source + news filter data into NT8's folder.

.DESCRIPTION
    NT8 only compiles what's in Documents\NinjaTrader 8\bin\Custom\... - this
    repo keeps the real source under ninjascript\ so it's git-tracked. Run
    this after editing Orb.cs, and after refreshing the news CSV with
    `python -m tools.nt_export --news`. Then open NinjaScript Editor in NT8
    (or restart it) to trigger a compile - see docs/research/nt8-automation-notes.md
    for why a plain file copy alone doesn't recompile.
#>

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$nt8Root = Join-Path $env:USERPROFILE "Documents\NinjaTrader 8"

if (-not (Test-Path $nt8Root)) {
    throw "NinjaTrader 8 folder not found at $nt8Root - is NT8 installed for this user?"
}

$strategiesDst = Join-Path $nt8Root "bin\Custom\Strategies"
New-Item -ItemType Directory -Force -Path $strategiesDst | Out-Null
Copy-Item (Join-Path $repoRoot "ninjascript\Strategies\*.cs") $strategiesDst -Force
Write-Host "Copied strategies -> $strategiesDst"

$newsSrc = Join-Path $repoRoot "data\nt_import\news_usd_high.csv"
if (Test-Path $newsSrc) {
    Copy-Item $newsSrc (Join-Path $nt8Root "news_usd_high.csv") -Force
    Write-Host "Copied news filter -> $nt8Root\news_usd_high.csv"
} else {
    Write-Warning "No $newsSrc yet - run 'python -m tools.nt_export --news' first. Orb.cs will run with no news filter until this exists."
}

Write-Host "Now open NinjaScript Editor in NT8 (or restart NT8) so it compiles the copied file."
