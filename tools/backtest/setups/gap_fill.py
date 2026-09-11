"""Small gap fill: trade the RTH open back toward the prior RTH close.

gap = 09:30 open - prior RTH close (same contract only). Trade if min_gap <=
|gap| <= max_gap (gap_unit: atr | points), toward the close, at the open of
the bar entry_delay_min after 09:30 - skipped if the gap already filled
before then. Stop = spec.stop from the fill; target = prior close.
"""
from ..data import RTH_OPEN


def run(d, sim, p, sp):
    need_atr = "atr" in (p["gap_unit"], sp["stop"]["type"])
    if d.prev_close is None or need_atr and d.atr is None:
        return
    gap = d.rth_open - d.prev_close
    size = abs(gap) / (d.atr if p["gap_unit"] == "atr" else 1)
    if gap == 0 or not p["min_gap"] <= size <= p["max_gap"]:
        return
    s, pc = (-1 if gap > 0 else 1), d.prev_close
    i0, e = sim.idx(RTH_OPEN), sim.idx(RTH_OPEN + p["entry_delay_min"])
    if e >= len(sim.m):
        return
    if any((sim.l[k] <= pc) if s < 0 else (sim.h[k] >= pc) for k in range(i0, e)):
        return
    if not sim.can_enter(e, s):
        return
    entry = sim.fill(e, s, "market")
    sim.trade(e, s, "market", entry, entry - s * sim.dist(sp["stop"]), pc)
