"""Pull text out of a PDF so it can be read cheaply.

Pasting a PDF into chat sends every page as an image (~1.5-2k tokens a page).
Plain text is usually 5-10x cheaper. Pages that carry images get listed so
only the ones whose charts matter are rendered and looked at.
"""
from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF

BLANK_TEXT_CHARS = 50  # fewer chars than this = image-only page


@dataclass
class PageInfo:
    number: int  # 1-based
    chars: int
    images: int

    @property
    def image_only(self) -> bool:
        return self.chars < BLANK_TEXT_CHARS


def parse_pages(spec: str | None, total: int) -> list[int]:
    """'1-5,9' -> [1, 2, 3, 4, 5, 9], 1-based, clipped to the document."""
    if not spec:
        return list(range(1, total + 1))
    pages = set()
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            lo, hi = part.split("-", 1)
            pages.update(range(int(lo), int(hi) + 1))
        elif part:
            pages.add(int(part))
    return sorted(p for p in pages if 1 <= p <= total)


def extract_text(pdf: Path, out: Path, pages: str | None = None) -> list[PageInfo]:
    """Write one '## Page N' section per page to `out`; return per-page stats."""
    infos = []
    chunks = [f"# {pdf.name}\n"]
    with fitz.open(pdf) as doc:
        for n in parse_pages(pages, doc.page_count):
            page = doc[n - 1]
            text = page.get_text().strip()
            infos.append(PageInfo(n, len(text), len(page.get_images())))
            chunks.append(f"\n## Page {n}\n\n{text or '_(no text - image only)_'}\n")
    out.write_text("".join(chunks), encoding="utf-8")
    return infos


def render_pages(pdf: Path, out_dir: Path, pages: str, dpi: int = 100) -> list[Path]:
    """Save the chosen pages as PNGs, for charts that text can't capture."""
    paths = []
    with fitz.open(pdf) as doc:
        for n in parse_pages(pages, doc.page_count):
            path = out_dir / f"{pdf.stem}-p{n:02d}.png"
            doc[n - 1].get_pixmap(dpi=dpi).save(path)
            paths.append(path)
    return paths
