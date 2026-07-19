from __future__ import annotations

import argparse
import html
import json
from datetime import date
from pathlib import Path
from urllib.parse import urlparse


SITE_URL = "https://qizl19.github.io"


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def format_date(value: str) -> str:
    year, month, day = value.split("-")
    return f"{year} 年 {int(month)} 月 {int(day)} 日"


def profile_url(profile: dict) -> str:
    return f"/aircraft/{profile['slug']}/"


def render_head(
    title: str,
    description: str,
    canonical_path: str,
    image: str,
    structured_data: dict,
) -> str:
    full_title = f"{title}｜飞机资料库｜Qzl's Blog"
    canonical = f"{SITE_URL}{canonical_path}"
    image_url = image if image.startswith("http") else f"{SITE_URL}{image}"
    schema = json.dumps(structured_data, ensure_ascii=False, separators=(",", ":"))
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(full_title)}</title>
  <meta name="description" content="{esc(description)}">
  <meta name="theme-color" content="#0b2740">
  <link rel="canonical" href="{canonical}">
  <link rel="icon" href="/img/bitbug_favicon.ico">
  <link rel="stylesheet" href="/aircraft/assets/css/aircraft.css">
  <meta property="og:type" content="website">
  <meta property="og:locale" content="zh_CN">
  <meta property="og:site_name" content="Qzl's Blog">
  <meta property="og:title" content="{esc(full_title)}">
  <meta property="og:description" content="{esc(description)}">
  <meta property="og:url" content="{canonical}">
  <meta property="og:image" content="{esc(image_url)}">
  <meta name="twitter:card" content="summary_large_image">
  <script type="application/ld+json">{schema}</script>
</head>"""


def site_header() -> str:
    return """<header class="site-header">
  <a class="brand" href="/aircraft/" aria-label="飞机资料库首页">
    <span class="brand-mark" aria-hidden="true">✦</span>
    <span><strong>飞机资料库</strong><small>Aircraft Dossiers</small></span>
  </a>
  <nav aria-label="主导航">
    <a href="/">博客首页</a>
    <a href="/aircraft/">全部档案</a>
  </nav>
</header>"""


def site_footer() -> str:
    return """<footer class="site-footer">
  <div><strong>飞机资料库</strong><p>公开资料整理、交叉核验、来源可追溯。</p></div>
  <div class="footer-links"><a href="/">Qzl's Blog</a><a href="/aircraft/">全部档案</a><a href="https://github.com/qizl19" rel="noopener">GitHub</a></div>
</footer>
<script src="/aircraft/assets/js/aircraft.js" defer></script>"""


def tags(profile: dict) -> str:
    values = [profile["nation"], profile["category"], *profile["tags"]]
    return "".join(f'<span class="tag">{esc(item)}</span>' for item in values)


def render_card(profile: dict, compact: bool = False) -> str:
    card_class = "aircraft-card compact" if compact else "aircraft-card"
    search_text = " ".join(
        [
            profile["nameZh"],
            profile["nameEn"],
            profile["nation"],
            profile["category"],
            profile["era"],
            *profile["tags"],
        ]
    ).lower()
    fact_items = "".join(
        f'<li><span>{esc(item["label"])}</span><strong>{esc(item["value"])}</strong></li>'
        for item in profile["facts"][:3]
    )
    return f"""<article class="{card_class}" data-aircraft-card data-search="{esc(search_text)}" data-nation="{esc(profile['nation'])}" data-category="{esc(profile['category'])}">
  <a class="card-image" href="{profile_url(profile)}" aria-label="阅读{esc(profile['nameZh'])}资料">
    <img src="{esc(profile['heroImage'])}" alt="{esc(profile['nameZh'])}完整飞机外观" loading="lazy">
    <span>{esc(profile['date'])}</span>
  </a>
  <div class="card-body">
    <div class="tag-row">{tags(profile)}</div>
    <h2><a href="{profile_url(profile)}">{esc(profile['nameZh'])}</a></h2>
    <p class="english-name">{esc(profile['nameEn'])}</p>
    <p class="card-subtitle">{esc(profile['subtitle'])}</p>
    <ul class="mini-facts">{fact_items}</ul>
    <a class="text-link" href="{profile_url(profile)}">打开完整档案 <span aria-hidden="true">→</span></a>
  </div>
</article>"""


def render_index(profiles: list[dict], transcripts: dict[str, dict]) -> str:
    latest = profiles[0]
    total_pages = sum(item["pageCount"] for item in transcripts.values())
    total_links = len(
        {
            link
            for item in transcripts.values()
            for link in item.get("embeddedLinks", [])
        }
    )
    nations = sorted({profile["nation"] for profile in profiles})
    categories = sorted({profile["category"] for profile in profiles})
    nation_options = "".join(f'<option value="{esc(item)}">{esc(item)}</option>' for item in nations)
    category_options = "".join(
        f'<option value="{esc(item)}">{esc(item)}</option>' for item in categories
    )
    cards = "\n".join(render_card(profile) for profile in profiles)
    description = "每两日更新的中文飞机资料库，包含机型时间线、设计特点、性能参数、真实照片、许可与可点击来源。"
    schema = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": "飞机资料库",
        "url": f"{SITE_URL}/aircraft/",
        "description": description,
        "hasPart": [
            {
                "@type": "Article",
                "headline": f"{item['nameZh']}（{item['nameEn']}）",
                "url": f"{SITE_URL}{profile_url(item)}",
                "datePublished": item["date"],
            }
            for item in profiles
        ],
    }
    return f"""{render_head('飞机资料库', description, '/aircraft/', latest['heroImage'], schema)}
<body class="archive-page">
{site_header()}
<main>
  <section class="archive-hero">
    <div class="hero-copy">
      <p class="eyebrow">Qzl's Blog · 每两日更新</p>
      <h1>把一架飞机，<br><em>讲清楚。</em></h1>
      <p class="hero-lead">从研制背景、总体布局到动力、参数与运营历史。每期资料均保留原始来源、图片许可和 PDF 全文转写。</p>
      <div class="hero-actions"><a class="button primary" href="{profile_url(latest)}">阅读最新一期</a><a class="button ghost" href="#archive">浏览全部档案</a></div>
    </div>
    <figure class="featured-aircraft">
      <img src="{esc(latest['heroImage'])}" alt="{esc(latest['nameZh'])}飞行中的完整外观">
      <figcaption><span>最新档案 · {esc(latest['date'])}</span><strong>{esc(latest['nameZh'])}</strong><small>{esc(latest['nameEn'])}</small></figcaption>
    </figure>
  </section>

  <section class="archive-stats" aria-label="资料库统计">
    <div><strong>{len(profiles):02d}</strong><span>机型档案</span></div>
    <div><strong>{total_pages}</strong><span>PDF 原文页</span></div>
    <div><strong>{total_links}</strong><span>原始资料链接</span></div>
    <div><strong>2 天</strong><span>更新周期</span></div>
  </section>

  <section class="archive-section" id="archive">
    <div class="section-heading"><div><p class="eyebrow">Archive</p><h2>全部飞机档案</h2></div><p>当前显示 <strong id="result-count">{len(profiles)}</strong> 份资料</p></div>
    <form class="filters" id="aircraft-filters" role="search">
      <label><span>搜索</span><input id="aircraft-search" type="search" placeholder="机型、国家、用途或年代" autocomplete="off"></label>
      <label><span>国家 / 地区</span><select id="nation-filter"><option value="">全部</option>{nation_options}</select></label>
      <label><span>用途</span><select id="category-filter"><option value="">全部</option>{category_options}</select></label>
      <button class="filter-reset" type="reset">清除筛选</button>
    </form>
    <div class="aircraft-grid" id="aircraft-grid">{cards}</div>
    <p class="empty-state" id="empty-state" hidden>没有符合条件的档案，请换一个关键词。</p>
  </section>

  <section class="method-section">
    <div><p class="eyebrow">Editorial standard</p><h2>资料不是堆砌，<br>而是可核查的叙述。</h2></div>
    <ol>
      <li><span>01</span><div><strong>优先一手来源</strong><p>制造商、航空管理机构、博物馆、军方和事故调查机构。</p></div></li>
      <li><span>02</span><div><strong>关键数据交叉核验</strong><p>不同型号、批次和统计口径明确区分，不制造“唯一标准值”。</p></div></li>
      <li><span>03</span><div><strong>图片许可逐张记录</strong><p>照片作者、原始页面、许可状态与许可链接都可追溯。</p></div></li>
    </ol>
  </section>
</main>
{site_footer()}
</body>
</html>
"""


def render_detail(profile: dict, transcript: dict, profiles: list[dict]) -> str:
    facts = "".join(
        f'<div><span>{esc(item["label"])}</span><strong>{esc(item["value"])}</strong>'
        + (f'<small>{esc(item["note"])}</small>' if item.get("note") else "")
        + "</div>"
        for item in profile["facts"]
    )
    timeline = "".join(
        f'<li><time>{esc(item["year"])}</time><p>{esc(item["event"])}</p></li>'
        for item in profile["timeline"]
    )
    design = "".join(
        f'<li><span>{index:02d}</span><p>{esc(item)}</p></li>'
        for index, item in enumerate(profile["designPoints"], start=1)
    )
    variants = "".join(
        f'<tr><th scope="row">{esc(item["name"])}</th><td>{esc(item["description"])}</td></tr>'
        for item in profile["variants"]
    )
    strengths = "".join(f"<li>{esc(item)}</li>" for item in profile["strengths"])
    limits = "".join(f"<li>{esc(item)}</li>" for item in profile["limits"])
    photos = "".join(
        f"""<figure class="photo-card">
  <a href="{esc(photo['sourceUrl'])}" rel="noopener"><img src="{esc(photo['src'])}" alt="{esc(photo['alt'])}" loading="lazy"></a>
  <figcaption><strong>{esc(photo['caption'])}</strong><span>摄影 / 作者：{esc(photo['credit'])}</span><span><a href="{esc(photo['sourceUrl'])}" rel="noopener">原始来源</a> · <a href="{esc(photo['licenseUrl'])}" rel="license noopener">{esc(photo['license'])}</a></span></figcaption>
</figure>"""
        for photo in profile["photos"]
    )
    sources = "".join(
        f'<li><a href="{esc(item["url"])}" rel="noopener">{esc(item["label"])}</a><span>{esc(urlparse(item["url"]).netloc)}</span></li>'
        for item in profile["sources"]
    )
    transcript_pages = []
    for page in transcript["pages"]:
        page_links = ""
        if page["links"]:
            items = "".join(
                f'<li><a href="{esc(link)}" rel="noopener">{esc(urlparse(link).netloc or link)}</a></li>'
                for link in page["links"]
            )
            page_links = f'<div class="page-links"><strong>本页嵌入链接</strong><ul>{items}</ul></div>'
        transcript_pages.append(
            f'<section class="transcript-page"><h3>第 {page["number"]} 页</h3><div class="transcript-copy">{esc(page["text"])}</div>{page_links}</section>'
        )
    related = "".join(render_card(item, compact=True) for item in profiles if item["slug"] != profile["slug"])
    description = profile["summary"]
    schema = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": f"{profile['nameZh']}（{profile['nameEn']}）飞机资料卡",
        "description": description,
        "image": f"{SITE_URL}{profile['heroImage']}",
        "datePublished": profile["date"],
        "dateModified": profile["date"],
        "inLanguage": "zh-CN",
        "author": {"@type": "Person", "name": "Qzl"},
        "publisher": {"@type": "Person", "name": "Qzl"},
        "mainEntityOfPage": f"{SITE_URL}{profile_url(profile)}",
    }
    return f"""{render_head(profile['nameZh'], description, profile_url(profile), profile['heroImage'], schema)}
<body class="detail-page" style="--accent:{esc(profile['accent'])}">
{site_header()}
<main>
  <section class="detail-hero">
    <div class="detail-hero-copy">
      <a class="back-link" href="/aircraft/">← 返回全部档案</a>
      <p class="eyebrow">{esc(profile['eyebrow'])} · {esc(format_date(profile['date']))}</p>
      <h1>{esc(profile['nameZh'])}</h1>
      <p class="detail-english">{esc(profile['nameEn'])}</p>
      <p class="detail-subtitle">{esc(profile['subtitle'])}</p>
      <div class="tag-row">{tags(profile)}</div>
      <div class="hero-actions"><a class="button primary" href="{esc(profile['pdf'])}">下载原始 PDF</a><a class="button ghost" href="#transcript">阅读全文转写</a></div>
    </div>
    <figure><img src="{esc(profile['heroImage'])}" alt="{esc(profile['nameZh'])}完整飞机外观"><figcaption>{esc(profile['photos'][0]['caption'])} 摄影 / 作者：{esc(profile['photos'][0]['credit'])}。</figcaption></figure>
  </section>

  <div class="detail-layout">
    <aside class="contents"><strong>本期目录</strong><nav><a href="#overview">执行摘要</a><a href="#timeline">研制时间线</a><a href="#design">设计特点</a><a href="#power">动力系统</a><a href="#variants">主要改型</a><a href="#assessment">优势与局限</a><a href="#gallery">图片与许可</a><a href="#sources">参考资料</a><a href="#transcript">PDF 全文</a></nav></aside>
    <article class="dossier">
      <section id="overview" class="dossier-section lead-section"><p class="section-kicker">Executive summary</p><h2>执行摘要</h2><p class="standfirst">{esc(profile['summary'])}</p><blockquote>{esc(profile['statement'])}</blockquote><div class="fact-grid">{facts}</div></section>
      <section id="timeline" class="dossier-section"><p class="section-kicker">Development</p><h2>研制背景与时间线</h2><ol class="timeline">{timeline}</ol></section>
      <section id="design" class="dossier-section"><p class="section-kicker">Configuration</p><h2>总体布局与设计特点</h2><ol class="design-list">{design}</ol></section>
      <section id="power" class="dossier-section"><p class="section-kicker">Propulsion</p><h2>动力系统</h2><p>{esc(profile['power'])}</p></section>
      <section id="variants" class="dossier-section"><p class="section-kicker">Variants</p><h2>主要型号与改型</h2><div class="table-wrap"><table><thead><tr><th>型号 / 口径</th><th>定位与说明</th></tr></thead><tbody>{variants}</tbody></table></div></section>
      <section id="assessment" class="dossier-section"><p class="section-kicker">Assessment</p><h2>优势与局限</h2><div class="assessment-grid"><div class="positive"><h3>优势</h3><ul>{strengths}</ul></div><div class="caution"><h3>局限 / 公开不足</h3><ul>{limits}</ul></div></div></section>
      <section id="gallery" class="dossier-section wide-section"><p class="section-kicker">Photography</p><h2>真实照片与许可</h2><p class="section-note">所有图片均保留作者、原始来源与许可链接；点击照片可查看原始页面。</p><div class="photo-grid">{photos}</div></section>
      <section id="sources" class="dossier-section"><p class="section-kicker">References</p><h2>主要参考资料</h2><ol class="source-list">{sources}</ol><p class="source-note">PDF 中另含 {len(transcript['embeddedLinks'])} 个可点击原始链接，已在下方全文转写中按页保留。</p></section>
      <section id="transcript" class="dossier-section wide-section transcript-section"><p class="section-kicker">Full transcript</p><h2>PDF 全文转写</h2><p class="section-note">以下文字由原始 {transcript['pageCount']} 页 PDF 提取，并逐页保留。表格内容可能因 PDF 阅读顺序呈线性排列；参数口径与脚注以原 PDF 为准。</p><div class="transcript-meta"><span>页数 <strong>{transcript['pageCount']}</strong></span><span>SHA256 <code>{esc(transcript['sha256'])}</code></span><a href="{esc(profile['pdf'])}">打开排版原稿</a></div>{''.join(transcript_pages)}</section>
    </article>
  </div>
  <section class="related-section"><div class="section-heading"><div><p class="eyebrow">Continue reading</p><h2>继续浏览</h2></div><a class="text-link" href="/aircraft/">查看全部 →</a></div><div class="related-grid">{related}</div></section>
</main>
{site_footer()}
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the static aircraft archive.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.root.resolve()
    aircraft_root = root / "aircraft"
    profiles = read_json(aircraft_root / "data" / "aircraft.json")
    transcripts = {
        profile["slug"]: read_json(
            aircraft_root / "data" / "transcripts" / f"{profile['slug']}.json"
        )
        for profile in profiles
    }

    write(aircraft_root / "index.html", render_index(profiles, transcripts))
    for profile in profiles:
        write(
            aircraft_root / profile["slug"] / "index.html",
            render_detail(profile, transcripts[profile["slug"]], profiles),
        )

    urls = [f"{SITE_URL}/aircraft/"] + [
        f"{SITE_URL}{profile_url(profile)}" for profile in profiles
    ]
    sitemap = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">\n"
    sitemap += "\n".join(f"  <url><loc>{esc(item)}</loc></url>" for item in urls)
    sitemap += "\n</urlset>\n"
    write(aircraft_root / "sitemap.xml", sitemap)
    print(f"Built aircraft archive with {len(profiles)} profiles")


if __name__ == "__main__":
    main()
