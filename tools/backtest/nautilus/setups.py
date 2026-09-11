"""The 5 registry setups as Nautilus strategies. Same rules as the old
tools/backtest/setups/*.py (read their docstrings); numbers live in
registry/strategies/<id>.json.

What changes because Nautilus does the fills (its defaults, see engine.py):
- market entries fill at the signal bar's close (= the next bar's open time),
  no added slippage; SL/TP priced from that planned entry;
- stop and limit orders fill on touch, along Nautilus's O-H-L-C bar path, so a
  bar holding both stop and target exits at whichever that path hits first;
- a bar that hits two pending entries (both ORB sides, two key levels) fills
  the first one on the path and cancels the rest (the old engine skipped it);
- gap-fill / key-level use the 09:30 open for their filters from the 09:29
  close on - the same instant.
"""
import numpy as np

from ..data import RTH_OPEN, TICK, hm
from ..setups.range_mode import profile
from ..sim import tick
from .base import SetupStrategy


def window_mask(d, spec: str):
    a, b = (hm(x) for x in spec.split("-"))
    r = (d.mins >= a) & (d.mins < b)
    return r, b, r.sum() >= (b - a) // 2


class Orb(SetupStrategy):
    def start_day(self, d):
        p = self.p
        r, self.b, enough = window_mask(d, p["range_window"])
        self.done = not enough or (p["atr_mode"] != "off" and d.atr is None)
        if self.done:
            return
        self.hi, self.lo = float(d.h[r].max()), float(d.l[r].min())
        if p["atr_mode"] == "range-filter" and self.hi - self.lo > p["range_max_atr"] * d.atr:
            self.done = True
        self.up, self.dn = self.hi + TICK, self.lo - TICK
        self.start = max(self.b, self.win_from)

    def watch(self, i):
        # the break came while entries were off for news -> no trade today
        d, m = self.d, int(self.d.mins[i])
        if (not self.done and not self.pending and self.pos is None and m >= self.start
                and self.blocked(m) and (d.h[i] >= self.up or d.l[i] <= self.dn)):
            self.done = True
            self.news_skipped += 1

    def step(self, i, t):
        if self.done or self.pending or t < self.start:
            return
        p = self.p
        for s, px in ((1, self.up), (-1, self.dn)):
            if not self.can_enter(t, s, count=False):
                continue
            if p["atr_mode"] == "atr-stop":
                stop = px - s * self.dist({"type": "atr", "value": p["atr_stop"]})
            elif p["stop_at"] == "middle":
                stop = tick((self.hi + self.lo) / 2)
            else:
                stop = self.dn if s > 0 else self.up
            target = px + s * self.dist(self.spec["target"], risk=(px - stop) * s, ref=self.hi - self.lo)
            self.enter(s, "stop", px, stop, target)

    def on_entry(self, oid):
        self.done = True


class KeyLevelFade(SetupStrategy):
    def start_day(self, d):
        sp, p = self.spec, self.p
        if not p["first_touch_only"]:
            raise NotImplementedError("key-level-fade: only first_touch_only=true")
        self.live, self.rest = [], {}
        self.start = max(self.win_from, RTH_OPEN)
        if sp["stop"]["type"] == "atr" and d.atr is None:
            return
        ref = {"pdh": (d.prev_high, -1), "pdl": (d.prev_low, 1),
               "onh": (d.on_high, -1), "onl": (d.on_low, 1)}
        for name in p["levels"]:
            lvl, s = ref[name]
            if lvl is not None and (d.rth_open - lvl) * s > 0:
                self.live.append((lvl + s * p["touch_ticks"] * TICK, s))

    def watch(self, i):
        # first touch uses a level up: filled, or touched while off (news / in a trade)
        d = self.d
        if not self.live or d.mins[i] < self.start:
            return
        for lv in [lv for lv in self.live if (d.l[i] <= lv[0] if lv[1] > 0 else d.h[i] >= lv[0])]:
            self.live.remove(lv)
            self.news_skipped += self.pos is None and self.blocked(int(d.mins[i]))

    def step(self, i, t):
        if t < self.start:
            return
        self.rest = {k: lv for k, lv in self.rest.items() if k in self.pending}
        resting = set(self.rest.values())
        for lv in self.live:
            px, s = lv
            if lv in resting or not self.can_enter(t, s, count=False):
                continue
            stop = px - s * self.dist(self.spec["stop"])
            oid = self.enter(s, "limit", px, stop,
                             px + s * self.dist(self.spec["target"], risk=(px - tick(stop)) * s))
            if oid is not None:
                self.rest[oid] = lv

    def on_entry(self, oid):
        lv = self.rest.pop(oid, None)
        if lv in self.live:
            self.live.remove(lv)
        self.rest = {}


class RangeMode(SetupStrategy):
    def start_day(self, d):
        p = self.p
        r, self.b, self.ok = window_mask(d, p["profile_window"])
        if not self.ok:
            return
        self.poc, vah, val = profile(d.h[r], d.l[r], d.v[r], p["value_area_pct"])
        self.ok = vah - val >= 2 * TICK
        self.edges = {-1: vah, 1: val}        # short fades above VAH, long below VAL
        self.st = {-1: None, 1: None}         # None | [poke bar, extreme] | "dead"

    def step(self, i, t):
        d, p, m = self.d, self.p, int(self.d.mins[i])
        if not self.ok or m < max(self.b, self.win_from) or m >= self.win_to:
            return
        poke, buf = p["poke_ticks"] * TICK, p["stop_buffer_ticks"] * TICK
        for s, edge in self.edges.items():
            st = self.st[s]
            if st == "dead":
                continue
            if st is None:
                if not (d.h[i] >= edge + poke if s < 0 else d.l[i] <= edge - poke):
                    continue
                st = self.st[s] = [i, float(d.h[i] if s < 0 else d.l[i])]
            else:
                st[1] = max(st[1], float(d.h[i])) if s < 0 else min(st[1], float(d.l[i]))
            if not (d.c[i] < edge if s < 0 else d.c[i] > edge):
                if i - st[0] + 1 >= p["reclaim_bars"]:
                    self.st[s] = "dead"
                continue
            self.st[s] = None
            if not self.can_enter(t, s):
                continue
            entry = float(d.c[i])
            stop = st[1] - s * buf
            target = self.poc if p["target_at"] == "poc" else self.edges[-s]
            risk, reward = (entry - stop) * s, (target - entry) * s
            if risk <= 0 or reward < p["min_rr"] * risk:
                continue
            self.enter(s, "market", entry, stop, target)
            if self.pos is not None:
                break


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


class GapFill(SetupStrategy):
    def start_day(self, d):
        p, sp = self.p, self.spec
        self.go = None
        need_atr = "atr" in (p["gap_unit"], sp["stop"]["type"])
        if d.prev_close is None or need_atr and d.atr is None:
            return
        gap = d.rth_open - d.prev_close
        size = abs(gap) / (d.atr if p["gap_unit"] == "atr" else 1)
        if gap != 0 and p["min_gap"] <= size <= p["max_gap"]:
            self.go = (-1 if gap > 0 else 1, d.prev_close, RTH_OPEN + p["entry_delay_min"])

    def watch(self, i):
        # gap already filled before the entry time -> skip
        d = self.d
        if self.go and RTH_OPEN <= d.mins[i] < self.go[2]:
            s, pc, _ = self.go
            if (d.l[i] <= pc) if s < 0 else (d.h[i] >= pc):
                self.go = None

    def step(self, i, t):
        if not self.go or t < self.go[2]:
            return
        s, pc, _ = self.go
        self.go = None
        if self.can_enter(t, s):
            entry = float(self.d.c[i])
            self.enter(s, "market", entry, entry - s * self.dist(self.spec["stop"]), pc)


SETUPS = {"orb": Orb, "range-mode": RangeMode, "vwap-snap": VwapSnap,
          "key-level-fade": KeyLevelFade, "gap-fill": GapFill}
