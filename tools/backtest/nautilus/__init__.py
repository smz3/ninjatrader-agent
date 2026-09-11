"""NautilusTrader engine (engine id "nautilus-1m") - the only engine since 2026-09-11.

  engine.py  venue/instrument/bar feed, one BacktestEngine per run, grid combos
  base.py    day rules every setup shares (window, news, flat_by, brackets, trades)
  setups.py  the 5 setups as Nautilus strategies
"""
from .engine import COSTS, Engine
from .setups import SETUPS
