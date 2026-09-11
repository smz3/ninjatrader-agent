"""VWAP snap-back: fade a morning stretch away from session VWAP.

VWAP and volume-weighted std dev of the typical price (h+l+c)/3, anchored at
params.vwap_anchor. Signal = a bar closes beyond VWAP +/- stretch_mult x unit
(stretch_unit: std | atr) -> fade with a market order at that close (= the
next bar's open time). Stop = spec.stop from the signal close; target = VWAP
at the signal bar (target_at: vwap) or halfway to it (half). After a signal,
a side re-arms only once a bar closes back inside the band (bars are only
checked while flat).
"""
import numpy as np

from ...data import hm
from ..base import SetupStrategy


class VwapSnap(SetupStrategy):
    def start_day(self, d):
        p, sp = self.p, self.spec
        self.i0 = int(np.searchsorted(d.mins, hm(p["vwap_anchor"])))
        self.ok = self.i0 < len(d.mins) and not (
            d.atr is None and "atr" in (p["stretch_unit"], sp["stop"]["type"]))
        if not self.ok:
            return
        h, l, c, v = d.h[self.i0:], d.l[self.i0:], d.c[self.i0:], d.v[self.i0:]
        tp = (h + l + c) / 3
        cv = np.cumsum(v)
        self.vwap = np.cumsum(tp * v) / cv
        self.std = np.sqrt(np.maximum(np.cumsum(v * tp * tp) / cv - self.vwap ** 2, 0))
        self.armed = {1: True, -1: True}

    def step(self, i, t):
        d, p, m = self.d, self.p, int(self.d.mins[i])
        if not self.ok or i < self.i0 or m < self.win_from or m >= self.win_to:
            return
        k = i - self.i0
        band = p["stretch_mult"] * (self.std[k] if p["stretch_unit"] == "std" else d.atr)
        dev = d.c[i] - self.vwap[k]
        if band <= 0 or abs(dev) < band:
            self.armed = {1: True, -1: True}
            return
        s = 1 if dev < 0 else -1
        if not self.armed[s]:
            return
        self.armed[s] = False
        if self.can_enter(t, s):
            entry, w = float(d.c[i]), float(self.vwap[k])
            target = w if p["target_at"] == "vwap" else entry + (w - entry) / 2
            self.enter(s, "market", entry, entry - s * self.dist(self.spec["stop"]), target)
