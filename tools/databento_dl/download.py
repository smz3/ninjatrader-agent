"""Price-check and download CME futures data from Databento.

Every pull is priced first with Databento's free cost estimate; anything over
the cap is refused before a cent is spent. Pulls are split into calendar-year
chunks, each fetched as its own Databento batch job: the server builds the
file, then we download it (resumable). Never use plain streaming
(timeseries.get_range) here: it kept breaking mid-pull on this connection AND
each broken stream was billed as if complete (2026-09-11: 12.90 USD pull
cost 26.92 USD). Each chunk's job id is saved next
to it (<chunk>.dbn.zst.job) so a re-run reuses the job instead of paying
again, and a re-run only fetches chunks still missing.

Chunks are kept as .dbn.zst (Databento's own format, re-readable offline for
free) under parts/<pull>/, then joined into one .parquet for pandas.
Timestamps stay UTC - convert to ET in the backtest.

Continuous symbols like ES.v.0 follow the highest-volume contract and are NOT
back-adjusted: prices jump at each roll (instrument_id changes on that row).
"""
import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

import databento as db
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "databento"
DATASET = "GLBX.MDP3"  # CME Globex
POLL_SECONDS = 15


@dataclass
class Pull:
    symbol: str  # e.g. ES.v.0
    schema: str  # e.g. ohlcv-1m, ohlcv-1d, trades
    start: str   # YYYY-MM-DD or ISO datetime, UTC
    end: str

    @property
    def stem(self) -> str:
        return f"{self.symbol}_{self.schema}_{self.start[:10]}_{self.end[:10]}"

    def params(self) -> dict:
        return dict(dataset=DATASET, symbols=[self.symbol], stype_in="continuous",
                    schema=self.schema, start=self.start, end=self.end)

    def yearly(self) -> list["Pull"]:
        """Split into calendar-year chunks (end is exclusive, so no overlap)."""
        start, end = pd.Timestamp(self.start, tz="UTC"), pd.Timestamp(self.end, tz="UTC")
        cuts = [start] + [pd.Timestamp(y, 1, 1, tz="UTC") for y in range(start.year + 1, end.year + 1)] + [end]
        return [Pull(self.symbol, self.schema, a.isoformat(), b.isoformat())
                for a, b in zip(cuts, cuts[1:]) if a < b]


def client() -> db.Historical:
    """API key from the env, else from the repo's gitignored .env."""
    key = os.environ.get("DATABENTO_API_KEY")
    if not key and (ROOT / ".env").exists():
        for line in (ROOT / ".env").read_text().splitlines():
            k, _, v = line.partition("=")
            if k.strip() == "DATABENTO_API_KEY":
                key = v.strip().strip("\"'")
    if not key:
        raise SystemExit("DATABENTO_API_KEY not set (env or .env)")
    return db.Historical(key)


def dataset_end(c: db.Historical) -> str:
    return c.metadata.get_dataset_range(dataset=DATASET)["end"]


def price(c: db.Historical, pull: Pull) -> tuple[float, int]:
    """(USD cost, billable bytes) - free to call."""
    p = pull.params()
    return c.metadata.get_cost(**p), c.metadata.get_billable_size(**p)


def _job_for(c: db.Historical, chunk: Pull, dest: Path) -> str:
    """Reuse the chunk's saved job id, else submit a new job (spends credit)."""
    job_file = dest.with_name(dest.name + ".job")
    if job_file.exists():
        return job_file.read_text().strip()
    job_id = c.batch.submit_job(**chunk.params(), split_duration="none")["id"]
    job_file.write_text(job_id)
    print(f"  submitted {chunk.stem} ({job_id})")
    return job_id


def download(c: db.Historical, pull: Pull, out_dir: Path = DATA_DIR) -> tuple[Path, int]:
    """Fetch every missing chunk via batch jobs, then join. Returns (parquet path, rows)."""
    parts = out_dir / "parts" / pull.stem
    parts.mkdir(parents=True, exist_ok=True)
    chunks = {parts / f"{ch.stem}.dbn.zst": ch for ch in pull.yearly()}

    pending = {_job_for(c, ch, f): f for f, ch in chunks.items() if not f.exists()}
    staging = parts / "_batch"
    while pending:
        done = {j["id"] for j in c.batch.list_jobs(states="done")}
        for job_id in [j for j in pending if j in done]:
            f = pending.pop(job_id)
            files = c.batch.download(job_id=job_id, output_dir=staging)
            next(p for p in files if p.name.endswith(".dbn.zst")).replace(f)
            f.with_name(f.name + ".job").unlink()
            print(f"  got {f.name}")
        if pending:
            time.sleep(POLL_SECONDS)
    shutil.rmtree(staging, ignore_errors=True)

    df = pd.concat(db.DBNStore.from_file(f).to_df() for f in chunks).sort_index()
    pq = out_dir / f"{pull.stem}.parquet"
    df.to_parquet(pq)
    return pq, len(df)
