# ninjatrader-agent

## Session continuity

- Shared state = one JSON file per record, git-tracked:
  `.claude/state/tasks/<id>.json` and `.claude/state/handovers/<id>.json`
  (random ids like `t-3fa9c1`; older tasks keep `1`, `2`, `3`). Branches and
  worktrees merge record by record - only both sides editing the same task
  conflicts, as a normal text conflict in that one file. Until it's
  resolved, db calls warn and keep the last good import. Change them via
  `db.py`, not by hand.
- `.claude/state.db` (SQLite) is a local, gitignored cache of those files
  plus local-only tables (`sessions`, `context_watch`,
  `handovers_delivered`). Safe to delete - rebuilt from the files on the
  next db call. Full schema + rationale: docstrings in
  `.claude/scripts/lib/schema.py` and `lib/state_files.py`. `db.py` is just
  the CLI entrypoint/router; logic lives under
  `.claude/scripts/{hooks,cli,lib}/` by who calls it - `hooks/` = only ever
  invoked by a settings.json hook, `cli/` = only ever invoked manually,
  `lib/` = shared helpers used by both.
- SessionStart shows the current + 1 previous undelivered handover, then
  marks them (and anything older) delivered in this checkout so they don't
  repeat.
- `/handover` — wrap up a session: saves work, syncs tasks, logs a handover.
- `tasks` table is the source of truth for cross-session work items. Manage
  via `db.py task-add` / `task-status` / `task-list`. When the user hands you
  a new work item in conversation, log it immediately in the same turn -
  don't wait to be asked.
- Before `task-add`, always run `task-list` first and check by *meaning*,
  not just title text, whether an open/discussing task already covers it -
  a root cause you just found is usually an update to the task that
  prompted the investigation, not a new task. This is a behavioral rule on
  purpose, not a code-level dedup check - matching by meaning needs
  understanding, not a string-similarity heuristic.
- Context tripwire: warns at 100k tokens (soft), 145k (hard). Checked on
  both UserPromptSubmit and PostToolUse.
- `sessions.status` self-heals on your next heartbeat — safe to resume a
  session after being idle past 5min.

## Git workflow

- SessionStart flags another active session on `main`? Use a worktree
  (`EnterWorktree`), don't edit directly.
- Nothing flagged, working solo -> use `main` directly.
- Worktree done -> merge into `main`, remove the worktree.
- Commit/push via `.claude/scripts/git_safe.py`, not raw `git commit`/
  `git push`. Auto-push after every commit, no confirmation needed.
- Push takes `--session <id>`. If it's blocked on a session you know is
  actually closed, prefer `db.py session-end --session <id>` to mark it
  dead once (clears the guard for good) over repeating
  `--override-session-guard` on every push.

## Stack

Not yet decided.
