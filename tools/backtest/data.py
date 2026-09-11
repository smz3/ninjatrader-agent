"""ES 1m bars (Databento, UTC) -> ET trading sessions with the levels setups need.

Session = CME Globex day: 18:00 ET the evening before -> 17:00 ET, named by the
date it ends on. Minutes are counted from that date's midnight ET, so the
overnight part is negative (18:00 the evening before = -360) and times
compare in order (09:30 = 570).

Rolls: ES.v.0 is not back-adjusted; the contract switches at a session start
(instrument_id changes). Each session keeps only the bars of its main RTH
contract, and levels from the prior session (close/high/low, ATR's prior
close) are only used when that session traded the same contract - a close
from the old contract would fake a gap.

ATR = simple mean true range of the prior ATR_LEN full sessions (never the
current one). Overnight high/low = 18:00 -> 09:30. Prior-day high/low/close
= prior session's RTH (09:30-16:00).

News = data/news/usd_high.csv (python -m tools.news_dates): USD High-impact
event minutes per date; an all-day row (elections) flags the whole date.
"""
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
BARS = ROOT / "data" / "databento" / "ES.v.0_ohlcv-1m_2016-09-01_2026-09-10.parquet"
NEWS = ROOT / "data" / "news" / "usd_high.csv"
SOURCE = "databento ES.v.0 ohlcv-1m"
TICK = 0.25
PT_USD = 50.0
RTH_OPEN, RTH_CLOSE = 570, 960       # 09:30, 16:00 ET
WORK_FROM = 540                      # sim works on 09:00-16:00 bars
ATR_LEN = 14


def hm(s: str) -> int:
    """'09:30' -> 570 minutes."""
    h, m = s.split(":")
    return int(h) * 60 + int(m)


@dataclass
class Day:
    date: str                  # YYYY-MM-DD (ET)
    mins: np.ndarray           # 09:00-16:00 bars only (see WORK_FROM)
    o: np.ndarray
    h: np.ndarray
    l: np.ndarray
    c: np.ndarray
    v: np.ndarray
    rth_open: float
    atr: float | None
    prev_close: float | None   # None = no prior session or contract rolled
    prev_high: float | None
    prev_low: float | None
    on_high: float | None
    on_low: float | None
    news: tuple                # event minutes ET
    news_all_day: bool


def _news() -> tuple[dict, set]:
    if not NEWS.exists():
        raise SystemExit(f"{NEWS.relative_to(ROOT)} missing - run python -m tools.news_dates")
    n = pd.read_csv(NEWS, dtype={"time_et": str})
    all_day = set(n.loc[n.all_day.astype(str) == "True", "date_et"])
    timed = n[n.time_et.notna() & ~n.date_et.isin(all_day)]
    by_date = {}
    for d, t in zip(timed.date_et, timed.time_et):
        by_date.setdefault(d, set()).add(hm(t))
    return {d: tuple(sorted(v)) for d, v in by_date.items()}, all_day


@lru_cache(maxsize=1)
def sessions() -> tuple[Day, ...]:
    """Every session with RTH bars, oldest first (cached per process)."""
    df = pd.read_parquet(BARS, columns=["instrument_id", "open", "high", "low", "close", "volume"])
    et = df.index.tz_convert("America/New_York").tz_localize(None)
    date = (et + pd.Timedelta(hours=6)).normalize()
    df = df.assign(date=date.strftime("%Y-%m-%d"),
                   m=((et - date) // pd.Timedelta(minutes=1)).astype(int)).reset_index(drop=True)
    df = df[(df.m >= -360) & (df.m < 1020)]

    rth = df[(df.m >= RTH_OPEN) & (df.m < RTH_CLOSE)]
    main = rth.groupby(["date", "instrument_id"]).volume.sum().reset_index()
    main = main.loc[main.groupby("date").volume.idxmax(), ["date", "instrument_id"]]
    df = df.merge(main, on=["date", "instrument_id"])      # keeps order, drops other contract

    g = df.groupby("date", sort=True)
    daily = pd.DataFrame({"inst": g.instrument_id.first(), "hi": g.high.max(), "lo": g.low.min(),
                          "cl": g.close.last()})
    r = df[(df.m >= RTH_OPEN) & (df.m < RTH_CLOSE)].groupby("date")
    daily = daily.join(pd.DataFrame({"rth_open": r.open.first(), "rth_high": r.high.max(),
                                     "rth_low": r.low.min(), "rth_close": r.close.last()}))
    on = df[df.m < RTH_OPEN].groupby("date")
    daily = daily.join(pd.DataFrame({"on_high": on.high.max(), "on_low": on.low.min()}))

    same = daily.inst.eq(daily.inst.shift())
    pc = daily.cl.shift().where(same)
    tr = pd.concat([daily.hi - daily.lo, (daily.hi - pc).abs(), (daily.lo - pc).abs()], axis=1).max(axis=1)
    daily["atr"] = tr.rolling(ATR_LEN).mean().shift()
    for k in ("rth_close", "rth_high", "rth_low"):
        daily["prev_" + k[4:]] = daily[k].shift().where(same)

    news, all_day = _news()
    work = df[(df.m >= WORK_FROM) & (df.m < RTH_CLOSE)]
    cols = {k: work[k].to_numpy() for k in ("m", "open", "high", "low", "close", "volume")}
    dates = work.date.to_numpy()
    cuts = np.flatnonzero(dates[1:] != dates[:-1]) + 1
    starts, ends = np.r_[0, cuts], np.r_[cuts, len(dates)]

    nan = lambda x: None if pd.isna(x) else float(x)
    out = []
    for a, b in zip(starts, ends):
        d = dates[a]
        row = daily.loc[d]
        out.append(Day(
            date=d, mins=cols["m"][a:b], o=cols["open"][a:b], h=cols["high"][a:b],
            l=cols["low"][a:b], c=cols["close"][a:b], v=cols["volume"][a:b].astype(float),
            rth_open=float(row.rth_open), atr=nan(row.atr), prev_close=nan(row.prev_close),
            prev_high=nan(row.prev_high), prev_low=nan(row.prev_low), on_high=nan(row.on_high),
            on_low=nan(row.on_low), news=news.get(d, ()), news_all_day=d in all_day))
    return tuple(out)


def window(start: str, end: str) -> list[Day]:
    """Sessions with start <= date <= end (YYYY-MM-DD)."""
    return [d for d in sessions() if start <= d.date <= end]
