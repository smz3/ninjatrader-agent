"""Databento ES 1m parquet -> NinjaTrader 8 import text format.

NT8's Import Wizard expects one row per bar as
`yyyyMMdd HHmmss;open;high;low;close;volume`. Timestamps are written in
America/Chicago because NT8/CME session templates (RTH 08:30-15:15 CT) are
defined in Exchange time, which is Central for CME Globex - verify against
Tools > Options > General > Time Zone in NT8 before trusting session-boundary
logic like ORB.

ES.v.0 is not back-adjusted (see databento_dl/download.py) - rows keep the
raw price of whichever contract was highest-volume that day, same convention
the Python/Nautilus backtests used. Import this into a dedicated
backtest-only NT8 instrument, never a live-tradeable contract, so a rollover
mid-file doesn't corrupt real trading data.
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
BARS = ROOT / "data" / "databento" / "ES.v.0_ohlcv-1m_2016-09-01_2026-09-10.parquet"
OUT_DIR = ROOT / "data" / "nt_import"
DEFAULT_TZ = "America/Chicago"


def export(tz: str = DEFAULT_TZ, out_dir: Path = OUT_DIR) -> list[Path]:
    """One .txt per calendar year, NT8 minute-import format. Returns paths written."""
    df = pd.read_parquet(BARS, columns=["open", "high", "low", "close", "volume"])
    local = df.index.tz_convert(tz)
    stamp = local.strftime("%Y%m%d %H%M%S")
    lines = (stamp + ";" + df.open.round(2).astype(str) + ";" + df.high.round(2).astype(str)
              + ";" + df.low.round(2).astype(str) + ";" + df.close.round(2).astype(str)
              + ";" + df.volume.astype(int).astype(str))

    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for year, chunk in lines.groupby(local.year):
        path = out_dir / f"ES_1m_{year}.txt"
        path.write_text("\n".join(chunk), encoding="ascii")
        written.append(path)
    return written
