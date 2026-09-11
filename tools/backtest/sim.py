"""Shared trade simulator on 1m bars - every setup enters and exits through it.

Fill model (conservative - 1m bars don't show the order of prices inside a bar):
- market entry: that bar's open + slippage.
- stop entry: at the trigger (or the bar's open if it gapped past) + slippage.
- limit (entry or target): only when price trades THROUGH it by 1 tick; filled
  at the limit (or a better open), no slippage.
- stop-loss: at the stop (or a worse open) + slippage.
- stop and target inside one bar -> stop first. On the bar a stop/limit entry
  fills, the stop is checked but not the target (can't know it came after).
- forced exits at the open of the first bar at/after flat_by or a news
  window start: market + slippage.
- news: USD High event at E -> no entries (signal dropped, counted in
  news_skipped) and no open position during bars starting in
  [E - before, E + after). All-day event (elections) = no trading that day.
- entry_window [from, to): entries only on bars starting from <= t < to.
- max_stop_pts: a trade whose stop is wider is skipped (signal dropped).
Costs per 1 ES: commission round turn + slippage (ticks per side) on every
market/stop fill. P/L in R = net $ / (stop distance x $50).
"""
from bisect import bisect_left
from dataclasses import dataclass

from .data import PT_USD, RTH_CLOSE, TICK, Day, hm


@dataclass
class Trade:
    date: str
    side: int            # +1 long, -1 short
    entry_min: int
    entry: float
    stop: float
    target: float
    exit_min: int
    exit: float
    reason: str          # target | stop | flat | news | eod
    pnl_pts: float       # after slippage, before commission
    pnl_usd: float       # per 1 ES, after all costs
    risk_pts: float
    r: float
    peak_r: float        # best open profit in R (for intraday-trailing drawdown)
    exit_i: int = 0


def tick(x: float) -> float:
    return round(x / TICK) * TICK


class Sim:
    def __init__(self, day: Day, spec: dict, costs: dict):
        self.d = day
        self.m = day.mins.tolist()
        self.o, self.h, self.l, self.c = (a.tolist() for a in (day.o, day.h, day.l, day.c))
        self.v = day.v.tolist()
        self.sides = {"long": (1,), "short": (-1,), "both": (1, -1)}[spec["sides"]]
        self.win_from, self.win_to = (hm(x) for x in spec["entry_window"])
        self.flat = hm(spec["flat_by"])
        assert self.flat <= RTH_CLOSE, "flat_by after 16:00 not supported"
        self.max_trades = spec["max_trades_per_day"]
        self.max_stop = spec["max_stop_pts"]
        self.slip = costs["slippage_ticks"] * TICK
        self.comm = costs["commission_rt_usd"]
        before, after = spec["news_buffer_min"]
        self.blocks = sorted((e - before, e + after) for e in day.news)
        self.dead = day.news_all_day
        self.flat_i = self.idx(self.flat)
        self.trades: list[Trade] = []
        self.news_skipped = 0

    def idx(self, minute: int) -> int:
        """First bar starting at/after `minute`."""
        return bisect_left(self.m, minute)

    def blocked(self, minute: int) -> bool:
        return any(a <= minute < b for a, b in self.blocks)

    def in_window(self, i: int) -> bool:
        return i < self.flat_i and self.win_from <= self.m[i] < self.win_to

    def can_enter(self, i: int, side: int) -> bool:
        """Entry allowed on bar i? A news block also counts a skipped signal."""
        if (self.dead or i >= len(self.m) or len(self.trades) >= self.max_trades
                or side not in self.sides or not self.in_window(i)):
            return False
        if self.blocked(self.m[i]):
            self.news_skipped += 1
            return False
        return True

    def touched(self, i: int, side: int, kind: str, price: float) -> bool:
        """Would a pending entry order at `price` fill on bar i?"""
        if kind == "stop":
            return self.h[i] >= price if side > 0 else self.l[i] <= price
        return self.l[i] <= price - TICK if side > 0 else self.h[i] >= price + TICK

    def fill(self, i: int, side: int, kind: str, price: float | None = None) -> float:
        o = self.o[i]
        if kind == "market":
            return o + side * self.slip
        if kind == "stop":
            return (max(o, price) if side > 0 else min(o, price)) + side * self.slip
        return min(o, price) if side > 0 else max(o, price)

    def dist(self, level: dict, risk: float | None = None, ref: float | None = None) -> float:
        """Points for a non-structure LEVEL (r needs risk, range needs ref)."""
        t, v = level["type"], level["value"]
        pts = {"points": lambda: v, "ticks": lambda: v * TICK, "r": lambda: v * risk,
               "atr": lambda: v * self.d.atr, "range": lambda: v * ref}[t]()
        return max(tick(pts), TICK)

    def trade(self, i: int, side: int, kind: str, entry: float, stop: float,
              target: float) -> Trade | None:
        """Hold from bar i (entry fill bar) to exit. None = skipped (bad/too-wide stop)."""
        risk = (entry - stop) * side
        if risk <= 0 or (target - entry) * side <= 0:
            return None
        if self.max_stop is not None and risk > self.max_stop:
            return None
        n = len(self.m)
        force = self.flat
        reason_force = "flat"
        for a, _ in self.blocks:
            if self.m[i] < a < force:
                force, reason_force = a, "news"
        mfe = 0.0
        exit_px = reason = None
        j = i
        while j < n:
            o, hi, lo = self.o[j], self.h[j], self.l[j]
            if j > i:
                if self.m[j] >= force:
                    exit_px, reason = o - side * self.slip, reason_force
                    break
                if (o - stop) * side <= 0:                  # gapped through the stop
                    exit_px, reason = o - side * self.slip, "stop"
                    break
                if (o - target) * side >= TICK:             # gapped through the target
                    exit_px, reason = o, "target"
                    break
            mfe = max(mfe, (hi - entry) if side > 0 else (entry - lo))
            if (lo <= stop) if side > 0 else (hi >= stop):
                exit_px, reason = stop - side * self.slip, "stop"
                break
            if j > i or kind == "market":
                if (hi >= target + TICK) if side > 0 else (lo <= target - TICK):
                    exit_px, reason = target, "target"
                    break
            j += 1
        else:
            j = n - 1
            exit_px, reason = self.c[j] - side * self.slip, "eod"
        pnl_pts = (exit_px - entry) * side
        pnl_usd = pnl_pts * PT_USD - self.comm
        t = Trade(self.d.date, side, self.m[i], entry, stop, target, self.m[j], exit_px, reason,
                  round(pnl_pts, 4), round(pnl_usd, 2), risk, pnl_usd / (risk * PT_USD),
                  max(mfe, 0.0) / risk, j)
        self.trades.append(t)
        return t
