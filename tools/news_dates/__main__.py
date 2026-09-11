"""CLI: build the USD high-impact news list for the backtest news filter.

Default:  python -m tools.news_dates          (2016-09 -> 3 months ahead)
Custom:   python -m tools.news_dates --start 2016-09 --end 2026-12 --refresh

Writes data/news/usd_high.csv, one row per event, times in ET (exchange
time) plus UTC (to join Databento bars). source=ff = ForexFactory
High-impact USD ("red folder" - Lucid's rule). source=fed = an FOMC
statement day from federalreserve.gov that FF doesn't list (14:00 ET
assumed). all_day=True = FF gave no time (elections etc.). Union on
purpose: if either source lists it, the bot avoids it.
"""
import argparse
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import pandas as pd

from . import ff, fomc

ET = ZoneInfo("America/New_York")
OUT = ff.ROOT / "data" / "news" / "usd_high.csv"
FOMC_WORDS = ("FOMC", "Federal Funds Rate", "Fed Announcement")


def month_arg(s: str) -> date:
    y, m = map(int, s.split("-"))
    return date(y, m, 1)


def add_months(d: date, n: int) -> date:
    k = d.month - 1 + n
    return date(d.year + k // 12, k % 12 + 1, 1)


def main():
    p = argparse.ArgumentParser(prog="python -m tools.news_dates")
    p.add_argument("--start", type=month_arg, default=date(2016, 9, 1), help="YYYY-MM")
    p.add_argument("--end", type=month_arg, help="YYYY-MM (default: 3 months ahead)")
    p.add_argument("--refresh", action="store_true", help="refetch cached months too")
    a = p.parse_args()
    end = a.end or add_months(date.today(), 3)
    stop = add_months(end, 1)  # exclusive

    high = {e["id"]: e for e in ff.load(a.start, end, a.refresh) if e["impactName"] == "high"}
    rows = [
        dict(et=datetime.fromtimestamp(e["dateline"], ET), event=e["name"], source="ff",
             all_day=not e["timeLabel"][:1].isdigit(), ff_id=e["id"])
        for e in high.values()
    ]
    ff_fomc = {r["et"].date() for r in rows if any(w in r["event"] for w in FOMC_WORDS)}
    fed = {d for d in fomc.load(a.start.year) if a.start <= d < stop}
    for d in sorted(fed - ff_fomc):
        rows.append(dict(et=datetime.combine(d, time(14), ET), event="FOMC Statement (Fed site)",
                         source="fed", all_day=False, ff_id=None))

    df = pd.DataFrame(rows)
    df["et"] = pd.to_datetime(df.et, utc=True).dt.tz_convert(ET)
    df = df[(df.et.dt.date >= a.start) & (df.et.dt.date < stop)].sort_values(["et", "event"])
    df.insert(1, "utc", df.et.dt.tz_convert("UTC"))
    df.insert(2, "date_et", df.et.dt.strftime("%Y-%m-%d"))
    df.insert(3, "time_et", df.et.dt.strftime("%H:%M"))
    df["ff_id"] = df.ff_id.astype("Int64")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)

    ff_stmt = {t.date() for t, e in zip(df.et, df.event) if e == "FOMC Statement"}
    print(f"saved {OUT.relative_to(ff.ROOT)}: {len(df)} events, {df.date_et.nunique()} days")
    print(f"fed-only FOMC days added: {sorted(str(d) for d in fed - ff_fomc)}")
    print(f"FF FOMC Statement days not on Fed site: {sorted(str(d) for d in ff_stmt - fed)}")
    print(f"all-day events: {int(df.all_day.sum())}")


if __name__ == "__main__":
    main()
