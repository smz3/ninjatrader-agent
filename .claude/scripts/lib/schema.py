"""
Schema + connection for state.db (SQLite, local gitignored cache). Stdlib
only, no deps. Shared by every hooks/cli module - nothing here depends on
them.

Where things live (schema v2, since 2026-09-10):
  Shared, git-tracked: tasks + handovers, as one JSON file per record under
    .claude/state/ - see lib/state_files.py. state.db holds a copy that
    get_conn() re-imports whenever those files change. Deleting state.db
    loses nothing shared: the next db call rebuilds it from the files.
  Local-only, never leave this checkout: sessions, context_watch,
    handovers_delivered, meta.
  state.db itself used to be git-tracked, but git can't merge a binary
  file, every worktree got its own diverging copy, and autoincrement ids
  collided across branches.

Table: handovers(id, ts, session_id, summary, next_steps, questions)
  Plain columns, no JSON - written ONLY on-command (the `log` subcommand,
  normally via the /handover skill), never automatically. A session that
  ends without the user saying "handover" leaves no row here - that's
  deliberate, not a bug (see cmd_stop_check in hooks/sessions.py). One row
  per log call, not one per session - a session can log more than once.
  id is random ('h-07bd2e'). Write-once, never edited, never pruned.
Table: handovers_delivered(handover_id, ts)
  Which handovers SessionStart has already shown in THIS checkout. Kept out
  of the handover files on purpose: a handover pulled in from another
  branch/worktree still gets shown here once. SessionStart surfaces the
  latest undelivered handover from up to HANDOVER_SHOW_COUNT distinct
  sessions, most recent first, then marks those and everything older
  delivered (see recent_handovers in lib/handovers.py) - so a handover is
  replayed to the next session once and never again, instead of re-showing
  the same stale context to every SessionStart for a rolling time window.
Table: sessions(name, started_ts, last_seen_ts, status, session_id)
  One row per session, updated in place. name is a random adjective-noun
  label assigned once on first touch, purely so a human can tell sessions
  apart at a glance - not an identifier, session_id still is. started_ts set
  once; last_seen_ts bumped on every session-start, stop-check, and
  context-check call (a heartbeat - context-check is wired to both
  UserPromptSubmit and PostToolUse, so it also gives tool-call granularity,
  not just once per turn). status = 'live' | 'dead': set to 'live' on every
  heartbeat, set to 'dead' by session-end (which used to delete the row
  outright - now it marks it dead instead, so closed sessions stay visible).
  A session abandoned without SessionEnd firing is caught by
  reap_stale_sessions (called on every heartbeat via touch_session, AND at
  the top of session_activity_note - see STALE_MINUTES /
  LIKELY_DEAD_GRACE_MINUTES in lib/sessions.py), which writes status='dead'
  back to the row itself - not just a display-time filter, so the table is
  trustworthy on its own (e.g. read directly in the SQLite viewer). The
  session_activity_note call matters specifically because git_safe.py's
  push guard reads that function directly and never calls touch_session -
  without a reap there too, a dead session's row could read 'live' forever
  regardless of wall-clock time (old task #3).
Table: context_watch(id, ts, session_id, level)
  level = 'soft' | 'hard'. One row per threshold crossed per session -
  written once each by context-check so the same token-usage nudge doesn't
  repeat every turn. Low volume by construction (at most 2 rows/session).
Table: tasks(id, status, priority, category, task_title, task_details,
             created_ts, updated_ts)
  Named `todos` before 2026-08-20 - renamed for how much easier "task" is to
  type/say than "todo".
  id is random ('t-3fa9c1'); tasks from before v2 keep their old integer
  ids as strings ("1", "2", ...).
  status = 'open' | 'discussing' | 'rejected' | 'closed' (CHECK-constrained).
  priority = 1 (blocking/do next) | 2 (important, soon) | 3 (worth doing, no
  rush) | 4 (someday). Required (NOT NULL, CHECK-constrained) - no untriaged
  state, every task gets a real priority at creation. Not Eisenhower's
  quadrants on purpose — "delegate" doesn't mean anything in a two-party
  repo, so these are our own plain-language levels instead.
  category = 'infra' (the Claude-collaboration tooling, meant to be portable
  to other projects) | 'app' (the trading bot itself). Required, same as
  priority.
  The source of truth for cross-session work items — unlike handover's free-
  text "next steps", a task persists and keeps showing up at every
  SessionStart until it's explicitly moved to rejected/closed, so nothing
  gets silently dropped just because a later handover's prose didn't repeat
  it. task_details doubles as the running note: status changes append a
  timestamped note there (e.g. why something was rejected) rather than
  overwriting the original description. Sort order everywhere is priority,
  then created_ts (random ids don't sort by age). See TASK_BLOAT_THRESHOLD
  (lib/tasks.py) for the soft-cap reminder on open+discussing count.
  The CHECK constraints double as validation of the JSON files: a file
  that breaks one makes the whole import skip (see sync_from_files).
Table: meta(key, value)
  Local bookkeeping. files_sig = signature of the .claude/state/ files at
  the last successful import.

Migrations: PRAGMA user_version. 0 = a brand-new db or the old git-tracked
layout (integer ids, handovers.delivered column, maybe a `todos` table).
_migrate takes it straight to v2 once.
"""
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from lib.state_files import (
    HANDOVER_FIELDS,
    TASK_FIELDS,
    format_problems,
    sync_from_files,
    write_handover,
    write_task,
)

# This file lives at .claude/scripts/lib/schema.py - parents[2] is .claude,
# so state.db always resolves next to the .claude directory regardless of
# which subfolder (lib/hooks/cli) ends up importing it.
DB_PATH = str(Path(__file__).resolve().parents[2] / "state.db")

SCHEMA_VERSION = 2

_TABLES = (
    """CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        status TEXT NOT NULL CHECK(status IN ('open', 'discussing', 'rejected', 'closed')),
        priority INTEGER NOT NULL CHECK(priority IN (1, 2, 3, 4)),
        category TEXT NOT NULL CHECK(category IN ('infra', 'app')),
        task_title TEXT NOT NULL,
        task_details TEXT,
        created_ts TEXT NOT NULL,
        updated_ts TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS handovers (
        id TEXT PRIMARY KEY,
        ts TEXT NOT NULL,
        session_id TEXT NOT NULL,
        summary TEXT NOT NULL,
        next_steps TEXT NOT NULL,
        questions TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS handovers_delivered (
        handover_id TEXT PRIMARY KEY,
        ts TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS context_watch (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT NOT NULL,
        session_id TEXT NOT NULL,
        level TEXT NOT NULL CHECK(level IN ('soft', 'hard'))
    )""",
    """CREATE TABLE IF NOT EXISTS sessions (
        name TEXT,
        started_ts TEXT NOT NULL,
        last_seen_ts TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'live' CHECK(status IN ('live', 'dead')),
        session_id TEXT PRIMARY KEY
    )""",
    """CREATE TABLE IF NOT EXISTS meta (
        key TEXT PRIMARY KEY,
        value TEXT
    )""",
)


def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    if conn.execute("PRAGMA user_version").fetchone()[0] < SCHEMA_VERSION:
        _migrate(conn)
    # Never let a bad state file take the db down with it - callers still
    # get a connection to the last good import, plus a warning.
    try:
        problems = sync_from_files(conn)
    except (OSError, sqlite3.Error) as e:
        problems = [f"import failed: {e}"]
    if problems:
        print(format_problems(problems), file=sys.stderr)
    return conn


def _migrate(conn):
    """Bring a v0 db (brand-new, or the old git-tracked layout) to v2, once.
    One write transaction; the version is re-checked after taking the lock,
    so two hooks racing on a fresh db can't both migrate it."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        if conn.execute("PRAGMA user_version").fetchone()[0] < SCHEMA_VERSION:
            existing = {
                r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
            }
            delivered = _export_legacy(conn, existing)
            for table in ("todos", "tasks", "handovers"):
                if table in existing:
                    conn.execute(f"DROP TABLE {table}")
            for ddl in _TABLES:
                conn.execute(ddl)
            ts = now()
            conn.executemany(
                "INSERT OR IGNORE INTO handovers_delivered (handover_id, ts) VALUES (?, ?)",
                [(hid, ts) for hid in delivered],
            )
            conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        conn.commit()
    except BaseException:
        conn.rollback()
        raise


def _export_legacy(conn, existing):
    """Write the old layout's task/handover rows out as .claude/state/ files
    (integer ids become strings; a file that already exists is never
    overwritten). Returns the ids of handovers this checkout already showed,
    for handovers_delivered."""
    for table in ("todos", "tasks"):
        if table not in existing:
            continue
        for row in conn.execute(f"SELECT {', '.join(TASK_FIELDS)} FROM {table}").fetchall():
            record = dict(zip(TASK_FIELDS, row))
            record["id"] = str(record["id"])
            write_task(record, overwrite=False)

    if "handovers" not in existing:
        return []
    cols = {r[1] for r in conn.execute("PRAGMA table_info(handovers)")}
    select = ", ".join(HANDOVER_FIELDS) + (", delivered" if "delivered" in cols else ", 1")
    rows = conn.execute(f"SELECT {select} FROM handovers").fetchall()
    # The old code only ever marked the newest handover per session, so an
    # older undelivered one from before the newest delivered one was
    # superseded, not pending - count it as delivered too.
    newest_delivered = max((r[1] for r in rows if r[-1]), default="")
    delivered = []
    for row in rows:
        record = dict(zip(HANDOVER_FIELDS, row[:-1]))
        record["id"] = str(record["id"])
        write_handover(record, overwrite=False)
        if row[-1] or record["ts"] <= newest_delivered:
            delivered.append(record["id"])
    return delivered


def now():
    return datetime.now(timezone.utc).isoformat()


def read_stdin_json():
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, ValueError):
        return {}
