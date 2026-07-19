from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_SECTIONS = [
    "基本资料",
    "研制背景与时间线",
    "总体布局与设计特点",
    "动力系统",
    "主要型号与改型",
    "优势与局限",
    "参考资料与图片许可",
]
REMOVED_POSTS = {
    "330e82f5": "直升机，不是直升飞机",
    "4a17b156": "Hello World",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate aircraft posts in the Butterfly blog output.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.root.resolve()
    profiles = json.loads((root / "data" / "aircraft_posts.json").read_text(encoding="utf-8"))
    errors: list[str] = []

    if (root / "aircraft").exists():
        errors.append("Independent /aircraft directory still exists")
    for post_id, title in REMOVED_POSTS.items():
        if (root / "p" / f"{post_id}.html").exists():
            errors.append(f"Removed article still exists: {title}")
    for obsolete in [
        "build_aircraft_site.py",
        "extract_aircraft_pdfs.py",
        "import_aircraft_data.mjs",
        "link_aircraft_archive.py",
        "screenshot_aircraft_site.cjs",
        "validate_aircraft_site.py",
    ]:
        if (root / "tools" / obsolete).exists():
            errors.append(f"Obsolete archive tool still exists: {obsolete}")

    for profile in profiles:
        page = root / "p" / f"{profile['postId']}.html"
        if not page.is_file():
            errors.append(f"Missing article: {profile['nameZh']}")
            continue
        content = page.read_text(encoding="utf-8")
        for required in [profile["nameZh"], profile["nameEn"], *REQUIRED_SECTIONS]:
            if required not in content:
                errors.append(f"Missing {required} in {page.name}")
        for forbidden in ["PDF 全文转写", "全文转写", 'href="/aircraft/"', "/aircraft/assets/"]:
            if forbidden in content:
                errors.append(f"Forbidden archive content {forbidden} in {page.name}")
        if 'href="/categories/%E9%A3%9E%E6%9C%BA%E8%B5%84%E6%96%99%E6%95%B4%E7%90%86/"' not in content:
            errors.append(f"Missing category link in {page.name}")
        for photo in profile["photos"]:
            source = root / photo["src"].lstrip("/")
            if not source.is_file():
                errors.append(f"Missing photo {source}")
            if photo["sourceUrl"] not in content or photo["licenseUrl"] not in content:
                errors.append(f"Missing photo credit links in {page.name}: {source.name}")

    checks = {
        root / "index.html": [profile["nameZh"] for profile in profiles],
        root / "categories" / "飞机资料整理" / "index.html": [profile["nameZh"] for profile in profiles],
        root / "archives" / "index.html": [profile["nameZh"] for profile in profiles],
        root / "tags" / "航空" / "index.html": [profile["nameZh"] for profile in profiles],
        root / "search.xml": [profile["nameZh"] for profile in profiles],
    }
    for path, titles in checks.items():
        content = path.read_text(encoding="utf-8")
        for title in titles:
            if title not in content:
                errors.append(f"Missing listing {title} in {path}")
        if "飞机资料库" in content or 'href="/aircraft/"' in content:
            errors.append(f"Independent archive link remains in {path}")

    for path in root.rglob("*.html"):
        if ".git" in path.parts:
            continue
        content = path.read_text(encoding="utf-8")
        if 'href="/aircraft/"' in content:
            errors.append(f"Independent archive navigation remains in {path}")
        for post_id, title in REMOVED_POSTS.items():
            if f'/p/{post_id}.html' in content or title in content:
                errors.append(f"Removed article reference remains in {path}: {title}")

    search = (root / "search.xml").read_text(encoding="utf-8")
    for post_id, title in REMOVED_POSTS.items():
        if f'/p/{post_id}.html' in search or title in search:
            errors.append(f"Removed article remains in search.xml: {title}")

    expected_listing_counts = {
        root / "archives" / "index.html": 7,
        root / "archives" / "2022" / "index.html": 2,
        root / "archives" / "2022" / "03" / "index.html": 1,
        root / "archives" / "2022" / "01" / "index.html": 1,
        root / "categories" / "飞机资料整理" / "index.html": 5,
        root / "tags" / "航空" / "index.html": 5,
    }
    for path, expected in expected_listing_counts.items():
        actual = path.read_text(encoding="utf-8").count('<div class="article-sort-item"><a')
        if actual != expected:
            errors.append(f"Listing count mismatch in {path}: expected {expected}, got {actual}")

    homepage = (root / "index.html").read_text(encoding="utf-8")
    home_cards = homepage.count('<div class="recent-post-item"><div class="post_cover')
    if home_cards != 7:
        errors.append(f"Homepage article count mismatch: expected 7, got {home_cards}")

    if errors:
        print("Validation failed:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print(f"Validation passed: {len(profiles)} independent aircraft articles, no /aircraft archive")


if __name__ == "__main__":
    main()
