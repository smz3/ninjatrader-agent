# NinjaTrader 8 automation - no clicks (research 2026-09-11)

User decision 2026-09-11: stop Python backtests, backtest in NinjaTrader 8 directly,
using NT8's own results (Strategy Analyzer / SystemPerformance). User must not have
to press anything in NT8 -> everything automated. ORB only first.

## What's on this PC

- NT8 8.1.8.2, running (NinjaTrader.exe), connection "Simulation" (flaky latency in log).
- User folder: `C:\Users\User\Documents\NinjaTrader 8\` - scripts in
  `bin\Custom\Strategies`, `bin\Custom\AddOns` (empty), `NinjaTrader.Custom.csproj`
  present (VS project; never build it in VS - breaks NT per forum).
- Data in `db\`: ES day bars back to the 03-17 contract; ES minute = only
  `ES 09-26`, 7 days (2026-08-12..09-11); no tick, no second data.
  -> 10y 1m history must come from NT's data server (unknown depth) or an
  import of our Databento 1m bars (NT text format, file `ES 09-26.Last.txt`,
  importing.htm). 1s/tick for Order Fill Resolution = High: also needed.
- dotnet CLI + .NET Framework 4.0.30319 present (not needed if NT compiles).

## Found in NT's own DLLs (reflection, NinjaTrader.Core.dll / Gui.dll)

- `NinjaTrader.NinjaScript.StrategyBase.RunBacktest()` - public, no args. Also
  `RunOptimization(Action)`. Settable props: `Instrument`, `BarsPeriod`, `From`,
  `To`, `OrderFillResolution`/`OrderFillResolutionType`/`Value`, `Slippage`,
  `IncludeCommission`, `BacktestCommissionTemplate`, `IsFillLimitOnTouch`,
  `BarsRequiredToTrade`, `IncludeTradeHistoryInBacktest`; results in
  `SystemPerformance` (same object the Strategy Analyzer shows).
- Strategy Analyzer GUI uses `Gui...StrategyAnalyzer.StrategyRunner.RunBacktest`
  (non-public) -> `StrategyBase.RunBacktest`.
- `NinjaTrader.Code.Compiler.Compile` exists (non-public), event
  `Compiler.CompileCompleted` public. NT compiles on startup if needed.
- Third party doing exactly this: CrossTrade MCP "RunStrategyBacktest" runs a
  compiled strategy through `Strategy.RunBacktest()`, returns trades + all
  SystemPerformance metrics "bit-identical to Strategy Analyzer":
  https://crosstrade.io/docs/api/mcp-trading/backtesting-and-optimization

## Compiling without F5

- Forum (NT staff): saving a .cs in any external editor while a NinjaScript
  Editor window is open auto-compiles:
  https://forum.ninjatrader.com/forum/ninjatrader-8/add-on-development/1274422-visual-studio-and-auto-compile-ninjascript-after-file-save
  -> keep an Editor window in the saved workspace; copying a file in = compile.
- Or: our AddOn calls `Compiler.Compile` via reflection (unsupported API).

## Plan (built 2026-09-15, not compiled yet)

1. Source of truth in repo: `ninjascript/Strategies/Orb.cs`,
   `ninjascript/AddOns/BacktestRunner.cs`; `ninjascript/deploy.ps1` copies both
   into `bin\Custom\...`.
2. AddOn `BacktestRunner` inside NT: watches `ninjascript/jobs/` **directly in
   this repo checkout** (not copied into NT8's folder - the AddOn reads the
   repo path off disk, hardcoded to this machine, single-user project).
   Job file = plain `key=value` lines (not JSON - avoids an uncertain
   NinjaScript library reference), e.g.:
   ```
   strategy=Orb
   instrument=ES 12-26
   bars_minutes=1
   from=2016-09-01
   to=2024-12-31
   prop.Slippage=0
   ```
   `prop.X=Y` sets any public strategy property X by reflection (covers both
   StrategyBase props like `Slippage` and the strategy's own
   `[NinjaScriptProperty]` params like `RangeStartTime`). Drop a `.job` file
   in `ninjascript/jobs/`, AddOn picks it up via FileSystemWatcher, calls
   `RunBacktest()`, writes `ninjascript/results/<jobid>.result.txt` (perf
   summary + full trade list) and moves the job to `jobs/done/`.
3. One-time bootstrap: get the AddOn compiled once (editor-open-while-saving
   trick, or F5 in NinjaScript Editor - same as any strategy), then everything
   else is file drops, no more clicking.
4. Genuinely unverified: `Instrument.GetInstrument(name)`, whether
   `RunBacktest()` needs no other setup beyond `Instrument`/`BarsPeriod`/
   `From`/`To`, and the exact `SystemPerformance` property names used in
   `FormatPerformance()`. First compile will likely surface a few of these as
   errors - expected, fix forward same as Orb.cs's OrderFillResolution bug.
4. Data: no need for a new data-trial account or MultiCharts - we already
   own 10y of ES 1m bars from Databento. `python -m tools.nt_export` converts
   `data/databento/ES...1m...parquet` to NT8 import format (yearly .txt,
   `data/nt_import/`, America/Chicago timestamps - CME session templates are
   in Central time; verify against NT8's own Time Zone setting before
   trusting ORB's session-open minute). Import into a dedicated
   backtest-only instrument, not a live contract, so this doesn't collide
   with the real "ES 09-26" data used for trading. Commission template $3.50
   RT (Lucid ES). Check Order Fill Resolution High needs 1-tick/1-second
   data - 1m bars only support lower fill-resolution settings for now.
5. ORB in NinjaScript per registry/strategies/orb.json (both-sides-bar rule
   still open with user).

## Headless recompile via Windows UI Automation (found + proven 2026-09-17)

User asked why every AddOn/Strategy code change still needed a manual click
in NT8's GUI. Answer: it doesn't - NT8's NinjaScript Editor is a normal
top-level window, drivable from PowerShell with no NT8-side changes needed.
Proven working end-to-end this session:

1. Find the editor window (it's a *separate top-level HWND* under the
   NinjaTrader.exe process, not just the Control Center's MainWindowTitle -
   use `EnumWindows` + `GetWindowThreadProcessId` filtered to NT8's pid, not
   `FindWindow`/`Get-Process .MainWindowTitle`, which only sees one window
   per process). Title is `"NinjaScript Editor - <context>"` (e.g. `- Add on
   - BacktestRunner`) - substring-match, it changes with whatever tab has
   focus.
2. **Gotcha #1 - stale tab buffer:** if that file's tab was already open
   before you overwrote it on disk (via deploy.ps1 or otherwise), the editor
   does **not** auto-reload it. Pressing F5 recompiles the *stale in-memory
   buffer*, silently ignoring your on-disk change - no error, no warning, it
   just keeps running old code. Detectable/fixable: try to close that tab: if
   NT8 pops "Close Tab - unsaved changes will be lost", the tab is stale
   relative to disk (we never edit inside the NT8 editor ourselves, so any
   "unsaved changes" it thinks it has are exactly this drift). Click **Yes**
   to discard, then reopen the file fresh by double-clicking it in the
   "NinjaScript Explorer" tree panel (docked top-right) - that forces a
   read from disk. *Only* safe to always-discard because this repo is the
   sole source of truth for these files (deploy.ps1 is the only writer) -
   if a human ever edits directly in NT8's editor instead, this would
   silently blow that away.
3. Restore-if-minimized (`ShowWindow(hwnd, 9)` then `3`), `SetForegroundWindow`,
   click into the editor body once (keyboard focus needs to land in the text
   pane, not just the window), then `SendKeys::SendWait("{F5}")`. F5 recompiles
   the **whole custom assembly**, not just the open tab - doesn't matter which
   file is showing as long as *no* open tab for a changed file has gone stale
   per #2.
4. **Gotcha #2 - no readable output surface:** NinjaScript `Print()` output
   (the "NinjaScript Output" window) and compile errors are **not** exposed
   via UI Automation `TextPattern`/`ValuePattern`/`Name` - it's a
   custom-rendered editor control, `AutomationElement.FromHandle` +
   `TreeWalker` only surfaces tab labels and button glyphs, never the actual
   log text. The only way found to read it back programmatically: restore +
   foreground the window, screenshot the whole screen
   (`System.Drawing.Graphics.CopyFromScreen`), save PNG, read the PNG as an
   image. Same applies to checking for compile errors - no error text is
   queryable, only visually confirmable (screenshot the editor after F5 and
   look for an error-list panel / red markers).
5. NT8's platform log files (`Documents\NinjaTrader 8\log\log.*.txt`) do
   **not** reliably capture new activity - one log file's mtime updated
   without any new lines appearing in it across two full recompile+job
   cycles this session (cause unclear, possibly a session-numbering quirk
   after Session Break). Don't trust "no new log lines" as proof nothing
   happened - always cross-check with an Output-panel screenshot instead.
6. Not yet built: a consolidated script wrapping steps 1-4 (e.g.
   `tools/nt8_recompile.ps1` or under `.claude/scripts/`) - this session did
   every step by hand via ad hoc PowerShell each time. Next session doing
   another Orb.cs/BacktestRunner.cs change should build that script rather
   than repeating the manual dance.
