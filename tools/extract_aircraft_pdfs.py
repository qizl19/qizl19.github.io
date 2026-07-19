from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

import pdfplumber
from PIL import Image, ImageOps


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract searchable text and embedded links from aircraft PDFs."
    )
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--site-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--render-dir", type=Path)
    parser.add_argument("--pdftoppm", type=Path)
    parser.add_argument("--dpi", type=int, default=100)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def extract_pdf(pdf_path: Path) -> dict:
    pages = []
    all_links = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            text = (page.extract_text(x_tolerance=2, y_tolerance=3) or "").strip()
            links = []
            for item in page.hyperlinks:
                uri = item.get("uri")
                if isinstance(uri, str) and re.match(r"^https?://", uri):
                    if uri not in links:
                        links.append(uri)
                    if uri not in all_links:
                        all_links.append(uri)
            pages.append({"number": page_number, "text": text, "links": links})
    return {
        "pdf": pdf_path.name,
        "pageCount": len(pages),
        "sha256": sha256(pdf_path),
        "embeddedLinks": all_links,
        "pages": pages,
    }


def render_pdf(
    executable: Path, pdf_path: Path, render_root: Path, slug: str, dpi: int
) -> None:
    aircraft_dir = render_root / slug
    aircraft_dir.mkdir(parents=True, exist_ok=True)
    prefix = aircraft_dir / "page"
    subprocess.run(
        [str(executable), "-png", "-r", str(dpi), str(pdf_path), str(prefix)],
        check=True,
    )

    page_paths = sorted(
        aircraft_dir.glob("page-*.png"),
        key=lambda item: int(item.stem.rsplit("-", 1)[1]),
    )
    for sheet_number, offset in enumerate(range(0, len(page_paths), 3), start=1):
        paths = page_paths[offset : offset + 3]
        images = [Image.open(item).convert("RGB") for item in paths]
        max_height = max(image.height for image in images)
        normalized = [
            ImageOps.pad(image, (image.width, max_height), color="white") for image in images
        ]
        width = sum(image.width for image in normalized)
        sheet = Image.new("RGB", (width, max_height), "white")
        x = 0
        for image in normalized:
            sheet.paste(image, (x, 0))
            x += image.width
        sheet.save(aircraft_dir / f"contact-{sheet_number}.png", optimize=True)


def main() -> None:
    args = parse_args()
    profiles = json.loads(args.data.read_text(encoding="utf-8"))
    args.output_dir.mkdir(parents=True, exist_ok=True)

    for profile in profiles:
        relative_pdf = profile["pdf"].removeprefix("/")
        pdf_path = args.site_root / relative_pdf
        if not pdf_path.is_file():
            raise FileNotFoundError(pdf_path)
        result = extract_pdf(pdf_path)
        result.update(
            {
                "slug": profile["slug"],
                "nameZh": profile["nameZh"],
                "nameEn": profile["nameEn"],
                "date": profile["date"],
            }
        )
        output_path = args.output_dir / f"{profile['slug']}.json"
        output_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(
            f"{profile['slug']}: {result['pageCount']} pages, "
            f"{len(result['embeddedLinks'])} embedded links"
        )
        if args.render_dir and args.pdftoppm:
            render_pdf(
                args.pdftoppm,
                pdf_path,
                args.render_dir,
                profile["slug"],
                args.dpi,
            )


if __name__ == "__main__":
    main()
