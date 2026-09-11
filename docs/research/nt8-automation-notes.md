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

## Plan (not built yet)

1. Source of truth in repo (e.g. `ninjascript/Strategies/Orb.cs`,
   `ninjascript/AddOns/BacktestRunner.cs`); a deploy step copies into
   `bin\Custom\...`.
2. AddOn `BacktestRunner` inside NT: watches a jobs folder; job JSON = strategy,
   params, instrument, dates, fill resolution, commission; creates the strategy,
   sets props, `RunBacktest()`, writes SystemPerformance summary + every trade
   (CSV/JSON) to a results folder. No Python metrics - NT's numbers only.
3. One-time bootstrap: get the AddOn compiled once (editor-open trick or NT
   restart), then everything else is file drops.
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
