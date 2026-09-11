"""Python 1-minute backtester for the setups in registry/strategies.

  data.py     ES 1m bars -> ET sessions + daily levels (ATR, prior day, overnight, news)
  sim.py      shared fill/exit model (stop-first, costs, flat_by, news flattening)
  setups/     one file per strategy id: turns a session into trades via sim
  metrics.py  per-1-ES stats after costs (registry METRICS)
  prop.py     real trade days -> tools.prop_sim (LucidDaily eval + funded)
  runner.py   grid over the strategy's `grid`, records a run via tools.registry

CLI: python -m tools.backtest --help
"""
