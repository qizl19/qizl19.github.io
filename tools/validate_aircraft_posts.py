from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path


REQUIRED_SECTIONS = [
    "基本资料",
    "研制背景与时间线",
    "总体布局与设计特点",
    "动力系统",
    "主要型号与改型",
    "优势与局限",
    "三维外形示意",
    "飞机参数对比",
    "尺寸图表",
    "工程关系图",
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
    weekly_posts = json.loads(
        (root / "data" / "cad_cae_weekly_posts.json").read_text(encoding="utf-8")
    )
    aeroengine_path = root / "data" / "aeroengine_posts.json"
    aeroengine_posts = (
        json.loads(aeroengine_path.read_text(encoding="utf-8"))
        if aeroengine_path.is_file()
        else []
    )
    expected_total_posts = len(profiles) + len(weekly_posts) + len(aeroengine_posts) + 2
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
        for key in ["updated", "metrics", "diagram", "model"]:
            if key not in profile:
                errors.append(f"Missing aircraft widget data {key}: {profile['nameZh']}")
        widget_needles = [
            'data-aircraft-model',
            'data-aircraft-comparison',
            'data-aircraft-chart',
            'data-aircraft-mermaid',
            '<script defer src="/js/aircraft-article.js"></script>',
            '点击后下载 GLB',
            '进入视口后加载',
            '进入视口后渲染',
            'aircraft-chart-fallback',
            'aircraft-mermaid-fallback',
            '非工程模型',
        ]
        for needle in widget_needles:
            if needle not in content and not (needle == "非工程模型" and "不可用于工程分析" in content):
                errors.append(f"Missing aircraft widget marker {needle} in {page.name}")
        if content.count('<script defer src="/js/aircraft-article.js"></script>') != 1:
            errors.append(f"Aircraft widget script count must be one in {page.name}")
        model = profile.get("model", {})
        if model:
            model_path = root / model["src"].lstrip("/")
            if not model_path.is_file():
                errors.append(f"Missing GLB model: {model_path}")
            else:
                if model_path.stat().st_size > 5 * 1024 * 1024:
                    errors.append(f"GLB exceeds 5 MiB target: {model_path}")
                raw = model_path.read_bytes()
                if len(raw) < 20 or raw[:4] != b"glTF":
                    errors.append(f"Invalid GLB header: {model_path}")
                else:
                    _, version, length = struct.unpack_from("<4sII", raw, 0)
                    if version != 2 or length != len(raw):
                        errors.append(f"Invalid GLB version or length: {model_path}")
            for field in ["author", "sourceUrl", "license", "licenseUrl", "note"]:
                if not model.get(field):
                    errors.append(f"Missing model credit {field}: {profile['nameZh']}")
                elif field in {"sourceUrl", "licenseUrl"} and model[field] not in content:
                    errors.append(f"Missing model credit link {field} in {page.name}")
            if model.get("kind") == "triposg-image-reconstruction":
                for field in ["inputImage", "inputCredit", "inputSourceUrl", "engine", "engineUrl", "engineLicense"]:
                    if not model.get(field):
                        errors.append(f"Missing TripoSG provenance {field}: {profile['nameZh']}")
                input_image = root / model.get("inputImage", "").lstrip("/")
                if not input_image.is_file():
                    errors.append(f"Missing TripoSG input image: {input_image}")
                for field in ["inputSourceUrl", "engineUrl"]:
                    if model.get(field) and model[field] not in content:
                        errors.append(f"Missing TripoSG credit link {field} in {page.name}")
                if model.get("engine") != "TripoSG":
                    errors.append(f"Unexpected reconstruction engine: {profile['nameZh']}")
                if model.get("engineUrl") != "https://github.com/VAST-AI-Research/TripoSG":
                    errors.append(f"Unexpected TripoSG source URL: {profile['nameZh']}")
                if model.get("engineLicense") != "MIT":
                    errors.append(f"Unexpected TripoSG license: {profile['nameZh']}")
                expected_sha = model.get("outputSha256")
                if not expected_sha:
                    errors.append(f"Missing TripoSG output SHA-256: {profile['nameZh']}")
                elif model_path.is_file():
                    actual_sha = hashlib.sha256(model_path.read_bytes()).hexdigest()
                    if actual_sha != expected_sha:
                        errors.append(f"TripoSG output SHA-256 mismatch: {model_path}")
                generation = model.get("generation", {})
                required_settings = {
                    "steps": 40,
                    "seed": 42,
                    "guidanceScale": 7.0,
                    "denseDepth": 8,
                    "hierarchicalDepth": 9,
                    "targetFaces": 80000,
                    "flashDecoder": False,
                }
                for key, expected in required_settings.items():
                    if generation.get(key) != expected:
                        errors.append(
                            f"Unexpected TripoSG setting {key}: {profile['nameZh']}"
                        )
            else:
                errors.append(f"Aircraft model has not migrated to TripoSG: {profile['nameZh']}")

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
        if ".git" in path.parts or "tmp" in path.parts:
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
        root / "archives" / "index.html": expected_total_posts,
        root / "archives" / "2022" / "index.html": 2,
        root / "archives" / "2022" / "03" / "index.html": 1,
        root / "archives" / "2022" / "01" / "index.html": 1,
        # The category and tag also contain the legacy "欧洲直升机" article,
        # which is intentionally not part of aircraft_posts.json.
        root / "categories" / "飞机资料整理" / "index.html": len(profiles) + 1,
        root / "tags" / "航空" / "index.html": len(profiles) + 1,
    }
    for path, expected in expected_listing_counts.items():
        actual = path.read_text(encoding="utf-8").count('<div class="article-sort-item"><a')
        if actual != expected:
            errors.append(f"Listing count mismatch in {path}: expected {expected}, got {actual}")

    homepage = (root / "index.html").read_text(encoding="utf-8")
    home_cards = homepage.count('<div class="recent-post-item"><div class="post_cover')
    if home_cards != expected_total_posts:
        errors.append(
            f"Homepage article count mismatch: expected {expected_total_posts}, got {home_cards}"
        )

    calendar_checks = {
        'id="github-contributions"': 1,
        '<!-- GITHUB_CONTRIBUTIONS_START -->': 1,
        '<!-- GITHUB_CONTRIBUTIONS_END -->': 1,
        'data-user="qizl19"': 1,
        'https://github-contributions-api.jogruber.de/v4/qizl19?y=last': 1,
        '<script defer src="/js/github-contributions.js"></script>': 1,
    }
    for needle, expected in calendar_checks.items():
        actual = homepage.count(needle)
        if actual != expected:
            errors.append(f"GitHub calendar homepage marker mismatch for {needle}: expected {expected}, got {actual}")

    random_checks = {
        'id="random-aircraft"': 1,
        '<!-- RANDOM_AIRCRAFT_START -->': 1,
        '<!-- RANDOM_AIRCRAFT_END -->': 1,
        'class="random-aircraft-button"': 1,
        '<script defer src="/js/random-aircraft.js"></script>': 1,
    }
    for needle, expected in random_checks.items():
        actual = homepage.count(needle)
        if actual != expected:
            errors.append(f"Random aircraft homepage marker mismatch for {needle}: expected {expected}, got {actual}")
    for forbidden in ["aircraft-article.js", "chart.js@", "mermaid@", "model-viewer@", "data-aircraft-model"]:
        if forbidden in homepage:
            errors.append(f"Heavy aircraft widget leaked into homepage: {forbidden}")

    comparison_path = root / "data" / "aircraft-comparison.json"
    if not comparison_path.is_file():
        errors.append("Missing local aircraft comparison JSON")
    else:
        comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
        if {item["slug"] for item in comparison} != {profile["slug"] for profile in profiles}:
            errors.append("Aircraft comparison JSON does not match article data")

    article_script = root / "js" / "aircraft-article.js"
    if not article_script.is_file():
        errors.append("Missing local aircraft article script")
    else:
        script = article_script.read_text(encoding="utf-8")
        for needle in [
            "IntersectionObserver",
            "chart.js@4.5.1",
            "mermaid@11.16.0",
            "@google/model-viewer@4.2.0",
            "prefers-reduced-motion",
            "max-width: 768px",
            "releaseViewer",
            "pagehide",
            "模型加载失败",
            "对比数据加载失败",
            "图表组件加载失败",
            "工程图组件加载失败",
        ]:
            if needle not in script:
                errors.append(f"Aircraft article script is missing {needle}")

    random_script = root / "js" / "random-aircraft.js"
    if not random_script.is_file():
        errors.append("Missing local random aircraft script")
    elif random_script.stat().st_size > 4 * 1024:
        errors.append("Homepage random aircraft script is larger than 4 KiB")

    calendar_script = root / "js" / "github-contributions.js"
    if not calendar_script.is_file():
        errors.append("Missing local GitHub contributions script")
    else:
        script = calendar_script.read_text(encoding="utf-8")
        for needle in ["fetch(card.dataset.api", "AbortController", "REQUEST_TIMEOUT", "暂时无法加载贡献数据", "day.level"]:
            if needle not in script:
                errors.append(f"GitHub contributions script is missing {needle}")

    calendar_css = (root / "css" / "index.css").read_text(encoding="utf-8")
    for needle in [".github-calendar-card", ".github-calendar-grid", '[data-level="4"]', "prefers-reduced-motion"]:
        if needle not in calendar_css:
            errors.append(f"GitHub contributions styles are missing {needle}")

    legacy_calendar_tokens = [
        "gitcalendar.akilar.top",
        "hexo-filter-gitcalendar",
        "/js/githubcalendar.js",
        "<scscrip",
        "GitCalendarInit",
    ]
    for path in root.rglob("*.html"):
        if ".git" in path.parts or "tmp" in path.parts:
            continue
        content = path.read_text(encoding="utf-8")
        for token in legacy_calendar_tokens:
            if token in content:
                errors.append(f"Legacy GitHub calendar token remains in {path}: {token}")
        if path != root / "index.html" and 'id="github-contributions"' in content:
            errors.append(f"GitHub contributions card must only appear on homepage: {path}")
        if path != root / "index.html" and 'id="random-aircraft"' in content:
            errors.append(f"Random aircraft card must only appear on homepage: {path}")

    styles = (root / "css" / "index.css").read_text(encoding="utf-8")
    for needle in [".random-aircraft-card", ".aircraft-model-host model-viewer", ".aircraft-comparison-controls", ".aircraft-chart-stage", ".aircraft-mermaid-output"]:
        if needle not in styles:
            errors.append(f"Aircraft widget styles are missing {needle}")

    if errors:
        print("Validation failed:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print(f"Validation passed: {len(profiles)} independent aircraft articles, no /aircraft archive")


if __name__ == "__main__":
    main()
