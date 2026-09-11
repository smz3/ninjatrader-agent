"""Simulate one or many prop-firm evaluations.

Two trade models, both handing the sim one day at a time as (P/L $, open
peak $) per trade:
- Strategy: binary - a win adds risk * rr, a loss subtracts risk, and every
  trade pays `cost` (commission + slippage).
- Empirical: real backtest days (tools/backtest), resampled whole - so the
  real trade count per day (incl. no-trade days), real R per trade and real
  open-profit peaks carry over. R x risk assumes exact risk sizing.
Eval drawdown is checked after every closed trade, so intraday-trailing eval
results are optimistic for binary trades (their losers have no open peak).
"""
from dataclasses import dataclass
import random
import statistics


@dataclass
class Firm:
    start: float = 50_000
    target: float = 3_000
    max_dd: float = 2_000
    dd_mode: str = "eod"                # "eod" | "intraday" | "static"
    lock_at_start: bool = True          # trailing threshold stops at start balance
    consistency: float | None = None    # best day must be <= this share of total profit
    daily_loss: float | None = None     # stop for the day once down this much
    max_days: int = 60


@dataclass
class Strategy:
    win_rate: float
    rr: float
    risk: float                         # $ lost on a losing trade
    trades_per_day: int = 3
    cost: float = 0.0                   # $ per trade

    @property
    def expectancy_r(self) -> float:
        return self.win_rate * self.rr - (1 - self.win_rate)

    def day(self, rng: random.Random, loser_mfe: float | None = None):
        """Yield (P/L $, open peak $) per trade, lazily (a stopped day draws no more).
        Losers' peak = random 0..loser_mfe share of a win; None = no peak drawn."""
        win = self.risk * self.rr - self.cost
        loss = self.risk + self.cost
        for _ in range(self.trades_per_day):
            if rng.random() < self.win_rate:
                yield win, win
            else:
                yield -loss, (rng.uniform(0, loser_mfe) * win if loser_mfe is not None else 0.0)


@dataclass
class Empirical:
    """Resample real backtest days. days = one list per trading day (empty = no
    trade) of (P/L in R, open peak in R) per trade, costs already inside."""
    days: list
    risk: float

    def day(self, rng: random.Random, loser_mfe: float | None = None):
        for r, peak in self.days[rng.randrange(len(self.days))]:
            yield r * self.risk, peak * self.risk


def _trail(firm: Firm, hwm: float, threshold: float) -> float:
    new = hwm - firm.max_dd
    if firm.lock_at_start:
        new = min(new, firm.start)
    return max(threshold, new)


def run_one(firm: Firm, strat: "Strategy | Empirical", rng: random.Random) -> tuple[str, int]:
    """Return (outcome, day) where outcome is "pass" | "blown" | "timeout"."""
    bal = hwm = firm.start
    threshold = firm.start - firm.max_dd
    best_day = 0.0

    for day in range(1, firm.max_days + 1):
        day_start = bal
        for pnl, peak in strat.day(rng):
            if firm.dd_mode == "intraday" and bal + peak > hwm:
                hwm = bal + peak
                threshold = _trail(firm, hwm, threshold)
            bal += pnl
            if bal <= threshold:
                return "blown", day

            profit = bal - firm.start
            if profit >= firm.target:
                best = max(best_day, bal - day_start)
                if firm.consistency is None or best <= firm.consistency * profit:
                    return "pass", day
                break  # target hit but day too big: stop so it doesn't grow
            if firm.daily_loss is not None and day_start - bal >= firm.daily_loss:
                break

        best_day = max(best_day, bal - day_start)
        if firm.dd_mode == "eod" and bal > hwm:
            hwm = bal
            threshold = _trail(firm, hwm, threshold)

    return "timeout", firm.max_days


def run_many(firm: Firm, strat: "Strategy | Empirical", n: int = 5000, seed: int = 1) -> dict:
    rng = random.Random(seed)
    counts = {"pass": 0, "blown": 0, "timeout": 0}
    pass_days = []
    for _ in range(n):
        outcome, day = run_one(firm, strat, rng)
        counts[outcome] += 1
        if outcome == "pass":
            pass_days.append(day)
    return {
        "pass_rate": counts["pass"] / n,
        "blown_rate": counts["blown"] / n,
        "timeout_rate": counts["timeout"] / n,
        "median_days": statistics.median(pass_days) if pass_days else None,
    }
