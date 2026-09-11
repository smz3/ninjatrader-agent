"""Range mode: failed auction beyond the opening value area -> back to the POC.

Profile = params.profile_window bars (needs half of them), each bar's volume
spread evenly over the ticks it traded (1m approximation of a real volume
profile - swap in trades data if this setup earns it). Value area grows from
the POC one tick at a time toward the side with more volume until it holds
value_area_pct. Poke = a bar trades poke_ticks+ beyond VAH (or VAL). Reclaim
= a bar closes back inside within reclaim_bars bars (the poke bar is bar 1)
-> fade with a market order at that bar's close (= the next bar's open
time). Stop = poke extreme + stop_buffer_ticks; target = POC, or the opposite
value-area edge (target_at: poc | opposite). No reclaim in time = accepted
outside -> that side is done for the day. Skip if reward < min_rr x risk
(from the reclaim close). After a reclaim the side re-arms. Pokes are only
tracked while flat. Entries from max(entry_window from, profile end).
"""
import numpy as np

from ...data import TICK
from ..base import SetupStrategy, window_mask


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
