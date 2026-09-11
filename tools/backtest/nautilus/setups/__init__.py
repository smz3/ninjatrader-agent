"""The 5 registry setups as Nautilus strategies, one file each. Rules in words:
each file's docstring + the "rules" field of registry/strategies/<id>.json;
numbers: its spec/params.

What changes because Nautilus does the fills (its defaults, see engine.py):
- market entries fill at the signal bar's close (= the next bar's open time),
  no added slippage; SL/TP priced from that planned entry;
- stop and limit orders fill on touch, along Nautilus's bar path (adaptive:
  the extreme nearer the open first), so a bar holding both stop and target
  exits at whichever that path hits first;
- a bar that hits two pending entries (both ORB sides, two key levels) fills
  the first one on the path and cancels the rest (the old engine skipped it);
- gap-fill / key-level use the 09:30 open for their filters from the 09:29
  close on - the same instant.
"""
from .gap_fill import GapFill
from .key_level_fade import KeyLevelFade
from .orb import Orb
from .range_mode import RangeMode
from .vwap_snap import VwapSnap

SETUPS = {"orb": Orb, "range-mode": RangeMode, "vwap-snap": VwapSnap,
          "key-level-fade": KeyLevelFade, "gap-fill": GapFill}
