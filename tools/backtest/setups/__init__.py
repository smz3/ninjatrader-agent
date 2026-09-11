"""One module per strategy id. Each has run(day, sim, params, spec): it reads the
session's bars and levels and enters/exits only through sim (sim.can_enter,
sim.fill, sim.trade). Rule details sit in each module's docstring; the numbers
live in registry/strategies/<id>.json.
"""
from . import gap_fill, key_level_fade, orb, range_mode, vwap_snap

SETUPS = {
    "orb": orb.run,
    "range-mode": range_mode.run,
    "vwap-snap": vwap_snap.run,
    "key-level-fade": key_level_fade.run,
    "gap-fill": gap_fill.run,
}
