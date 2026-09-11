"""NautilusTrader engine (engine id "nautilus-1m") - the default since 2026-09-11.

  engine.py  venue/instrument/bar feed, one BacktestEngine per run, grid combos
  base.py    day rules every setup shares (window, news, flat_by, brackets, trades)
  setups.py  the 5 setups as Nautilus strategies

The old home-made fill engine (sim.py + setups/) stays as "python-1m" only to
compare against until the Nautilus results are checked.
"""
from .engine import COSTS, Engine
