"""Manual handover logging (normally invoked via the /handover skill). Read
helpers used by the SessionStart hook live in lib/handovers.py.

File-first like cli/tasks.py: the handover's JSON file under
.claude/state/handovers/ is the record; get_conn() then re-imports it.
"""
import json

from lib.schema import get_conn, now
from lib.state_files import HANDOVERS_DIR, new_id, write_handover


def cmd_log(args):
    write_handover({
        "id": new_id("h", HANDOVERS_DIR),
        "ts": now(),
        "session_id": args.session,
        "summary": args.summary,
        "next_steps": args.next,
        "questions": args.questions or "",
    })
    get_conn().close()
    print(json.dumps({"systemMessage": "Handover logged."}))
