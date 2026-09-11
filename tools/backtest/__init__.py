"""1-minute backtester for the setups in registry/strategies, on NautilusTrader.

  data.py     ES 1m bars -> ET sessions + daily levels (ATR, prior day, overnight, news)
  nautilus/   the engine: venue/instrument/bar feed, shared day rules, the setups
  metrics.py  per-1-ES stats after costs (registry METRICS)
  prop.py     real trade days -> tools.prop_sim (LucidDaily eval + funded)
  runner.py   grid over the strategy's `grid`, records a run via tools.registry

The old home-made fill engine (sim.py + setups/, runs tagged "python-1m") was
deleted 2026-09-11; its runs and trade files stay in the registry for reference.

CLI: python -m tools.backtest --help
"""
