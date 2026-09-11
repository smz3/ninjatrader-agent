"""CLI: python 1m backtests of registry strategies.

  python -m tools.backtest run orb vwap-snap         full grid, in-sample, recorded as runs
  python -m tools.backtest run all                   every strategy that has a setup file
  python -m tools.backtest run orb --base --dry      the strategy's own numbers only, not recorded
  python -m tools.backtest run orb --split out-of-sample --vary params.stop_at=middle
      out-of-sample = one final check of a picked combo: needs --vary or --base
  options: --eval-risk 800  --funded-risk 300  --sims 2000

Compare afterwards: python -m tools.registry runs --sort expectancy_r
"""
import argparse
import json

from . import runner
from .setups import SETUPS


def parse_vary(items: list[str]) -> dict:
    out = {}
    for it in items:
        k, _, v = it.partition("=")
        try:
            out[k] = json.loads(v)
        except json.JSONDecodeError:
            out[k] = v
    return out


def main():
    p = argparse.ArgumentParser(prog="python -m tools.backtest")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("ids", nargs="+", help="strategy ids, or 'all'")
    r.add_argument("--split", default="in-sample", choices=list(runner.SPLITS))
    r.add_argument("--base", action="store_true", help="skip the grid, test the strategy as is")
    r.add_argument("--vary", action="append", default=[], metavar="KEY=VALUE",
                   help="test one combo, e.g. spec.target.value=0.5 (repeatable)")
    r.add_argument("--dry", action="store_true", help="print only, don't record a run")
    r.add_argument("--eval-risk", type=float, default=800)
    r.add_argument("--funded-risk", type=float, default=300)
    r.add_argument("--sims", type=int, default=2000)
    a = p.parse_args()

    ids = list(SETUPS) if a.ids == ["all"] else a.ids
    varies = [parse_vary(a.vary)] if a.vary else ([{}] if a.base else None)
    if a.split == "out-of-sample" and varies is None:
        raise SystemExit("out-of-sample is a one-time check - pick the combo with --vary or --base")
    for sid in ids:
        runner.run(sid, a.split, varies, not a.dry, a.eval_risk, a.funded_risk, a.sims)


if __name__ == "__main__":
    main()
