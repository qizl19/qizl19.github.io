from __future__ import annotations

import argparse
import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path


class AssetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.assets: list[tuple[str, str]] = []
        self.ids: list[str] = []
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag in {"a", "link"} and values.get("href"):
            self.assets.append(("href", values["href"] or ""))
        if tag in {"img", "script"} and values.get("src"):
            self.assets.append(("src", values["src"] or ""))
        if values.get("id"):
            self.ids.append(values["id"] or "")
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest().upper()


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the static aircraft archive.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.root.resolve()
    aircraft_root = root / "aircraft"
    profiles = json.loads((aircraft_root / "data" / "aircraft.json").read_text("utf-8"))
    errors: list[str] = []

    slugs = [item["slug"] for item in profiles]
    if len(slugs) != len(set(slugs)):
        errors.append("Aircraft slugs are not unique")
    if not profiles:
        errors.append("No aircraft profiles found")

    html_paths = [aircraft_root / "index.html"] + [
        aircraft_root / slug / "index.html" for slug in slugs
    ]
    for path in html_paths:
        if not path.is_file():
            errors.append(f"Missing HTML: {path}")
            continue
        content = path.read_text(encoding="utf-8")
        parsed = AssetParser()
        parsed.feed(content)
        if not parsed.title.strip():
            errors.append(f"Missing title: {path}")
        if len(parsed.ids) != len(set(parsed.ids)):
            errors.append(f"Duplicate ids: {path}")
        if "file://" in content or "C:\\Users\\" in content:
            errors.append(f"Local path leaked into HTML: {path}")
        for attr, value in parsed.assets:
            if not value.startswith("/") or value.startswith("//"):
                continue
            clean = value.split("#", 1)[0].split("?", 1)[0]
            target = root / clean.removeprefix("/")
            if clean.endswith("/"):
                target /= "index.html"
            if clean and not target.exists():
                errors.append(f"Broken local {attr} {value} in {path}")

    for profile in profiles:
        slug = profile["slug"]
        transcript_path = aircraft_root / "data" / "transcripts" / f"{slug}.json"
        if not transcript_path.is_file():
            errors.append(f"Missing transcript: {slug}")
            continue
        transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
        if transcript.get("pageCount", 0) < 1:
            errors.append(f"Empty transcript: {slug}")
        if len(transcript.get("pages", [])) != transcript.get("pageCount"):
            errors.append(f"Transcript page mismatch: {slug}")
        if any(len(page.get("text", "")) < 100 for page in transcript.get("pages", [])):
            errors.append(f"Suspiciously short transcript page: {slug}")
        pdf_path = root / profile["pdf"].removeprefix("/")
        if not pdf_path.is_file():
            errors.append(f"Missing PDF: {slug}")
        elif digest(pdf_path) != transcript.get("sha256"):
            errors.append(f"PDF digest mismatch: {slug}")
        if not profile.get("photos") or any(
            not photo.get("sourceUrl")
            or not photo.get("license")
            or not photo.get("licenseUrl")
            for photo in profile.get("photos", [])
        ):
            errors.append(f"Incomplete photo licensing: {slug}")
        detail = (aircraft_root / slug / "index.html").read_text(encoding="utf-8")
        if detail.count('class="transcript-page"') != transcript["pageCount"]:
            errors.append(f"Rendered transcript page mismatch: {slug}")
        for required in [profile["nameZh"], profile["nameEn"], "PDF 全文转写", "真实照片与许可"]:
            if required not in detail:
                errors.append(f"Missing detail content {required}: {slug}")

    homepage = (root / "index.html").read_text(encoding="utf-8")
    if 'href="/aircraft/"' not in homepage:
        errors.append("Blog homepage does not link to /aircraft/")

    if errors:
        print("Validation failed:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print(
        f"Validation passed: {len(profiles)} profiles, {len(html_paths)} HTML pages, "
        f"{sum(json.loads((aircraft_root / 'data' / 'transcripts' / f'{slug}.json').read_text('utf-8'))['pageCount'] for slug in slugs)} transcript pages"
    )


if __name__ == "__main__":
    main()
