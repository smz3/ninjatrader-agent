<#
.SYNOPSIS
    Copy this repo's NinjaScript source + news filter data into NT8's folder.

.DESCRIPTION
    NT8 only compiles what's in Documents\NinjaTrader 8\bin\Custom\... - this
    repo keeps the real source under ninjascript\ so it's git-tracked. Run
    this after editing Orb.cs, and after refreshing the news CSV with
    `python -m tools.nt_export --news`. If NT8 is running, this also opens
    the NinjaScript Editor (NT8 only auto-compiles on file save while an
    editor window is open) and waits for the compiled DLL to update - no
    NT8 restart or re-login needed. See docs/research/nt8-automation-notes.md.
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

$addOnsDst = Join-Path $nt8Root "bin\Custom\AddOns"
New-Item -ItemType Directory -Force -Path $addOnsDst | Out-Null
Copy-Item (Join-Path $repoRoot "ninjascript\AddOns\*.cs") $addOnsDst -Force
Write-Host "Copied add-ons -> $addOnsDst"

$newsSrc = Join-Path $repoRoot "data\nt_import\news_usd_high.csv"
if (Test-Path $newsSrc) {
    Copy-Item $newsSrc (Join-Path $nt8Root "news_usd_high.csv") -Force
    Write-Host "Copied news filter -> $nt8Root\news_usd_high.csv"
} else {
    Write-Warning "No $newsSrc yet - run 'python -m tools.nt_export --news' first. Orb.cs will run with no news filter until this exists."
}

$nt = Get-Process NinjaTrader -ErrorAction SilentlyContinue
if (-not $nt) {
    Write-Host "NT8 not running - it compiles on next start."
    return
}

# Open the NinjaScript Editor via UI Automation if it isn't already open:
# Control Center > New > NinjaScript Editor.
Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes
$A = [System.Windows.Automation.AutomationElement]
$scope = [System.Windows.Automation.TreeScope]
$pidCond = New-Object System.Windows.Automation.PropertyCondition($A::ProcessIdProperty, [int]$nt.Id)
$windows = $A::RootElement.FindAll($scope::Children, $pidCond)
if (-not ($windows | Where-Object { $_.Current.Name -like "NinjaScript Editor*" })) {
    $menuCond = New-Object System.Windows.Automation.PropertyCondition($A::ControlTypeProperty, [System.Windows.Automation.ControlType]::MenuItem)
    $newMenu = $null
    foreach ($w in $windows) {
        $newMenu = $w.FindAll($scope::Descendants, $menuCond) | Where-Object { $_.Current.Name -eq "New" } | Select-Object -First 1
        if ($newMenu) { break }
    }
    if (-not $newMenu) { throw "Couldn't find NT8's Control Center 'New' menu - open the NinjaScript Editor by hand." }
    $newMenu.GetCurrentPattern([System.Windows.Automation.ExpandCollapsePattern]::Pattern).Expand()
    Start-Sleep -Seconds 1
    $editorCond = New-Object System.Windows.Automation.PropertyCondition($A::NameProperty, "NinjaScript Editor")
    $A::RootElement.FindFirst($scope::Descendants, $editorCond).GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
    Start-Sleep -Seconds 5
    Write-Host "Opened NinjaScript Editor."
}

# Copy-Item keeps the source mtime, so a copied file may not look changed -
# touch everything we deployed so the editor sees a save and compiles.
$dll = Join-Path $nt8Root "bin\Custom\NinjaTrader.Custom.dll"
$before = (Get-Item $dll).LastWriteTime
Get-ChildItem (Join-Path $strategiesDst "*.cs"), (Join-Path $addOnsDst "*.cs") | ForEach-Object { $_.LastWriteTime = Get-Date }

for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep -Seconds 1
    if ((Get-Item $dll).LastWriteTime -gt $before) {
        Write-Host "Compiled OK ($((Get-Item $dll).LastWriteTime))."
        return
    }
}
Write-Warning "DLL didn't update in 60s - likely a compile error. Check the NinjaScript Editor's error list."
exit 1
