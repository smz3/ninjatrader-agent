"""CLI: the strategy registry - one table for every setup and every test.

  python -m tools.registry list                  every strategy: status, runs, best result
  python -m tools.registry runs [--strategy ID] [--split in-sample] [--sort expectancy_usd]
  python -m tools.registry show ID               one strategy + its runs
  python -m tools.registry status ID STATUS [--note "..."]
  python -m tools.registry note ID "text"
  python -m tools.registry check                 validate every file (run before commit)
  python -m tools.registry schema                every field + what it means

Records live in registry/strategies/<id>.json and registry/runs/<id>.json
(git-tracked). Backtests record results with tools.registry.store.new_run().
"""
import argparse
import json

import pandas as pd

from . import schema as S
from . import store

pd.options.display.width = 250
pd.options.display.max_columns = None
pd.options.display.max_colwidth = 60
METRIC_COLS = ("trades", "trades_per_day", "win_rate", "rr", "expectancy_usd", "expectancy_r",
               "profit_factor", "max_dd_usd", "worst_day_usd")


def rows_table(runs: list[dict]) -> pd.DataFrame:
    """One line per combo tested, across runs."""
    out = []
    for r in runs:
        for i, row in enumerate(r["rows"]):
            m, p = row["metrics"], row.get("prop") or {}
            out.append({
                "run": r["id"], "row": i, "pick": "*" if r.get("selected") == i else "",
                "strategy": r["strategy_id"], "v": r["strategy_version"], "engine": r["engine"],
                "split": r["data"]["split"], "verdict": r.get("verdict") or "",
                "vary": ", ".join(f"{k.split('.', 1)[1]}={v}" for k, v in row["vary"].items()),
                **{k: m.get(k) for k in METRIC_COLS},
                "pass": p.get("eval_pass_rate"), "blown": p.get("funded_blown_rate"),
            })
    return pd.DataFrame(out, columns=["run", "row", "pick", "strategy", "v", "engine", "split",
                                      "verdict", "vary", *METRIC_COLS, "pass", "blown"])


def cmd_list(a):
    t = rows_table(store.load_all("run"))
    rows = []
    for s in store.load_all("strategy"):
        mine = t[t.strategy == s["id"]]
        rows.append({
            "id": s["id"], "name": s["name"], "kind": s["kind"], "family": s["family"],
            "status": s["status"], "v": s["version"], "runs": mine.run.nunique(),
            "best_exp_usd": mine.expectancy_usd.max(), "best_pass": mine["pass"].max(),
            "data_needed": ", ".join(s["data_needed"]),
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return print("no strategies yet")
    df = df.sort_values("status", key=lambda c: c.map(S.STATUS.index), kind="stable")
    print(df.to_string(index=False, na_rep="-"))


def cmd_runs(a):
    t = rows_table(store.load_all("run"))
    if a.strategy:
        t = t[t.strategy == a.strategy]
    if a.split:
        t = t[t.split == a.split]
    if t.empty:
        return print("no runs yet")
    print(t.sort_values(a.sort, ascending=False).to_string(index=False, na_rep="-"))


def cmd_show(a):
    print(json.dumps(store.get("strategy", a.id), indent=2))
    a.strategy, a.split, a.sort = a.id, None, "expectancy_usd"
    cmd_runs(a)


def cmd_status(a):
    s = store.add_note(a.id, a.note, status=a.status)
    print(f"{s['id']}: {s['status']} (v{s['version']})")


def cmd_note(a):
    store.add_note(a.id, a.text)
    print(f"{a.id}: note added")


def cmd_check(a):
    errs = store.check_all()
    for e in errs:
        print(e)
    n = {k: len(list(d.glob("*.json"))) for k, d in store.DIRS.items()}
    print(f"{'FAIL' if errs else 'ok'}: {n['strategy']} strategies, {n['run']} runs, {len(errs)} errors")
    raise SystemExit(1 if errs else 0)


def cmd_schema(a):
    for name, sch in (("STRATEGY  registry/strategies/<id>.json", S.STRATEGY),
                      ("SPEC  universal numbers every setup pins", S.SPEC),
                      ("LEVEL  stop / target", S.LEVEL),
                      ("RUN  registry/runs/<id>.json", S.RUN),
                      ("ROW  one combo tested", S.ROW),
                      ("METRICS  per 1 ES, after costs", S.METRICS),
                      ("PROP  prop_sim results", S.PROP)):
        print(f"\n== {name}")
        print("\n".join(S.describe(sch)))
    print(f"\nstatus order: {' -> '.join(('idea',) + S.READY)}; side exits: parked, rejected")


def main():
    p = argparse.ArgumentParser(prog="python -m tools.registry")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list").set_defaults(fn=cmd_list)
    r = sub.add_parser("runs")
    r.add_argument("--strategy")
    r.add_argument("--split", choices=S.SPLITS)
    r.add_argument("--sort", default="expectancy_usd", choices=METRIC_COLS)
    r.set_defaults(fn=cmd_runs)
    s = sub.add_parser("show")
    s.add_argument("id")
    s.set_defaults(fn=cmd_show)
    s = sub.add_parser("status")
    s.add_argument("id")
    s.add_argument("status", choices=S.STATUS)
    s.add_argument("--note", default="")
    s.set_defaults(fn=cmd_status)
    s = sub.add_parser("note")
    s.add_argument("id")
    s.add_argument("text")
    s.set_defaults(fn=cmd_note)
    sub.add_parser("check").set_defaults(fn=cmd_check)
    sub.add_parser("schema").set_defaults(fn=cmd_schema)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
