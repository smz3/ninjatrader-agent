"""ForexFactory calendar scrape: month pages -> USD events with exact times.

Each month page embeds its events as JSON (window.calendarComponentStates).
`dateline` is a unix timestamp, so times don't depend on the page's display
timezone (FF picks that from your IP). Only USD events are kept, all impacts.

Don't use the Hugging Face dump (Ehsanrs2/Forex_Factory_Calendar) instead:
its times are broken - e.g. NFP 2016-2024 shows as 00:00 Tehran, i.e.
15:30 ET the day before.
"""
import calendar
import json
import time
from datetime import date
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT / "data" / "news" / "ff"
URL = "https://www.forexfactory.com/calendar?month={slug}"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0 Safari/537.36"
}
KEEP = ("id", "dateline", "name", "impactName", "timeLabel", "actual", "forecast", "previous")
DELAY_S = 2.0  # between page fetches - be polite


def months(start: date, end: date):
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def parse(html: str) -> list[dict]:
    i = html.find("days: [")
    if i < 0:
        raise ValueError("no calendar JSON on page (layout changed or blocked)")
    i += len("days: ")
    days = json.loads(html[i:html.find("\n", i)].rstrip().rstrip(","))
    return [{k: e[k] for k in KEEP} for d in days for e in d["events"] if e["currency"] == "USD"]


def fetch_month(y: int, m: int, session: requests.Session) -> list[dict]:
    url = URL.format(slug=f"{calendar.month_abbr[m].lower()}.{y}")
    for attempt in range(3):
        try:
            r = session.get(url, headers=HEADERS, timeout=60)
            r.raise_for_status()
            return parse(r.text)
        except (requests.RequestException, ValueError):
            if attempt == 2:
                raise
            time.sleep(10 * (attempt + 1))


def load(start: date, end: date, refresh: bool = False, log=print) -> list[dict]:
    """USD events for every month in [start, end].

    Months that ended before last month are cached for good under
    data/news/ff/; last month, this month and future months are always
    refetched (schedules move, actuals get filled in).
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today()
    settled = (today.year, today.month - 1) if today.month > 1 else (today.year - 1, 12)
    events, session, fetched = [], requests.Session(), False
    for y, m in months(start, end):
        path = CACHE_DIR / f"{y}-{m:02d}.json"
        if path.exists() and not refresh and (y, m) < settled:
            events += json.loads(path.read_text(encoding="utf-8"))
            continue
        if fetched:
            time.sleep(DELAY_S)
        ev = fetch_month(y, m, session)
        fetched = True
        path.write_text(json.dumps(ev), encoding="utf-8")
        log(f"ff {y}-{m:02d}: {len(ev)} USD events")
        events += ev
    return events
