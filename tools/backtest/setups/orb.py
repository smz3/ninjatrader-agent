"""Opening Range Breakout.

Range = high/low of params.range_window. Buy stop 1 tick above the high, sell
stop 1 tick below the low; the first break is the only trade of the day (a
break during a news block = no trade). Entries from max(entry_window from,
range end). A bar breaking both sides = can't tell which came first -> skip.
Stop (params.stop_at): other-side = 1 tick past the opposite side; middle =
range middle. Target = spec.target (range = x range height, r = x stop).
params.atr_mode: off | range-filter (skip if range > range_max_atr x ATR) |
atr-stop (stop = atr_stop x ATR from the fill instead of stop_at).
"""
from ..data import TICK, hm
from ..sim import tick


def run(d, sim, p, sp):
    a, b = (hm(x) for x in p["range_window"].split("-"))
    i0, i1 = sim.idx(a), sim.idx(b)
    if i1 - i0 < (b - a) // 2:
        return
    hi, lo = max(sim.h[i0:i1]), min(sim.l[i0:i1])
    mode = p["atr_mode"]
    if mode != "off" and d.atr is None:
        return
    if mode == "range-filter" and hi - lo > p["range_max_atr"] * d.atr:
        return
    up, dn = hi + TICK, lo - TICK
    for i in range(max(i1, sim.idx(sim.win_from)), min(len(sim.m), sim.flat_i)):
        if sim.m[i] >= sim.win_to:
            return
        hit_up, hit_dn = sim.touched(i, 1, "stop", up), sim.touched(i, -1, "stop", dn)
        if not (hit_up or hit_dn):
            continue
        if hit_up and hit_dn:
            return
        s = 1 if hit_up else -1
        if not sim.can_enter(i, s):
            return
        entry = sim.fill(i, s, "stop", up if s > 0 else dn)
        if mode == "atr-stop":
            stop = entry - s * sim.dist({"type": "atr", "value": p["atr_stop"]})
        elif p["stop_at"] == "middle":
            stop = tick((hi + lo) / 2)
        else:
            stop = dn if s > 0 else up
        target = entry + s * sim.dist(sp["target"], risk=(entry - stop) * s, ref=hi - lo)
        sim.trade(i, s, "stop", entry, stop, target)
        return
