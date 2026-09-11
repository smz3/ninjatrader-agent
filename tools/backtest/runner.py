"""Run a strategy's grid on one data split and record it in the registry.

Every combo tested is recorded (the count matters for overfitting). Splits:
in-sample = tuning; out-of-sample = one final check of a picked combo, never
tuned on. Trade lists go to data/backtests/<run id>.parquet (gitignored).
"""
import copy
import itertools

import pandas as pd

from tools.registry import store

from . import data, metrics, prop
from .setups import SETUPS
from .sim import Sim

SPLITS = {"in-sample": ("2016-09-01", "2024-12-31"),
          "out-of-sample": ("2025-01-01", "2099-12-31"),
          "full": ("2016-09-01", "2099-12-31")}
COSTS = {"commission_rt_usd": 3.50, "slippage_ticks": 1}
MIN_TRADES_FOR_PROP = 30
TRADES_DIR = data.ROOT / "data" / "backtests"


def combos(grid: dict) -> list[dict]:
    keys = list(grid)
    return [dict(zip(keys, vals)) for vals in itertools.product(*grid.values())]


def apply(st: dict, vary: dict) -> tuple[dict, dict]:
    """Strategy spec/params with dotted overrides ('spec.stop.value', 'params.x')."""
    spec, params = copy.deepcopy(st["spec"]), copy.deepcopy(st["params"])
    for key, val in vary.items():
        root, *path = key.split(".")
        obj = spec if root == "spec" else params
        for k in path[:-1]:
            obj = obj[k]
        if path[-1] not in obj:
            raise KeyError(f"{key}: no such field in {st['id']}")
        obj[path[-1]] = val
    return spec, params


def backtest(sid: str, days: list, spec: dict, params: dict, costs: dict = COSTS):
    """(trades, news_skipped, per-day [(r, peak_r), ...] incl. empty days)."""
    fn = SETUPS[sid]
    trades, skipped, per_day = [], 0, []
    for d in days:
        sim = Sim(d, spec, costs)
        if not sim.dead:
            fn(d, sim, params, spec)
        trades += sim.trades
        skipped += sim.news_skipped
        per_day.append([(t.r, t.peak_r) for t in sim.trades])
    return trades, skipped, per_day


def fmt(k: int, vary: dict, m: dict, pr: dict | None) -> str:
    v = ", ".join(f"{key.split('.', 1)[1]}={val}" for key, val in vary.items()) or "(base)"
    pf = f"{m['profit_factor']:.2f}" if m["profit_factor"] is not None else "-"
    line = (f"{k:>3} {v:<58} n={m['trades']:<5} tpd={m['trades_per_day']:.2f} "
            f"wr={m['win_rate']:.1%} rr={m['rr']:.2f} exp=${m['expectancy_usd']:>7.2f} "
            f"expR={m['expectancy_r']:+.3f} pf={pf} dd=${m['max_dd_usd']:,.0f}")
    if pr:
        line += (f" | pass {pr['eval_pass_rate']:.0%} blown {pr['funded_blown_rate']:.0%} "
                 f"paid ${pr['funded_avg_paid_usd']:,.0f}")
    return line


def run(sid: str, split: str = "in-sample", varies: list[dict] | None = None, record: bool = True,
        eval_risk: float = 800, funded_risk: float = 300, sims: int = 2000, log=print,
        engine: str = "nautilus-1m"):
    """Test every combo in `varies` (default: the strategy's full grid)."""
    st = store.get("strategy", sid)
    if sid not in SETUPS:
        raise SystemExit(f"{sid}: no setup file in tools/backtest/setups")
    if st["status"] not in ("spec", "tested", "candidate", "nt8", "live"):
        raise SystemExit(f"{sid} is '{st['status']}' - pin its spec first")
    days = data.window(*SPLITS[split])
    varies = varies if varies is not None else (combos(st.get("grid") or {}) or [{}])
    log(f"== {sid} v{st['version']} | {split} {days[0].date} -> {days[-1].date} "
        f"({len(days)} days) | {len(varies)} combos")
    if engine == "nautilus-1m":
        from .nautilus import COSTS as costs, Engine
        eng = Engine(sid, days, max(data.hm(apply(st, v)[0]["flat_by"]) for v in varies))
        bt = eng.backtest
        how = "NautilusTrader defaults (no slippage, touch fills, O-H-L-C bar path), no message queue"
    else:
        costs, bt = COSTS, lambda spec, params: backtest(sid, days, spec, params)
        how = "tools/backtest sim.py: stop-first, limits need 1-tick trade-through"
    rows, frames = [], []
    for k, vary in enumerate(varies):
        spec, params = apply(st, vary)
        trades, skipped, per_day = bt(spec, params)
        m = metrics.compute(trades, len(days), skipped)
        pr = (prop.simulate(per_day, eval_risk, funded_risk, sims)
              if m["trades"] >= MIN_TRADES_FOR_PROP and m["expectancy_r"] > 0 else None)
        rows.append({"vary": vary, "metrics": m, "prop": pr})
        log(fmt(k, vary, m, pr))
        if trades:
            frames.append(pd.DataFrame([vars(t) for t in trades]).drop(columns="exit_i").assign(row=k))
    if not record:
        return rows, None
    rec = store.new_run(
        sid, engine,
        {"source": data.SOURCE, "start": days[0].date, "end": days[-1].date, "split": split},
        costs, rows,
        notes=(f"1m bars, {how}. prop = "
               f"LucidDaily eval (risk ${eval_risk:.0f}) + funded daily {prop.FUNDED_DAYS}d "
               f"(risk ${funded_risk:.0f}), {sims} sims on resampled real days; only rows with "
               f">= {MIN_TRADES_FOR_PROP} trades and expectancy_r > 0."))
    if frames:
        TRADES_DIR.mkdir(parents=True, exist_ok=True)
        path = TRADES_DIR / f"{rec['id']}.parquet"
        pd.concat(frames, ignore_index=True).to_parquet(path)
        rec["trades_file"] = path.relative_to(data.ROOT).as_posix()
        store.save("run", rec)
    if st["status"] == "spec":
        store.add_note(sid, f"run {rec['id']} ({split}, {len(rows)} combos)", status="tested")
    log(f"recorded {rec['id']}")
    return rows, rec
