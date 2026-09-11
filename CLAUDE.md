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

- Prop firm: Lucid Trading - LucidDaily 50K, EOD eval drawdown, $1,200 daily
  loss limit, personal profile. Funded = intraday drawdown + red-folder USD
  news is a hard breach (bot must be flat around it). Research + rules:
  `docs/research/prop-firm-shortlist.md`.
- Platform: NinjaTrader 8, strategies in NinjaScript (C#), connected via the
  Lucid dashboard's Tradovate login. Runs on a Windows VPS.
- Instrument: ES (MES only when a stop is too wide for exact risk sizing).
- Prop math / risk sizing: `tools/prop_sim` (eval) and
  `python -m tools.prop_sim.funded` (funded payouts).

## Strategy registry

- Every setup idea and every test lives in `registry/` (git-tracked, one
  JSON per record): `strategies/<id>.json` = rules + numbers + status,
  `runs/<id>.json` = one test (data window, costs, spec snapshot, results
  for every combo tried). Schema + rules: `tools/registry/schema.py`
  docstring, or `python -m tools.registry schema`.
- New idea -> add a strategy record (status `idea`), never just a task note.
  Check `python -m tools.registry list` first - it may already be there.
- Backtests record results via `tools.registry.store.new_run()`; compare
  with `python -m tools.registry list` / `runs`. Rule/number change = bump
  `version`. Never delete runs or rejected strategies.
- Run `python -m tools.registry check` before committing registry changes.

## Reading PDFs

- Don't paste big PDFs into chat - every page goes in as an image
  (~1.5-2k tokens/page; a 32-page ebook ate ~55-60k). Drop them in `inbox/`
  (gitignored) and run `python -m tools.pdf_extract inbox/<file>.pdf`: text
  goes to `inbox/<file>.md`, and it lists which pages have images. Render
  only the chart pages that matter with `--render 13,17`, then Read those PNGs.
- Whole-book reads can also go to a subagent (if the user asks) so only the
  summary lands in the main context. Save findings in full to `docs/research/`.
