"""VWAP snap-back: fade a morning stretch away from session VWAP.

VWAP and volume-weighted std dev of the typical price (h+l+c)/3, anchored at
params.vwap_anchor. Signal = a bar closes beyond VWAP +/- stretch_mult x unit
(stretch_unit: std | atr). Fade at the next bar's open. Stop = spec.stop from
the fill; target = VWAP at the signal bar (target_at: vwap) or halfway to it
(half). After a signal, both sides re-arm only once a bar closes back inside
the band.
"""
import numpy as np

from ..data import hm
from ..sim import tick


def run(d, sim, p, sp):
    i0 = sim.idx(hm(p["vwap_anchor"]))
    n = len(sim.m)
    if i0 >= n or d.atr is None and "atr" in (p["stretch_unit"], sp["stop"]["type"]):
        return
    h, l, c, v = d.h[i0:], d.l[i0:], d.c[i0:], d.v[i0:]
    tp = (h + l + c) / 3
    cv = np.cumsum(v)
    vwap = np.cumsum(tp * v) / cv
    std = np.sqrt(np.maximum(np.cumsum(v * tp * tp) / cv - vwap * vwap, 0))
    armed = {1: True, -1: True}
    i, end = max(i0, sim.idx(sim.win_from)), min(n - 1, sim.flat_i)
    while i < end and sim.m[i] < sim.win_to:
        k = i - i0
        band = p["stretch_mult"] * (std[k] if p["stretch_unit"] == "std" else d.atr)
        dev = sim.c[i] - vwap[k]
        if band <= 0 or abs(dev) < band:
            armed = {1: True, -1: True}
            i += 1
            continue
        s = 1 if dev < 0 else -1
        if not armed[s]:
            i += 1
            continue
        armed[s] = False
        j = i + 1
        t = None
        if sim.can_enter(j, s):
            entry = sim.fill(j, s, "market")
            stop = entry - s * sim.dist(sp["stop"])
            w = float(vwap[k])
            target = tick(w if p["target_at"] == "vwap" else entry + (w - entry) / 2)
            t = sim.trade(j, s, "market", entry, stop, target)
        i = (t.exit_i if t else i) + 1
