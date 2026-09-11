"""Backup FOMC dates straight from federalreserve.gov.

Statement dates come from the statement press-release links
(monetaryYYYYMMDDa.htm), which covers unscheduled moves too. Upcoming
meetings with no statement yet come from the calendar's month/date cells.
The page has no release time: scheduled statements are 14:00 ET, so callers
assume that.
"""
import calendar
import re
from datetime import date

import requests

from .ff import HEADERS

BASE = "https://www.federalreserve.gov/monetarypolicy/"
MONTH = {calendar.month_abbr[i]: i for i in range(1, 13)}


def _get(page: str) -> str:
    r = requests.get(BASE + page, headers=HEADERS, timeout=60)
    r.raise_for_status()
    return r.text


def statement_dates(html: str) -> set[date]:
    return {date(int(s[:4]), int(s[4:6]), int(s[6:])) for s in re.findall(r"monetary(\d{8})a\.htm", html)}


def scheduled(html: str) -> set[date]:
    """Last day of each meeting listed on the current calendar page."""
    out = set()
    for block in re.split(r"(?=\b\d{4} FOMC Meetings)", html):
        head = re.match(r"(\d{4}) FOMC Meetings", block)
        if not head:
            continue
        cells = re.findall(
            r"fomc-meeting__month[^>]*><strong>([^<]+)</strong>.*?fomc-meeting__date[^>]*>([^<]+)<",
            block, re.S,
        )
        for mon, days in cells:
            mon, nums = mon.split("/")[-1].strip()[:3], re.findall(r"\d+", days)
            if mon in MONTH and nums:
                out.add(date(int(head.group(1)), MONTH[mon], int(nums[-1])))
    return out


def load(start_year: int) -> set[date]:
    """Statement + scheduled meeting dates from start_year onwards."""
    cur = _get("fomccalendars.htm")
    first_current = min(int(y) for y in re.findall(r"(\d{4}) FOMC Meetings", cur))
    dates = statement_dates(cur) | scheduled(cur)
    for y in range(start_year, first_current):
        dates |= statement_dates(_get(f"fomchistorical{y}.htm"))
    return {d for d in dates if d.year >= start_year}
