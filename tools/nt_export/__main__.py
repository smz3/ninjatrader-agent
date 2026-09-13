"""CLI: convert data/databento/ES...1m parquet -> NT8 import text files.

python -m tools.nt_export
python -m tools.nt_export --tz America/New_York
python -m tools.nt_export --news   # also/instead: news_usd_high.csv for Orb.cs
"""
import argparse

from .export import DEFAULT_TZ, ROOT, export, export_news


def main():
    p = argparse.ArgumentParser(prog="python -m tools.nt_export")
    p.add_argument("--tz", default=DEFAULT_TZ, help=f"default: {DEFAULT_TZ} (NT8/CME exchange time)")
    p.add_argument("--news", action="store_true", help="only export the news filter CSV, skip bars")
    a = p.parse_args()

    paths = [export_news(tz=a.tz)] if a.news else [*export(tz=a.tz), export_news(tz=a.tz)]
    for path in paths:
        print(f"wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
