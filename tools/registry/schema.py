"""Strategy registry schema - one universal shape for every setup and test.

Two record types, one git-tracked JSON file each (merge-friendly, same idea
as .claude/state):

  registry/strategies/<id>.json  what a setup IS: rules, numbers, status
  registry/runs/<id>.json        one test of one strategy version:
                                 conditions + results for every combo tried

Lifecycle (strategy.status):
  idea -> spec (every number pinned) -> tested (python backtest done)
  -> candidate (passes prop_sim) -> nt8 (NT8 backtest matches python trades)
  -> live.   Side exits: parked (waiting on data/work - never dropped),
  rejected (tested and failed - kept, with its runs as proof).

Rules:
- A setup can't be tested until its `spec` is complete (status spec+).
- Any change to rules or numbers = bump `version`. Runs pin the version and
  snapshot spec + params, so an old run always says exactly what it tested.
  `check` fails if a strategy changed after a run without a version bump.
- Runs are never deleted. Only `selected`, `verdict`, `notes` change later.
- Money = USD per 1 ES contract after costs ($50/pt, $12.50/tick).
  Times = ET (America/New_York).
"""
import re
from dataclasses import dataclass

STATUS = ("idea", "spec", "tested", "candidate", "nt8", "live", "parked", "rejected")
READY = ("spec", "tested", "candidate", "nt8", "live")  # spec must be complete
KIND = ("setup", "filter")
FAMILY = ("mean-reversion", "breakout", "trend", "any")
ENGINES = ("nautilus-1m", "python-1m","python-tick", "nt8-analyzer", "nt8-replay", "nt8-sim", "live")
SPLITS = ("in-sample", "out-of-sample", "full")
TIME = r"^([01]\d|2[0-3]):[0-5]\d$"
DATE = r"^\d{4}-\d{2}-\d{2}$"
NUM = (int, float)


@dataclass(frozen=True)
class F:
    type: object  # python type(s), or a dict = nested object schema
    doc: str = ""
    required: bool = True
    null: bool = False
    choices: tuple = ()
    pattern: str = ""
    items: "F | None" = None  # element rule for lists


LEVEL = {
    "type": F(str, "how the distance is measured (r = multiple of the stop distance, targets only)",
              choices=("points", "ticks", "atr", "range", "r", "structure")),
    "value": F(NUM, "size in that unit (6 points, 1.5 ATR, 0.5 of range, 0.5 R); null only for "
                    "structure", null=True),
    "note": F(str, "e.g. 'other side of range', 'beyond the poke extreme'", required=False),
}

SPEC = {
    "instrument": F(str, "contract traded", choices=("ES", "MES")),
    "bar": F(str, "data the rules run on", choices=("1m", "tick")),
    "sides": F(str, "directions allowed", choices=("long", "short", "both")),
    "entry_window": F(list, "[from, to] ET - no new entries outside it", items=F(str, pattern=TIME)),
    "flat_by": F(str, "ET - close all positions + cancel orders", pattern=TIME),
    "entry_order": F(str, "order type used to enter", choices=("market", "limit", "stop")),
    "stop": F(LEVEL, "initial stop"),
    "target": F(LEVEL, "profit target"),
    "max_stop_pts": F(NUM, "skip the trade if the stop is wider (risk must fit $300 funded / "
                           "$800-1,000 eval)", null=True),
    "max_trades_per_day": F(int, "hard cap per day"),
    "news_buffer_min": F(list, "[before, after] minutes flat around USD High news "
                               "(data/news/usd_high.csv)", items=F(int)),
}

STRATEGY = {
    "id": F(str, "slug, same as the file name", pattern=r"^[a-z0-9][a-z0-9-]*$"),
    "name": F(str, "human name"),
    "kind": F(str, "setup = trades on its own; filter = add-on that allows/blocks a setup's trades",
              choices=KIND),
    "family": F(str, "trade style", choices=FAMILY),
    "status": F(str, "lifecycle stage - see top of file", choices=STATUS),
    "version": F(int, "bump on ANY rule/number change; runs pin it"),
    "source": F(str, "where the idea came from (doc path, task id, book)"),
    "thesis": F(str, "why it should make money, 1-2 lines"),
    "rules": F(str, "entry / stop / target / exit in plain words"),
    "data_needed": F(list, "e.g. ohlcv-1m, ohlcv-1d, trades, mbp-10, news", items=F(str)),
    "spec": F(SPEC, "universal numbers every setup pins; null while idea/parked/rejected", null=True),
    "params": F(dict, "setup-specific numbers (free names); null value = not pinned yet"),
    "grid": F(dict, "sweep plan: 'spec.stop.value' / 'params.x' -> list of values to test",
              required=False),
    "filters": F(list, "ids of kind=filter strategies applied on top", items=F(str), required=False),
    "notes": F(list, "dated log", items=F({"ts": F(str, "UTC ISO"), "text": F(str)})),
    "created_ts": F(str, "UTC ISO"),
    "updated_ts": F(str, "UTC ISO"),
}

METRICS = {
    "trades": F(int, "closed trades"),
    "days": F(int, "trading days in the data window"),
    "trades_per_day": F(NUM, "trades / days"),
    "win_rate": F(NUM, "0-1, after costs (a scratch that loses the commission counts as a loss)"),
    "avg_win_usd": F(NUM, "per 1 ES, after costs"),
    "avg_loss_usd": F(NUM, "per 1 ES, after costs (negative)"),
    "rr": F(NUM, "avg_win / |avg_loss|"),
    "expectancy_usd": F(NUM, "average P/L per trade after costs - THE number"),
    "expectancy_r": F(NUM, "average P/L per trade in R (1 R = stop distance) after costs - what "
                           "risk-sized trading earns", required=False),
    "avg_risk_pts": F(NUM, "average stop distance in points", required=False),
    "profit_factor": F(NUM, "gross win / gross loss", null=True),
    "net_usd": F(NUM, "total P/L per 1 ES after costs"),
    "max_dd_usd": F(NUM, "worst peak-to-trough of closed-trade equity (positive)"),
    "worst_day_usd": F(NUM, "worst single day (negative) - compare with the $1,200 DLL"),
    "news_skipped": F(int, "signals blocked by the news filter", required=False),
}

PROP = {
    "risk_usd": F(NUM, "$ risk per trade in the eval sim"),
    "eval_pass_rate": F(NUM, "tools.prop_sim - 0-1"),
    "eval_median_days": F(NUM, "tools.prop_sim", null=True),
    "funded_risk_usd": F(NUM, "$ risk per trade in the funded sim", required=False),
    "funded_blown_rate": F(NUM, "tools.prop_sim.funded - 0-1"),
    "funded_got_paid_rate": F(NUM, "tools.prop_sim.funded - 0-1"),
    "funded_avg_paid_usd": F(NUM, "tools.prop_sim.funded"),
}

ROW = {
    "vary": F(dict, "what this combo changed vs the run's spec/params, keys 'spec.stop.value' / "
                    "'params.x'; {} for a single test"),
    "metrics": F(METRICS, "backtest results"),
    "prop": F(PROP, "prop_sim results (fill for the rows worth simulating)", required=False, null=True),
}

RUN = {
    "id": F(str, "r-xxxxxx, same as the file name", pattern=r"^r-[0-9a-f]{6}$"),
    "strategy_id": F(str, "which strategy"),
    "strategy_version": F(int, "which version of it"),
    "ts": F(str, "UTC ISO, when run"),
    "engine": F(str, "what produced the numbers", choices=ENGINES),
    "code_commit": F(str, "git sha of the backtester (+ '-dirty' if tools/ had uncommitted changes)"),
    "data": F({
        "source": F(str, "e.g. databento ES.v.0 ohlcv-1m"),
        "start": F(str, "YYYY-MM-DD", pattern=DATE),
        "end": F(str, "YYYY-MM-DD", pattern=DATE),
        "split": F(str, "in-sample = tuning; out-of-sample = one final check, never tune on it",
                   choices=SPLITS),
    }, "data window"),
    "costs": F({
        "commission_rt_usd": F(NUM, "round turn per contract (Lucid: ES 3.50, MES 1.00)"),
        "slippage_ticks": F(NUM, "per side"),
    }, "cost model"),
    "spec": F(SPEC, "snapshot of the strategy's spec at run time"),
    "params": F(dict, "snapshot of the strategy's params at run time"),
    "filters": F(list, "filter ids active in this run", items=F(str), required=False),
    "rows": F(list, "one per combo tested - ALL of them (the count matters for overfitting)",
              items=F(ROW)),
    "selected": F(int, "row index picked as best", required=False, null=True),
    "verdict": F(str, "decision after looking", choices=("keep", "tweak", "reject"),
                 required=False, null=True),
    "trades_file": F(str, "trade list path under data/ (gitignored)", required=False, null=True),
    "notes": F(str, "anything worth knowing", required=False),
}

NAMED = {id(LEVEL): "LEVEL", id(SPEC): "SPEC", id(METRICS): "METRICS", id(PROP): "PROP",
         id(ROW): "ROW"}


def validate(obj, schema: dict, path: str = "") -> list[str]:
    if not isinstance(obj, dict):
        return [f"{path or 'record'}: expected an object"]
    errs = [f"{path}{k}: unknown field" for k in obj if k not in schema]
    for k, f in schema.items():
        if k in obj:
            errs += _check(obj[k], f, f"{path}{k}")
        elif f.required:
            errs.append(f"{path}{k}: missing")
    return errs


def _check(v, f: F, where: str) -> list[str]:
    if v is None:
        return [] if f.null else [f"{where}: null not allowed"]
    if isinstance(f.type, dict):
        return validate(v, f.type, where + ".")
    if isinstance(v, bool) and f.type is not bool or not isinstance(v, f.type):
        return [f"{where}: expected {type_name(f.type)}, got {type(v).__name__}"]
    errs = []
    if f.choices and v not in f.choices:
        errs.append(f"{where}: {v!r} not one of {f.choices}")
    if f.pattern and not re.match(f.pattern, v):
        errs.append(f"{where}: {v!r} doesn't match {f.pattern}")
    if f.items is not None:
        for i, x in enumerate(v):
            errs += _check(x, f.items, f"{where}[{i}]")
    return errs


def spec_rules(sp: dict, where: str = "spec") -> list[str]:
    errs = []
    if len(sp.get("entry_window") or []) != 2:
        errs.append(f"{where}.entry_window: needs [from, to]")
    if len(sp.get("news_buffer_min") or []) != 2:
        errs.append(f"{where}.news_buffer_min: needs [before, after]")
    for k in ("stop", "target"):
        lv = sp.get(k) or {}
        if lv.get("value") is None and lv.get("type") != "structure":
            errs.append(f"{where}.{k}.value: needed unless type=structure")
    return errs


def strategy_rules(s: dict) -> list[str]:
    errs = []
    ready = s.get("status") in READY
    if s.get("spec") is not None:
        errs += spec_rules(s["spec"])
    elif ready and s.get("kind") == "setup":
        errs.append(f"status {s['status']} needs a complete spec")
    if ready:
        unpinned = [k for k, v in (s.get("params") or {}).items() if v is None]
        if unpinned:
            errs.append(f"status {s['status']} but params not pinned: {unpinned}")
    errs += [f"grid key {k!r} must start with 'spec.' or 'params.'"
             for k in (s.get("grid") or {}) if not k.startswith(("spec.", "params."))]
    return errs


def run_rules(r: dict) -> list[str]:
    errs = spec_rules(r.get("spec") or {})
    rows = r.get("rows") or []
    if not rows:
        errs.append("rows: empty")
    sel = r.get("selected")
    if sel is not None and not 0 <= sel < len(rows):
        errs.append(f"selected: {sel} out of range")
    for i, row in enumerate(rows):
        errs += [f"rows[{i}].vary: key {k!r} must start with 'spec.' or 'params.'"
                 for k in (row.get("vary") or {}) if not k.startswith(("spec.", "params."))]
    return errs


def type_name(t) -> str:
    if isinstance(t, dict):
        return NAMED.get(id(t), "object")
    if t == NUM:
        return "number"
    return t.__name__


def describe(schema: dict, indent: int = 0) -> list[str]:
    """Human-readable field list (python -m tools.registry schema)."""
    out = []
    for k, f in schema.items():
        t = type_name(f.type)
        if f.items is not None:
            t = f"list[{type_name(f.items.type)}]"
        flags = ("" if f.required else " optional") + (" nullable" if f.null else "")
        choices = f" {'|'.join(f.choices)}" if f.choices else ""
        out.append(f"{' ' * indent}{k:<22} {t}{flags}{choices}  - {f.doc}")
        for sub in (f.type, f.items.type if f.items else None):
            if isinstance(sub, dict) and id(sub) not in NAMED:
                out += describe(sub, indent + 4)
    return out
