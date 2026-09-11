"""
Mirror of the strategy registry (repo-root registry/*.json) into state.db,
so it can be browsed in a SQLite viewer next to tasks.

The JSON files stay the source of truth (git-tracked, written and validated
by tools/registry - `python -m tools.registry check`). These tables are a
read-only cache: dropped and rebuilt by get_conn() whenever the registry
files change. Never write to them directly - changes would be lost.

Table: strategies(id, name, kind, family, status, version, source, thesis,
                  rules, data_needed, filters, params, grid, spec, notes,
                  created_ts, updated_ts)
  One row per setup idea. params/grid/spec/notes are JSON text.
Table: runs(id, strategy_id, strategy_version, ts, engine, code_commit,
            data_source, data_start, data_end, split, commission_rt_usd,
            slippage_ticks, filters, spec, params, rows_tested, selected,
            verdict, trades_file, notes)
  One row per test.
Table: run_rows(run_id, row_idx, strategy_id, strategy_version, split,
                selected, vary, <every metric>, <every prop_sim result>)
  One row per parameter combo tested - the table to sort and compare on.

A bad registry file skips only this mirror (tasks/handovers still import)
and warns on every db call until fixed; the tables keep the last good copy.
"""
import hashlib
import json
from pathlib import Path

REGISTRY = Path(__file__).resolve().parents[3] / "registry"

METRICS = {"trades": "INTEGER", "days": "INTEGER", "trades_per_day": "REAL", "win_rate": "REAL",
           "avg_win_usd": "REAL", "avg_loss_usd": "REAL", "rr": "REAL", "expectancy_usd": "REAL",
           "expectancy_r": "REAL", "avg_risk_pts": "REAL", "profit_factor": "REAL",
           "net_usd": "REAL", "max_dd_usd": "REAL", "worst_day_usd": "REAL",
           "news_skipped": "INTEGER"}
PROP = {"risk_usd": "REAL", "eval_pass_rate": "REAL", "eval_median_days": "REAL",
        "funded_risk_usd": "REAL", "funded_blown_rate": "REAL", "funded_got_paid_rate": "REAL",
        "funded_avg_paid_usd": "REAL"}
TABLES = {
    "strategies": {"id": "TEXT PRIMARY KEY", "name": "TEXT", "kind": "TEXT", "family": "TEXT",
                   "status": "TEXT", "version": "INTEGER", "source": "TEXT", "thesis": "TEXT",
                   "rules": "TEXT", "data_needed": "TEXT", "filters": "TEXT", "params": "TEXT",
                   "grid": "TEXT", "spec": "TEXT", "notes": "TEXT", "created_ts": "TEXT",
                   "updated_ts": "TEXT"},
    "runs": {"id": "TEXT PRIMARY KEY", "strategy_id": "TEXT", "strategy_version": "INTEGER",
             "ts": "TEXT", "engine": "TEXT", "code_commit": "TEXT", "data_source": "TEXT",
             "data_start": "TEXT", "data_end": "TEXT", "split": "TEXT",
             "commission_rt_usd": "REAL", "slippage_ticks": "REAL", "filters": "TEXT",
             "spec": "TEXT", "params": "TEXT", "rows_tested": "INTEGER", "selected": "INTEGER",
             "verdict": "TEXT", "trades_file": "TEXT", "notes": "TEXT"},
    "run_rows": {"run_id": "TEXT", "row_idx": "INTEGER", "strategy_id": "TEXT",
                 "strategy_version": "INTEGER", "split": "TEXT", "selected": "INTEGER",
                 "vary": "TEXT", **METRICS, **PROP},
}


def _cell(v):
    if isinstance(v, list) and all(isinstance(x, str) for x in v):
        return ", ".join(v)
    return json.dumps(v) if isinstance(v, (list, dict)) else v


def _records(p, rec):
    """(table, row-dict) pairs for one registry file."""
    if p.parent.name == "strategies":
        return [("strategies", rec)]
    d, c, rows = rec.get("data") or {}, rec.get("costs") or {}, rec.get("rows") or []
    out = [("runs", {**rec, "data_source": d.get("source"), "data_start": d.get("start"),
                     "data_end": d.get("end"), "split": d.get("split"),
                     "commission_rt_usd": c.get("commission_rt_usd"),
                     "slippage_ticks": c.get("slippage_ticks"), "rows_tested": len(rows)})]
    for i, row in enumerate(rows):
        out.append(("run_rows", {
            "run_id": rec["id"], "row_idx": i, "strategy_id": rec.get("strategy_id"),
            "strategy_version": rec.get("strategy_version"), "split": d.get("split"),
            "selected": int(rec.get("selected") == i), "vary": row.get("vary") or {},
            **(row.get("metrics") or {}), **(row.get("prop") or {}),
        }))
    return out


def sync_registry(conn):
    """Rebuild strategies/runs/run_rows if the registry files changed since
    the last import. Returns a list of problems (empty = fine)."""
    files = sorted(p for sub in ("strategies", "runs") if (REGISTRY / sub).is_dir()
                   for p in (REGISTRY / sub).glob("*.json"))
    h = hashlib.sha1()
    for p in files:
        st = p.stat()
        h.update(f"{p.parent.name}/{p.name}:{st.st_size}:{st.st_mtime_ns}\n".encode())
    sig = h.hexdigest()
    have = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    row = conn.execute("SELECT value FROM meta WHERE key = 'registry_sig'").fetchone()
    if row and row[0] == sig and set(TABLES) <= have:
        return []

    bad, data = [], {t: [] for t in TABLES}
    for p in files:
        try:
            rec = json.loads(p.read_text(encoding="utf-8"))
            if rec.get("id") != p.stem:
                raise ValueError("id field doesn't match filename")
            for table, r in _records(p, rec):
                data[table].append(tuple(_cell(r.get(col)) for col in TABLES[table]))
        except (OSError, ValueError, AttributeError, TypeError) as e:
            bad.append(f"registry/{p.parent.name}/{p.name}: {e}")
    if bad:
        return bad
    with conn:
        for table, cols in TABLES.items():
            conn.execute(f"DROP TABLE IF EXISTS {table}")
            conn.execute(f"CREATE TABLE {table} ({', '.join(f'{c} {t}' for c, t in cols.items())})")
            conn.executemany(f"INSERT INTO {table} VALUES ({', '.join('?' * len(cols))})", data[table])
        conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('registry_sig', ?)", (sig,))
    return []
