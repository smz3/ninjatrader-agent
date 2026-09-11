"""CLI: price-check, then download Databento pulls into data/databento/.

Price only:  python -m tools.databento_dl ES.v.0 --schemas ohlcv-1d ohlcv-1m --start 2016-09-01
Download:    ... --download --max-cost 15

Prices every pull first (free). Refuses to download if the total is over
--max-cost. Skips pulls whose .parquet already exists, and on a retry only
fetches the yearly chunks still missing (no double spend).
"""
import argparse

from .download import DATA_DIR, Pull, client, dataset_end, download, price


def main():
    p = argparse.ArgumentParser(prog="python -m tools.databento_dl")
    p.add_argument("symbol", help="continuous symbol, e.g. ES.v.0")
    p.add_argument("--schemas", nargs="+", required=True, help="e.g. ohlcv-1d ohlcv-1m trades")
    p.add_argument("--start", required=True, help="YYYY-MM-DD (UTC)")
    p.add_argument("--end", help="default: latest available")
    p.add_argument("--download", action="store_true", help="actually fetch (spends credit)")
    p.add_argument("--max-cost", type=float, default=0.0, help="USD cap for the whole run")
    a = p.parse_args()

    c = client()
    end = a.end or dataset_end(c)
    pulls = [Pull(a.symbol, s, a.start, end) for s in a.schemas]

    todo, total = [], 0.0
    for pull in pulls:
        if (DATA_DIR / f"{pull.stem}.parquet").exists():
            print(f"{pull.stem}: already downloaded, skip")
            continue
        cost, size = price(c, pull)
        total += cost
        todo.append(pull)
        print(f"{pull.stem}: ${cost:.2f}  {size / 1e6:.1f} MB")
    print(f"total: ${total:.2f}")

    if not a.download or not todo:
        return
    if total > a.max_cost:
        raise SystemExit(f"refused: ${total:.2f} > --max-cost ${a.max_cost:.2f}")
    for pull in todo:
        pq, rows = download(c, pull)
        print(f"saved {pq.name}  {rows:,} rows")


if __name__ == "__main__":
    main()
