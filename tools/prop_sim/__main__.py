"""CLI for the prop-firm evaluation simulator.

Single run:  python -m tools.prop_sim --wr 0.73 --rr 0.5 --risk 800
Grid:        python -m tools.prop_sim --grid --edge 0.1
  Grid rows = R:R, win rate solved so every row has the same edge
  (expectancy in R); columns = $ risk per trade.
"""
import argparse

from .engine import Firm, Strategy, run_many

GRID_RR = [0.5, 0.7, 1.0, 2.0, 3.0]
GRID_RISK = [150, 300, 500, 800, 1000]


def _firm(a) -> Firm:
    return Firm(target=a.target, max_dd=a.dd, dd_mode=a.dd_mode,
                consistency=a.consistency, daily_loss=a.daily_loss, max_days=a.days)


def _single(a):
    s = Strategy(a.wr, a.rr, a.risk, a.tpd, a.cost)
    r = run_many(_firm(a), s, a.n)
    print(f"WR {s.win_rate:.1%}  RR {s.rr}  risk ${s.risk:.0f}  "
          f"{s.trades_per_day}/day  cost ${s.cost:.0f}  edge {s.expectancy_r:+.2f}R")
    print(f"pass {r['pass_rate']:.1%}  blown {r['blown_rate']:.1%}  "
          f"timeout {r['timeout_rate']:.1%}  median days to pass {r['median_days']}")
    if a.fee and r["pass_rate"]:
        print(f"expected eval fees per pass: ${a.fee / r['pass_rate']:.0f}")


def _grid(a):
    firm = _firm(a)
    print(f"edge {a.edge:+.2f}R | dd ${a.dd:.0f} {a.dd_mode} | target ${a.target:.0f} | "
          f"consistency {a.consistency} | {a.tpd}/day | cost ${a.cost:.0f} | cells = pass %")
    print("RR    WR     " + "".join(f"${r:>6}" for r in GRID_RISK))
    for rr in GRID_RR:
        wr = (a.edge + 1) / (rr + 1)
        cells = [run_many(firm, Strategy(wr, rr, risk, a.tpd, a.cost), a.n)["pass_rate"]
                 for risk in GRID_RISK]
        print(f"{rr:<5} {wr:5.1%} " + "".join(f"{c:7.1%}" for c in cells))


def main():
    p = argparse.ArgumentParser(description="Prop-firm evaluation Monte Carlo")
    p.add_argument("--grid", action="store_true", help="same-edge R:R x risk table")
    p.add_argument("--edge", type=float, default=0.1, help="grid expectancy in R")
    p.add_argument("--wr", type=float, default=0.73)
    p.add_argument("--rr", type=float, default=0.5)
    p.add_argument("--risk", type=float, default=800)
    p.add_argument("--tpd", type=int, default=3, help="max trades per day")
    p.add_argument("--cost", type=float, default=0.0, help="$ commission+slippage per trade")
    p.add_argument("--target", type=float, default=3000)
    p.add_argument("--dd", type=float, default=2000)
    p.add_argument("--dd-mode", choices=["eod", "intraday", "static"], default="eod")
    p.add_argument("--consistency", type=float, default=None, help="e.g. 0.5 = best day <= 50%%")
    p.add_argument("--daily-loss", type=float, default=None)
    p.add_argument("--days", type=int, default=60, help="give up after N trading days")
    p.add_argument("--fee", type=float, default=0.0, help="$ per eval attempt")
    p.add_argument("--n", type=int, default=5000, help="simulations per config")
    a = p.parse_args()
    _grid(a) if a.grid else _single(a)


if __name__ == "__main__":
    main()
