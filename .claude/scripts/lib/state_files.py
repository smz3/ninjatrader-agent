"""
Git-tracked source of truth for the shared tables (tasks, handovers).

state.db is a local, gitignored cache. What git actually tracks is one
small JSON file per record:
  .claude/state/tasks/<id>.json
  .claude/state/handovers/<id>.json
One file per record so git merges branches/worktrees record by record:
sessions touching different tasks never conflict, and handovers are
write-once so they never conflict at all. A real conflict (the same task
edited on both sides) shows up as a normal text conflict in one small file.

Flow:
  - Writes are file-first: CLI commands write the record's file, then open
    get_conn(), which re-imports. The db is never the only copy of a
    shared row.
  - get_conn() calls sync_from_files(), which re-imports whenever the
    files' signature (name/size/mtime) differs from the last import - so
    a git pull/merge/checkout or a fresh worktree/clone is picked up on
    the next db call, no git hooks to install.
  - If any file doesn't parse (e.g. unresolved conflict markers), the
    import is skipped and the db keeps its last good state.

IDs are random (t-3fa9c1 / h-07bd2e), not autoincrement, so two branches
adding records at the same time can't both claim the same id. Records
from before this existed keep their old integer ids as strings ("1").

Local-only, never exported: sessions, context_watch, meta, and
handovers_delivered (which handovers this checkout has already shown - so
a handover pulled from elsewhere still gets shown here once).
"""
import hashlib
import json
import re
import secrets
import sqlite3
from pathlib import Path

STATE_DIR = Path(__file__).resolve().parents[2] / "state"
TASKS_DIR = STATE_DIR / "tasks"
HANDOVERS_DIR = STATE_DIR / "handovers"

TASK_FIELDS = ("id", "status", "priority", "category", "task_title",
               "task_details", "created_ts", "updated_ts")
HANDOVER_FIELDS = ("id", "ts", "session_id", "summary", "next_steps", "questions")

_ID_RE = re.compile(r"^[A-Za-z0-9-]+$")


def new_id(prefix, directory):
    while True:
        rid = f"{prefix}-{secrets.token_hex(3)}"
        if not (directory / f"{rid}.json").exists():
            return rid


def _write(directory, fields, record, overwrite):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{record['id']}.json"
    if not overwrite and path.exists():
        return
    tmp = path.with_name(path.name + ".tmp")
    body = json.dumps({f: record.get(f) for f in fields}, indent=2, ensure_ascii=False)
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(body + "\n")
    tmp.replace(path)


def write_task(record, overwrite=True):
    _write(TASKS_DIR, TASK_FIELDS, record, overwrite)


def write_handover(record, overwrite=True):
    _write(HANDOVERS_DIR, HANDOVER_FIELDS, record, overwrite)


def read_task(task_id):
    """The task's record straight from its file (not the db), or None if
    there's no such task. Raises ValueError if the file doesn't parse."""
    if not _ID_RE.match(task_id):
        return None
    path = TASKS_DIR / f"{task_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _files():
    return sorted(p for d in (TASKS_DIR, HANDOVERS_DIR) if d.is_dir() for p in d.glob("*.json"))


def _signature(files):
    h = hashlib.sha1()
    for p in files:
        st = p.stat()
        h.update(f"{p.parent.name}/{p.name}:{st.st_size}:{st.st_mtime_ns}\n".encode())
    return h.hexdigest()


def _load(directory, fields, bad):
    rows = []
    for p in sorted(directory.glob("*.json")) if directory.is_dir() else []:
        try:
            rec = json.loads(p.read_text(encoding="utf-8"))
            if rec.get("id") != p.stem:
                raise ValueError("id field doesn't match filename")
            rows.append(tuple(rec.get(f) for f in fields))
        except (OSError, ValueError) as e:
            bad.append(f"{p.relative_to(STATE_DIR.parent)}: {e}")
    return rows


def _insert_sql(table, fields):
    return f"INSERT INTO {table} ({', '.join(fields)}) VALUES ({', '.join('?' * len(fields))})"


def sync_from_files(conn):
    """Rebuild the tasks/handovers tables from .claude/state/ if the files
    changed since the last import. No-op when nothing changed.

    Returns a list of problems (empty = fine). On any problem nothing is
    imported and the signature isn't stored, so the next call re-checks -
    the warning keeps coming back until the files are fixed."""
    files = _files()
    sig = _signature(files)
    row = conn.execute("SELECT value FROM meta WHERE key = 'files_sig'").fetchone()
    if row and row[0] == sig:
        return []

    bad = []
    tasks = _load(TASKS_DIR, TASK_FIELDS, bad)
    handovers = _load(HANDOVERS_DIR, HANDOVER_FIELDS, bad)
    if not bad:
        try:
            with conn:
                conn.execute("DELETE FROM tasks")
                conn.executemany(_insert_sql("tasks", TASK_FIELDS), tasks)
                conn.execute("DELETE FROM handovers")
                conn.executemany(_insert_sql("handovers", HANDOVER_FIELDS), handovers)
                conn.execute(
                    "INSERT OR REPLACE INTO meta (key, value) VALUES ('files_sig', ?)", (sig,)
                )
        except sqlite3.IntegrityError as e:
            bad.append(f"a record breaks a table constraint: {e}")
    return bad


def format_problems(bad):
    return (
        "[state] NOT importing .claude/state/ - the db is still on its last good "
        "import. Fix these first (unresolved merge conflict?):\n  " + "\n  ".join(bad)
    )
