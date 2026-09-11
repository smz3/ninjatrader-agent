"""CLI: convert data/databento/ES...1m parquet -> NT8 import text files.

python -m tools.nt_export
python -m tools.nt_export --tz America/New_York
"""
import argparse

from .export import DEFAULT_TZ, ROOT, export


def main():
    p = argparse.ArgumentParser(prog="python -m tools.nt_export")
    p.add_argument("--tz", default=DEFAULT_TZ, help=f"default: {DEFAULT_TZ} (NT8/CME exchange time)")
    a = p.parse_args()

    for path in export(tz=a.tz):
        print(f"wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
