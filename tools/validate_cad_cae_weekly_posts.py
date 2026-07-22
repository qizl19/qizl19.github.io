from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


CATEGORY_URL = "/categories/CAD-CAE%E7%94%9F%E6%80%81%E5%91%A8%E6%8A%A5/"
TAG_URL = "/tags/CAD-CAE/"


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the CAD/CAE weekly blog column.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.root.resolve()
    posts = json.loads((root / "data" / "cad_cae_weekly_posts.json").read_text(encoding="utf-8"))
    aircraft = json.loads((root / "data" / "aircraft_posts.json").read_text(encoding="utf-8"))
    aeroengine_path = root / "data" / "aeroengine_posts.json"
    aeroengine = (
        json.loads(aeroengine_path.read_text(encoding="utf-8"))
        if aeroengine_path.is_file()
        else []
    )
    latest_post_date = max(
        item.get("updated") or item["date"] for item in posts + aircraft + aeroengine
    )
    expected_last_push = f'data-lastPushDate="{latest_post_date}T01:00:00.000Z"'
    errors: list[str] = []

    if not posts:
        errors.append("CAD/CAE weekly metadata is empty")
    cover = root / "images" / "cad-cae-weekly-cover-v2.webp"
    if not cover.is_file():
        errors.append("Missing CAD/CAE weekly cover")

    for post in posts:
        source = root / post["contentFile"]
        page = root / "p" / f"{post['postId']}.html"
        if not source.is_file():
            errors.append(f"Missing article source: {source}")
            continue
        if not page.is_file():
            errors.append(f"Missing generated article: {page}")
            continue
        content = page.read_text(encoding="utf-8")
        for required in [post["title"], post["subtitle"], "执行摘要", "本周最优先的 3 项行动", "本周态势总览", "决策与监控清单"]:
            if required not in content:
                errors.append(f"Missing {required} in {page.name}")
        if f'href="{CATEGORY_URL}"' not in content or f'href="{TAG_URL}"' not in content:
            errors.append(f"Missing weekly taxonomy links in {page.name}")
        if len(re.findall(r'class="toc-item toc-level-2"', content)) != len(post["headings"]):
            errors.append(f"TOC count mismatch in {page.name}")
        for forbidden in ["全文转写", "PDF 下载", "application/pdf", "<iframe"]:
            if forbidden in content:
                errors.append(f"Forbidden PDF-style content {forbidden} in {page.name}")

    checks = {
        root / "index.html": ["category-aircraft", "category-cad-cae", CATEGORY_URL, "/p/44bc590d.html"],
        root / "categories" / "index.html": ["CAD/CAE 生态周报", CATEGORY_URL],
        root / "categories" / "CAD-CAE生态周报" / "index.html": ["CAD/CAE 生态周报", "/p/44bc590d.html"],
        root / "tags" / "CAD-CAE" / "index.html": ["CAD/CAE", "/p/44bc590d.html"],
        root / "archives" / "index.html": ["CAD/CAE 生态周报｜2026-07-13"],
        root / "search.xml": ["CAD/CAE 生态周报｜2026-07-13", "FreeCAD Assembly"],
        root / "css" / "index.css": ["/p/eacebbb9/y20-000.jpg", "/images/cad-cae-weekly-cover-v2.webp"],
    }
    for path, needles in checks.items():
        if not path.is_file():
            errors.append(f"Missing required page: {path}")
            continue
        content = path.read_text(encoding="utf-8")
        for needle in needles:
            if needle not in content:
                errors.append(f"Missing {needle} in {path}")

    for path in root.rglob("*.html"):
        if ".git" in path.parts or "tmp" in path.parts:
            continue
        content = path.read_text(encoding="utf-8")
        if 'id="last-push-date"' in content and expected_last_push not in content:
            errors.append(f"Last update date is stale in {path}")

    copied_pdfs = [path for path in root.rglob("*.pdf") if ".git" not in path.parts and "tmp" not in path.parts]
    if copied_pdfs:
        errors.append("PDF files were copied into the permanent website: " + ", ".join(str(path) for path in copied_pdfs))

    if errors:
        print("Validation failed:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print(f"Validation passed: {len(posts)} CAD/CAE weekly article(s), HTML-only column, local category covers")


if __name__ == "__main__":
    main()
