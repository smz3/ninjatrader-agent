"""Opening Range Breakout.

Range = high/low of params.range_window (needs half its bars). Buy stop 1 tick
above the high and sell stop 1 tick below the low rest together from
max(entry_window from, range end); the first fill is the only trade of the
day and cancels the other side. A break while entries are off for news = no
trade that day. A bar breaking both sides fills whichever side Nautilus's bar
path reaches first (the old engine skipped the day). Stop (params.stop_at):
other-side = 1 tick past the opposite side; middle = range middle. Target =
spec.target (range = x range height, r = x stop), priced from the stop
trigger. params.atr_mode: off | range-filter (skip if range > range_max_atr x
ATR) | atr-stop (stop = atr_stop x ATR from the trigger instead of stop_at).
"""
from ...data import TICK
from ..base import SetupStrategy, tick, window_mask


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
