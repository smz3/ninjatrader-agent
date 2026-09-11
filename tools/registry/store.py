"""Load / save / check registry records (registry/strategies, registry/runs).

Backtests record a test with new_run(); everything else goes through the CLI.
"""
import json
import os
import secrets
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from . import schema as S

ROOT = Path(__file__).resolve().parents[2]
DIRS = {"strategy": ROOT / "registry" / "strategies", "run": ROOT / "registry" / "runs"}
SCHEMAS = {"strategy": S.STRATEGY, "run": S.RUN}
RULES = {"strategy": S.strategy_rules, "run": S.run_rules}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def errors(kind: str, rec: dict) -> list[str]:
    return S.validate(rec, SCHEMAS[kind]) + RULES[kind](rec)


def load_all(kind: str) -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(DIRS[kind].glob("*.json"))]


def get(kind: str, rid: str) -> dict:
    p = DIRS[kind] / f"{rid}.json"
    if not p.exists():
        raise SystemExit(f"no {kind} {rid!r} in {p.parent.relative_to(ROOT)}")
    return json.loads(p.read_text(encoding="utf-8"))


def save(kind: str, rec: dict) -> dict:
    errs = errors(kind, rec)
    if errs:
        raise ValueError(f"{kind} {rec.get('id')}: " + "; ".join(errs))
    d = DIRS[kind]
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / f"{rec['id']}.json.tmp"
    tmp.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, d / f"{rec['id']}.json")
    return rec


def add_note(sid: str, text: str, status: str | None = None) -> dict:
    rec = get("strategy", sid)
    if status:
        rec["status"] = status
        text = f"-> {status}" + (f": {text}" if text else "")
    rec["notes"].append({"ts": now(), "text": text})
    rec["updated_ts"] = now()
    return save("strategy", rec)


def code_commit() -> str:
    git = lambda *a: subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    return git("rev-parse", "--short", "HEAD") + ("-dirty" if git("status", "--porcelain", "--", "tools") else "")


def new_run(strategy_id: str, engine: str, data: dict, costs: dict, rows: list[dict],
            trades_file: str | None = None, notes: str = "") -> dict:
    """Record one test. Snapshots the strategy's current version, spec, params, filters."""
    st = get("strategy", strategy_id)
    if st["status"] not in S.READY:
        raise ValueError(f"{strategy_id} is '{st['status']}' - pin its spec (status spec) before testing")
    rec = {
        "id": "r-" + secrets.token_hex(3), "strategy_id": strategy_id,
        "strategy_version": st["version"], "ts": now(), "engine": engine,
        "code_commit": code_commit(), "data": data, "costs": costs, "spec": st["spec"],
        "params": st["params"], "filters": st.get("filters", []), "rows": rows,
        "selected": None, "verdict": None, "trades_file": trades_file, "notes": notes,
    }
    return save("run", rec)


def check_all() -> list[str]:
    """Every file valid + runs consistent with their strategies."""
    errs, strategies, runs = [], {}, []
    for kind, d in DIRS.items():
        for p in sorted(d.glob("*.json")):
            try:
                rec = json.loads(p.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                errs.append(f"{p.name}: bad JSON ({e})")
                continue
            errs += [f"{p.name}: {e}" for e in errors(kind, rec)]
            if rec.get("id") != p.stem:
                errs.append(f"{p.name}: id {rec.get('id')!r} != file name")
            (runs.append(rec) if kind == "run" else strategies.__setitem__(rec.get("id"), rec))
    for sid, st in strategies.items():
        errs += [f"{sid}: filter {f!r} not found or not kind=filter" for f in st.get("filters", [])
                 if strategies.get(f, {}).get("kind") != "filter"]
    for r in runs:
        st = strategies.get(r.get("strategy_id"))
        if st is None:
            errs.append(f"{r.get('id')}: unknown strategy {r.get('strategy_id')!r}")
        elif r["strategy_version"] > st["version"]:
            errs.append(f"{r['id']}: version {r['strategy_version']} > strategy's {st['version']}")
        elif r["strategy_version"] == st["version"] and (r["spec"], r["params"]) != (st["spec"], st["params"]):
            errs.append(f"{st['id']}: spec/params changed since run {r['id']} but version is still "
                        f"{st['version']} - bump version")
    return errs
