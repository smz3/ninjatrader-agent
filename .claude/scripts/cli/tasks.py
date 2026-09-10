"""Manual task-management commands (task-add/task-status/task-retitle/
task-list). The PostToolUse task-remind nudge is a hook, not a manual
command - see hooks/task_remind.py. Shared validation/bloat-check helpers
live in lib/tasks.py (also used by hooks/sessions.py for the SessionStart
summary).

Writes are file-first (see lib/state_files.py): the task's JSON file under
.claude/state/tasks/ is written, then get_conn() re-imports it into the db.
Edits read the record from its file, not the db, so they always start from
the git-tracked truth even if the db's last import was skipped.
"""
import json
import sys

from lib.schema import get_conn, now
from lib.state_files import TASKS_DIR, new_id, read_task, write_task
from lib.tasks import check_task_bloat, validate_task_title


def _fail(message):
    print(json.dumps({"error": message}))
    sys.exit(1)


def _load_task(task_id):
    try:
        record = read_task(task_id)
    except (OSError, ValueError) as e:
        _fail(f"task {task_id}'s file doesn't parse ({e}) - unresolved merge conflict?")
    if record is None:
        _fail(f"no task with id {task_id}")
    return record


def _bloat_after_write():
    conn = get_conn()
    bloat = check_task_bloat(conn)
    conn.close()
    return bloat


def cmd_task_add(args):
    validate_task_title(args.title)
    ts = now()
    task_id = new_id("t", TASKS_DIR)
    write_task({
        "id": task_id,
        "status": "open",
        "priority": args.priority,
        "category": args.category,
        "task_title": args.title,
        "task_details": args.details or "",
        "created_ts": ts,
        "updated_ts": ts,
    })
    bloat = _bloat_after_write()
    result = {
        "id": task_id,
        "status": "open",
        "priority": args.priority,
        "category": args.category,
        "task_title": args.title,
    }
    if bloat:
        result["reminder"] = bloat
    print(json.dumps(result))


def cmd_task_status(args):
    record = _load_task(args.id)
    details = record.get("task_details") or ""
    if args.note:
        addition = f"[{now()} -> {args.status}] {args.note}"
        details = f"{details}\n{addition}" if details else addition

    record["status"] = args.status
    record["task_details"] = details
    if args.priority is not None:
        record["priority"] = args.priority
    if args.category is not None:
        record["category"] = args.category
    record["updated_ts"] = now()
    write_task(record)

    bloat = _bloat_after_write()
    result = {
        "id": args.id,
        "status": args.status,
        "priority": record["priority"],
        "category": record["category"],
    }
    if bloat:
        result["reminder"] = bloat
    print(json.dumps(result))


def cmd_task_retitle(args):
    validate_task_title(args.title)
    record = _load_task(args.id)
    record["task_title"] = args.title
    record["updated_ts"] = now()
    write_task(record)
    get_conn().close()
    print(json.dumps({"id": args.id, "task_title": args.title}))


def cmd_task_list(args):
    statuses = [s.strip() for s in (args.status or "open,discussing").split(",") if s.strip()]
    placeholders = ",".join("?" for _ in statuses)
    params = list(statuses)
    category_clause = ""
    if args.category:
        category_clause = " AND category = ?"
        params.append(args.category)
    conn = get_conn()
    rows = conn.execute(
        f"SELECT id, status, priority, category, task_title, task_details, created_ts, updated_ts "
        f"FROM tasks WHERE status IN ({placeholders}){category_clause} "
        f"ORDER BY priority, created_ts, id",
        params,
    ).fetchall()
    conn.close()
    print(json.dumps([
        {
            "id": r[0],
            "status": r[1],
            "priority": r[2],
            "category": r[3],
            "task_title": r[4],
            "task_details": r[5],
            "created_ts": r[6],
            "updated_ts": r[7],
        }
        for r in rows
    ]))
