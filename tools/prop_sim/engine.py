"""Simulate one or many prop-firm evaluations.

Trades are binary: a win adds risk * rr, a loss subtracts risk, and every
trade pays `cost` (commission + slippage). Drawdown is checked after every
closed trade, so intraday-trailing results are optimistic (real firms trail
open-profit peaks too).
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


def _trail(firm: Firm, hwm: float, threshold: float) -> float:
    new = hwm - firm.max_dd
    if firm.lock_at_start:
        new = min(new, firm.start)
    return max(threshold, new)


def run_one(firm: Firm, strat: Strategy, rng: random.Random) -> tuple[str, int]:
    """Return (outcome, day) where outcome is "pass" | "blown" | "timeout"."""
    bal = hwm = firm.start
    threshold = firm.start - firm.max_dd
    best_day = 0.0
    win_amt = strat.risk * strat.rr - strat.cost
    loss_amt = strat.risk + strat.cost

    for day in range(1, firm.max_days + 1):
        day_start = bal
        for _ in range(strat.trades_per_day):
            bal += win_amt if rng.random() < strat.win_rate else -loss_amt

            if firm.dd_mode == "intraday" and bal > hwm:
                hwm = bal
                threshold = _trail(firm, hwm, threshold)
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


def run_many(firm: Firm, strat: Strategy, n: int = 5000, seed: int = 1) -> dict:
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
