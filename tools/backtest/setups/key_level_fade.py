"""Key level fade: first touch of prior-day RTH high/low or overnight high/low.

Resting limit touch_ticks inside each level: sell at pdh/onh, buy at pdl/onl.
A level counts only if the RTH open is on the near side of it; its first
touch uses it up (filled, blocked by news, or touched while already in a
trade). Two levels hit on one bar: same side -> the nearer one fills, both
used up; opposite sides -> can't tell the order, skip both. Stop = spec.stop
from the fill, target = spec.target (R). Only first_touch_only=true exists.
"""
from ..data import RTH_OPEN, TICK


def run(d, sim, p, sp):
    if not p["first_touch_only"]:
        raise NotImplementedError("key-level-fade: only first_touch_only=true")
    if sp["stop"]["type"] == "atr" and d.atr is None:
        return
    ref = {"pdh": (d.prev_high, -1), "pdl": (d.prev_low, 1),
           "onh": (d.on_high, -1), "onl": (d.on_low, 1)}
    live = []
    for name in p["levels"]:
        lvl, s = ref[name]
        if lvl is not None and (d.rth_open - lvl) * s > 0:
            live.append((lvl + s * p["touch_ticks"] * TICK, s))
    i, end = sim.idx(max(sim.win_from, RTH_OPEN)), min(len(sim.m), sim.flat_i)
    while live and i < end and sim.m[i] < sim.win_to:
        hit = [x for x in live if sim.touched(i, x[1], "limit", x[0])]
        if not hit:
            i += 1
            continue
        live = [x for x in live if x not in hit]
        sides = {x[1] for x in hit}
        s = sides.pop()
        if sides or not sim.can_enter(i, s):
            i += 1
            continue
        px = max(x[0] for x in hit) if s > 0 else min(x[0] for x in hit)
        entry = sim.fill(i, s, "limit", px)
        stop = entry - s * sim.dist(sp["stop"])
        target = entry + s * sim.dist(sp["target"], risk=(entry - stop) * s)
        t = sim.trade(i, s, "limit", entry, stop, target)
        if t:
            for k in range(i + 1, t.exit_i + 1):
                live = [x for x in live if not sim.touched(k, x[1], "limit", x[0])]
            i = t.exit_i
        i += 1
