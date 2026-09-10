"""Handover read helpers shared with hooks/sessions.py's SessionStart
handler. Writing a handover (cmd_log) is CLI-only - see cli/handovers.py.
See lib/schema.py for the handovers table's shape/lifecycle.
"""
from lib.schema import now

# SessionStart shows at most this many distinct sessions' latest undelivered
# handover (current + 1 previous) - not a time window. Combined with
# handovers_delivered, a handover is shown once (to whichever session starts
# next in this checkout) and then never replayed again.
HANDOVER_SHOW_COUNT = 2


def recent_handovers(conn, exclude_session_id, limit=HANDOVER_SHOW_COUNT):
    """Latest undelivered handover from up to `limit` distinct sessions (other
    than exclude_session_id), most recent first.

    Marks EVERY undelivered handover it looked at as delivered, not just the
    ones returned - the rest are either superseded (an older handover from a
    session whose newer one is shown) or older than the `limit` sessions
    shown. Otherwise a fresh checkout, whose local db has never delivered
    anything, would drip-feed the whole handover history two at a time over
    the next sessions.
    """
    rows = conn.execute(
        "SELECT id, session_id, ts, summary, next_steps, questions FROM handovers h "
        "WHERE session_id != ? AND NOT EXISTS "
        "(SELECT 1 FROM handovers_delivered d WHERE d.handover_id = h.id) "
        "ORDER BY ts DESC",
        (exclude_session_id,),
    ).fetchall()
    out, seen_sessions = [], set()
    for _row_id, session_id, ts, summary, next_steps, questions in rows:
        if session_id in seen_sessions or len(out) >= limit:
            continue
        seen_sessions.add(session_id)
        out.append((session_id, (ts, summary, next_steps, questions)))
    if rows:
        ts = now()
        conn.executemany(
            "INSERT OR IGNORE INTO handovers_delivered (handover_id, ts) VALUES (?, ?)",
            [(row[0], ts) for row in rows],
        )
        conn.commit()
    return out


def format_handovers(handovers):
    if not handovers:
        return "No undelivered handover (first session on this repo, or nothing new since the last one)."
    blocks = []
    for session_id, (ts, summary, next_steps, questions) in handovers:
        blocks.append(
            f"# Handover from session {session_id} (saved {ts})\n"
            f"Summary: {summary}\n"
            f"Next steps: {next_steps}\n"
            f"Open questions: {questions or ''}"
        )
    return "\n\n".join(blocks)
