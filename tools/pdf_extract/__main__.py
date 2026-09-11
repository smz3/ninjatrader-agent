"""CLI for reading PDFs without blowing up the chat context.

Text:    python -m tools.pdf_extract inbox/book.pdf [--pages 1-10] [--out notes.md]
Charts:  python -m tools.pdf_extract inbox/book.pdf --render 13,17 [--dpi 100]

Prints only a short summary (pages, ~tokens, which pages have images); then
read the .md and just the PNGs that matter.
"""
import argparse
from pathlib import Path

from .extract import extract_text, render_pages


def _pages(nums: list[int]) -> str:
    return ",".join(map(str, nums)) or "none"


def main():
    p = argparse.ArgumentParser(prog="python -m tools.pdf_extract")
    p.add_argument("pdf", type=Path)
    p.add_argument("--pages", help="e.g. 1-5,9 (default: all)")
    p.add_argument("--out", type=Path, help="text output (default: <pdf>.md next to the PDF)")
    p.add_argument("--render", metavar="PAGES", help="save these pages as PNGs instead of text")
    p.add_argument("--dpi", type=int, default=100)
    a = p.parse_args()

    if a.render:
        for path in render_pages(a.pdf, a.pdf.parent, a.render, a.dpi):
            print(path)
        return

    out = a.out or a.pdf.with_suffix(".md")
    infos = extract_text(a.pdf, out, a.pages)
    chars = sum(i.chars for i in infos)
    print(f"{out}  {len(infos)} pages  ~{chars // 4:,} tokens of text")
    print(f"image-only pages (render to read): {_pages([i.number for i in infos if i.image_only])}")
    print("pages with images (render if the chart matters): "
          f"{_pages([i.number for i in infos if i.images and not i.image_only])}")


if __name__ == "__main__":
    main()
