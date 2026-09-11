"""Small gap fill: trade the RTH open back toward the prior RTH close.

gap = 09:30 open - prior RTH close (same contract only). Trade if min_gap <=
|gap| <= max_gap (gap_unit: atr | points), toward the close, with a market
order at the close of the bar before 09:30 + entry_delay_min (the same
instant as that bar's open; delay 0 = the 09:29 close) - skipped if the gap
already filled before then. Stop = spec.stop from that close; target = prior
close.
"""
from ...data import RTH_OPEN
from ..base import SetupStrategy


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
