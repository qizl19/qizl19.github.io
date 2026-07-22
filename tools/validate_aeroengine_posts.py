from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


CATEGORY_URL = "/categories/%E8%88%AA%E7%A9%BA%E5%8F%91%E5%8A%A8%E6%9C%BA/"
TAG_URL = "/tags/%E8%88%AA%E7%A9%BA%E5%8F%91%E5%8A%A8%E6%9C%BA/"
REQUIRED_SECTIONS = [
    "本期问题与学习目标",
    "核心结论",
    "站位与总参数",
    "Brayton 循环的物理直觉",
    "必要公式与适用假设",
    "可复算的简化算例",
    "设计与分析的执行步骤",
    "常见误区与失效边界",
    "与整机、控制及其他部件的耦合",
    "自测题",
    "答案与下一期衔接",
    "参考资料与图示许可",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate aeroengine briefing posts.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.root.resolve()
    data_path = root / "data" / "aeroengine_posts.json"
    errors: list[str] = []

    if not data_path.is_file():
        raise SystemExit("Missing data/aeroengine_posts.json")
    posts = json.loads(data_path.read_text(encoding="utf-8"))
    if not posts:
        errors.append("Aeroengine briefing metadata is empty")

    issue_numbers = [post.get("issue") for post in posts]
    if len(issue_numbers) != len(set(issue_numbers)):
        errors.append("Duplicate issue number")
    if len({post.get("slug") for post in posts}) != len(posts):
        errors.append("Duplicate slug")
    if len({post.get("postId") for post in posts}) != len(posts):
        errors.append("Duplicate postId")

    for post in posts:
        source = root / post["contentFile"]
        page = root / "p" / f"{post['postId']}.html"
        if not source.is_file():
            errors.append(f"Missing article source: {source}")
            continue
        source_html = source.read_text(encoding="utf-8")
        plain = re.sub(r"<[^>]+>", " ", source_html)
        cjk_count = len(re.findall(r"[\u4e00-\u9fff]", plain))
        if not 2500 <= cjk_count <= 4500:
            errors.append(f"Chinese character count out of range in {source.name}: {cjk_count}")
        if len(re.findall(r"<li>", source_html)) < 20:
            errors.append(f"Insufficient structured steps/tests in {source.name}")
        if len(re.findall(r"<h2 id=", source_html)) != len(post["headings"]):
            errors.append(f"Source heading count mismatch in {source.name}")
        for required in REQUIRED_SECTIONS:
            if required not in source_html:
                errors.append(f"Missing section {required} in {source.name}")
        for formula in ["Tt3s", "πc", "轴功平衡", "ηth", "Pt5/Pt0≈3.83"]:
            if formula not in source_html:
                errors.append(f"Missing formula or result {formula} in {source.name}")
        for source_item in post.get("sources", []):
            if source_item["url"] not in source_html:
                errors.append(f"Missing source link in article: {source_item['url']}")
        for figure in post.get("figures", []):
            for key in ["src", "title", "author", "license", "licenseUrl"]:
                if not figure.get(key):
                    errors.append(f"Missing figure provenance {key}: {post['title']}")
            asset = root / figure["src"].lstrip("/")
            if not asset.is_file() or asset.stat().st_size == 0:
                errors.append(f"Missing or empty figure: {asset}")
            if figure["src"] not in source_html or figure["license"] not in source_html:
                errors.append(f"Figure not credited in source: {figure['src']}")

        if not page.is_file():
            errors.append(f"Missing generated page: {page}")
            continue
        content = page.read_text(encoding="utf-8")
        for required in [post["title"], post["subtitle"], *REQUIRED_SECTIONS]:
            if required not in content:
                errors.append(f"Missing {required} in {page.name}")
        if f'href="{CATEGORY_URL}"' not in content or f'href="{TAG_URL}"' not in content:
            errors.append(f"Missing aeroengine taxonomy links in {page.name}")
        if content.count('class="toc-item toc-level-2"') != len(post["headings"]):
            errors.append(f"TOC count mismatch in {page.name}")
        for forbidden in ["/aircraft/", "PDF 全文转写", "application/pdf", "<iframe"]:
            if forbidden in content:
                errors.append(f"Forbidden content {forbidden} in {page.name}")

    newest = posts[0]
    checks = {
        root / "index.html": [newest["title"], "category-aeroengine", CATEGORY_URL],
        root / "categories" / "index.html": ["航空发动机", CATEGORY_URL],
        root / "categories" / "航空发动机" / "index.html": [newest["title"]],
        root / "tags" / "航空发动机" / "index.html": [newest["title"]],
        root / "archives" / "index.html": [newest["title"]],
        root / "search.xml": [newest["title"], "轴功平衡"],
        root / "css" / "index.css": [".category-aeroengine", newest["heroImage"]],
    }
    for path, needles in checks.items():
        if not path.is_file():
            errors.append(f"Missing required page: {path}")
            continue
        content = path.read_text(encoding="utf-8")
        for needle in needles:
            if needle not in content:
                errors.append(f"Missing {needle} in {path}")

    index = (root / "index.html").read_text(encoding="utf-8")
    for forbidden in ["chart.js@", "mermaid@", "model-viewer@", "aircraft-article.js"]:
        if forbidden in index:
            errors.append(f"Heavy article component leaked into homepage: {forbidden}")

    if errors:
        print("Validation failed:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print(
        f"Validation passed: {len(posts)} aeroengine briefing(s), "
        f"{len(REQUIRED_SECTIONS)} sections, {cjk_count} Chinese characters"
    )


if __name__ == "__main__":
    main()
