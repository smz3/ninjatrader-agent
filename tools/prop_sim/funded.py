"""Simulate the funded (payout) stage of a prop account.

Compares Lucid-style payout rules: how much you actually withdraw and how often
the account blows before you're moved live. Trades are binary like engine.py.

Intraday drawdown trails open-profit peaks. Binary trades: winners are assumed
to close at their target (open peak = the win), but a loser may first run into
profit before stopping out: its open peak is a random 0..`loser_mfe` share of
a win. Empirical trades (engine.Empirical) carry their real peaks.

Run:  python -m tools.prop_sim.funded --wr 0.733 --rr 0.5 --risk 300
"""
from dataclasses import dataclass, field
import argparse
import random
import statistics

from .engine import Empirical, Strategy


@dataclass
class Payout:
    buffer: float = 2_100               # profit above start that's never withdrawable
    min_request: float = 500
    caps: tuple = ()                    # per-payout caps; last repeats; () = no cap
    share: float | None = None          # max share of cycle profit per payout (Flex 0.5)
    min_days: int = 1                   # trading days per cycle
    min_cycle_profit: float = 1         # net profit needed since last payout
    min_win_days: int = 0               # days per cycle at >= win_day_min profit
    win_day_min: float = 0
    consistency: float | None = None    # best cycle day <= this share of cycle profit
    max_payouts: int | None = None      # then moved live (sim stops)


@dataclass
class Funded:
    dd_mode: str = "eod"                # "eod" | "intraday"
    payout: Payout = field(default_factory=Payout)
    start: float = 50_000
    max_dd: float = 2_000               # MLL locks at start + 100


PLANS = {
    "flex": Funded("eod", Payout(buffer=0, share=0.5, caps=(2_000,), min_win_days=5,
                                 win_day_min=150, max_payouts=5)),
    "pro": Funded("eod", Payout(caps=(2_000, 2_500), min_days=3, min_cycle_profit=500,
                                consistency=0.4, max_payouts=5)),
    "daily": Funded("intraday", Payout()),
}


def run_one(acct: Funded, strat: "Strategy | Empirical", rng: random.Random, days: int,
            loser_mfe: float) -> tuple[str, float, int, int | None]:
    """Return (outcome, $ withdrawn gross, payouts, day of first payout)."""
    p = acct.payout
    intraday = acct.dd_mode == "intraday"
    lock = acct.start + 100
    bal = peak = acct.start
    mll = acct.start - acct.max_dd
    paid, n_paid, first = 0.0, 0, None
    cycle_start, cycle_days, best_day, win_days = bal, 0, 0.0, 0

    def trail(level: float):
        nonlocal peak, mll
        if level > peak:
            peak = level
            mll = max(mll, min(peak - acct.max_dd, lock))

    for day in range(1, days + 1):
        day_start = bal
        for pnl, peak in strat.day(rng, loser_mfe if intraday else None):
            if intraday:
                trail(bal + max(peak, pnl))
            bal += pnl
            if bal <= mll:
                return "blown", paid, n_paid, first
        if acct.dd_mode == "eod":
            trail(bal)

        day_pnl = bal - day_start
        cycle_days += 1
        best_day = max(best_day, day_pnl)
        win_days += p.min_win_days > 0 and day_pnl >= p.win_day_min
        cycle_profit = bal - cycle_start
        if (cycle_days < p.min_days or cycle_profit < p.min_cycle_profit
                or win_days < p.min_win_days
                or (p.consistency is not None and best_day > p.consistency * cycle_profit)):
            continue

        amt = bal - (acct.start + p.buffer)
        if p.share is not None:
            amt = min(amt, p.share * cycle_profit)
        if p.caps:
            amt = min(amt, p.caps[min(n_paid, len(p.caps) - 1)])
        if amt < p.min_request:
            continue
        bal -= amt
        paid += amt
        n_paid += 1
        first = first or day
        cycle_start, cycle_days, best_day, win_days = bal, 0, 0.0, 0
        if p.max_payouts and n_paid >= p.max_payouts:
            return "live", paid, n_paid, first

    return "running", paid, n_paid, first


def run_many(acct: Funded, strat: "Strategy | Empirical", days: int = 120, loser_mfe: float = 0.0,
             n: int = 5000, seed: int = 1) -> dict:
    rng = random.Random(seed)
    outs = [run_one(acct, strat, rng, days, loser_mfe) for _ in range(n)]
    firsts = [o[3] for o in outs if o[3] is not None]
    return {
        "blown": sum(o[0] == "blown" for o in outs) / n,
        "live": sum(o[0] == "live" for o in outs) / n,
        "avg_paid": statistics.mean(o[1] for o in outs),
        "avg_payouts": statistics.mean(o[2] for o in outs),
        "got_paid": len(firsts) / n,
        "median_first_day": statistics.median(firsts) if firsts else None,
    }


def main():
    a = argparse.ArgumentParser(description="Funded-stage payout Monte Carlo")
    a.add_argument("--wr", type=float, default=0.733)
    a.add_argument("--rr", type=float, default=0.5)
    a.add_argument("--risk", type=float, default=300)
    a.add_argument("--tpd", type=int, default=3)
    a.add_argument("--cost", type=float, default=0.0)
    a.add_argument("--days", type=int, default=120, help="trading days to simulate")
    a.add_argument("--mfe", type=float, default=0.8,
                   help="losers' max open profit as share of a win (intraday only)")
    a.add_argument("--n", type=int, default=5000)
    a = a.parse_args()
    s = Strategy(a.wr, a.rr, a.risk, a.tpd, a.cost)
    print(f"WR {s.win_rate:.1%}  RR {s.rr}  risk ${s.risk:.0f}  {s.trades_per_day}/day  "
          f"cost ${s.cost:.0f}  {a.days} trading days  (payouts gross, before 90/10)")
    print(f"{'plan':<22}{'blown':>7}{'live':>7}{'paid any':>10}{'1st pay day':>13}"
          f"{'payouts':>9}{'avg $ out':>11}")
    rows = [(k, v, a.mfe) for k, v in PLANS.items()] + [("daily (no loser spikes)",
                                                         PLANS["daily"], 0.0)]
    for name, acct, mfe in rows:
        r = run_many(acct, s, a.days, mfe, a.n)
        print(f"{name:<22}{r['blown']:7.1%}{r['live']:7.1%}{r['got_paid']:10.1%}"
              f"{str(r['median_first_day']):>13}{r['avg_payouts']:9.1f}{r['avg_paid']:11,.0f}")


if __name__ == "__main__":
    main()
