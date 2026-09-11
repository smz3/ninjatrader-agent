"""Range mode: failed auction beyond the opening value area -> back to the POC.

Profile = params.profile_window bars, each bar's volume spread evenly over the
ticks it traded (1m approximation of a real volume profile - swap in trades
data if this setup earns it). Value area grows from the POC one tick at a
time toward the side with more volume until it holds value_area_pct.
Poke = a bar trades poke_ticks+ beyond VAH (or VAL). Reclaim = a bar closes
back inside within reclaim_bars bars (the poke bar is bar 1) -> fade at the
next bar's open. Stop = poke extreme + stop_buffer_ticks; target = POC, or
the opposite value-area edge (target_at: poc | opposite). No reclaim in time
= accepted outside -> that side is done for the day. Skip if reward < min_rr
x risk. After a trade the side re-arms. Entries from max(entry_window from,
profile end).
"""
import numpy as np

from ..data import TICK, hm


def profile(h, l, v, pct):
    """(poc, vah, val) of 1m bars with volume spread evenly per tick."""
    lo = min(l)
    n = int(round((max(h) - lo) / TICK)) + 1
    vol = np.zeros(n)
    for hi, lw, vv in zip(h, l, v):
        a, b = int(round((lw - lo) / TICK)), int(round((hi - lo) / TICK))
        vol[a:b + 1] += vv / (b - a + 1)
    poc = int(vol.argmax())
    need, have, up, dn = pct / 100 * vol.sum(), vol[poc], poc, poc
    while have < need:
        nu = vol[up + 1] if up + 1 < n else -1.0
        nd = vol[dn - 1] if dn > 0 else -1.0
        if nu >= nd:
            up, have = up + 1, have + nu
        else:
            dn, have = dn - 1, have + nd
    return lo + poc * TICK, lo + up * TICK, lo + dn * TICK


def run(d, sim, p, sp):
    a, b = (hm(x) for x in p["profile_window"].split("-"))
    i0, i1 = sim.idx(a), sim.idx(b)
    if i1 - i0 < (b - a) // 2:
        return
    poc, vah, val = profile(sim.h[i0:i1], sim.l[i0:i1], sim.v[i0:i1], p["value_area_pct"])
    if vah - val < 2 * TICK:
        return
    poke, buf = p["poke_ticks"] * TICK, p["stop_buffer_ticks"] * TICK
    edges = {-1: vah, 1: val}            # short fades above VAH, long fades below VAL
    state = {-1: None, 1: None}          # None | [poke bar, extreme] | "dead"
    i, end = max(i1, sim.idx(sim.win_from)), min(len(sim.m) - 1, sim.flat_i)
    while i < end and sim.m[i] < sim.win_to:
        for s, edge in edges.items():
            st = state[s]
            if st == "dead":
                continue
            if st is None:
                if not (sim.h[i] >= edge + poke if s < 0 else sim.l[i] <= edge - poke):
                    continue
                st = state[s] = [i, sim.h[i] if s < 0 else sim.l[i]]
            else:
                st[1] = max(st[1], sim.h[i]) if s < 0 else min(st[1], sim.l[i])
            if not (sim.c[i] < edge if s < 0 else sim.c[i] > edge):
                if i - st[0] + 1 >= p["reclaim_bars"]:
                    state[s] = "dead"
                continue
            state[s] = None
            j = i + 1
            if not sim.can_enter(j, s):
                continue
            entry = sim.fill(j, s, "market")
            stop = st[1] - s * buf
            target = poc if p["target_at"] == "poc" else edges[-s]
            risk, reward = (entry - stop) * s, (target - entry) * s
            if risk <= 0 or reward < p["min_rr"] * risk:
                continue
            t = sim.trade(j, s, "market", entry, stop, target)
            if t:
                i = t.exit_i
                break
        i += 1
