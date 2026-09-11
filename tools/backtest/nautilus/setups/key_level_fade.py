"""Key level fade: first touch of prior-day RTH high/low or overnight high/low.

Resting limit touch_ticks inside each level: sell at pdh/onh, buy at pdl/onl.
A level counts only if the RTH open is on the near side of it; its first
touch uses it up (filled, blocked by news, or touched while already in a
trade). All live levels rest at once from max(entry_window from, 09:30): the
first to fill cancels the rest, and every level that bar touched is used up
(the old engine: same side -> nearer fills, opposite sides -> skip both).
Stop = spec.stop from the limit price, target = spec.target (R). Only
first_touch_only=true exists.
"""
from ...data import RTH_OPEN, TICK
from ..base import SetupStrategy, tick


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
