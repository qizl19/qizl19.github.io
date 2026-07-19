from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import re
import shutil
from pathlib import Path
from urllib.parse import quote


SITE_URL = "https://qizl19.github.io"
CATEGORY_URL = "/categories/%E9%A3%9E%E6%9C%BA%E8%B5%84%E6%96%99%E6%95%B4%E7%90%86/"
TAG_URL = "/tags/%E8%88%AA%E7%A9%BA/"
WEEKLY_CATEGORY = "CAD/CAE 生态周报"
WEEKLY_CATEGORY_URL = "/categories/CAD-CAE%E7%94%9F%E6%80%81%E5%91%A8%E6%8A%A5/"
WEEKLY_TAG = "CAD/CAE"
WEEKLY_TAG_URL = "/tags/CAD-CAE/"
LAZY_PLACEHOLDER = "/img/5-160914192R3.gif"
POST_IDS = {
    "boeing-747": "ebc40a24",
    "de-havilland-mosquito": "fe7680d9",
    "concorde": "6e9a9f42",
    "y-20-kunpeng": "eacebbb9",
}
OLD_HERO = "https://cdn.jsdelivr.net/gh/qizl19/Typora_PicGo/dbb44aed2e738bd4c1841401ad8b87d6277ff95d-16473576156451.webp"
HEADINGS = [
    "基本资料",
    "研制背景与时间线",
    "总体布局与设计特点",
    "动力系统",
    "主要型号与改型",
    "优势与局限",
    "参考资料与图片许可",
]
OLD_POSTS = [
    {
        "postId": "330e82f5",
        "nameZh": "直升机，不是直升飞机",
        "date": "2022-03-15",
        "heroImage": "https://i.loli.net/2020/05/01/gkihqEjXxJ5UZ1C.jpg",
        "category": "飞机资料整理",
    },
    {
        "postId": "ed3590dd",
        "nameZh": "欧洲直升机",
        "date": "2022-03-15",
        "heroImage": OLD_HERO,
        "category": "飞机资料整理",
    },
    {
        "postId": "3694e76f",
        "nameZh": "使用matlab实现排序问题",
        "date": "2022-01-25",
        "heroImage": "https://images8.alphacoders.com/984/984617.jpg",
        "category": "code记录",
    },
    {
        "postId": "4a17b156",
        "nameZh": "Hello World",
        "date": "2022-01-21",
        "heroImage": "https://images4.alphacoders.com/848/848687.png",
        "category": "",
    },
]


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def post_url(post: dict) -> str:
    return f"/p/{post['postId']}.html"


def post_title(post: dict) -> str:
    return post.get("title") or post["nameZh"]


def post_category(post: dict) -> str:
    return post.get("categoryName") or post.get("category", "")


def post_category_url(post: dict) -> str:
    if post.get("categoryUrl"):
        return post["categoryUrl"]
    return CATEGORY_URL if post_category(post) == "飞机资料整理" else ""


def post_tag(post: dict) -> str:
    return post.get("tagName", "")


def post_tag_url(post: dict) -> str:
    return post.get("tagUrl", "")


def normalize_aircraft(profile: dict) -> dict:
    profile["title"] = profile["nameZh"]
    profile["categoryName"] = "飞机资料整理"
    profile["categoryUrl"] = CATEGORY_URL
    profile["tagName"] = "航空"
    profile["tagUrl"] = TAG_URL
    return profile


def normalize_weekly(post: dict) -> dict:
    post["nameZh"] = post["title"]
    post["nameEn"] = post.get("subtitle", "")
    post["categoryName"] = WEEKLY_CATEGORY
    post["categoryUrl"] = WEEKLY_CATEGORY_URL
    post["tagName"] = WEEKLY_TAG
    post["tagUrl"] = WEEKLY_TAG_URL
    return post


def import_archive(root: Path, data_path: Path) -> list[dict]:
    source_path = root / "aircraft" / "data" / "aircraft.json"
    if not source_path.is_file():
        raise FileNotFoundError(f"Missing migration source: {source_path}")
    profiles = json.loads(source_path.read_text(encoding="utf-8"))
    for profile in profiles:
        post_id = POST_IDS[profile["slug"]]
        profile["postId"] = post_id
        profile.pop("pdf", None)
        source_hero = root / profile["heroImage"].lstrip("/")
        asset_dir = root / "p" / post_id
        asset_dir.mkdir(parents=True, exist_ok=True)
        copied: dict[str, str] = {}
        for photo in profile["photos"]:
            source = root / photo["src"].lstrip("/")
            target = asset_dir / source.name
            shutil.copy2(source, target)
            public_path = f"/p/{post_id}/{source.name}"
            copied[str(source.resolve())] = public_path
            photo["src"] = public_path
        hero_target = copied.get(str(source_hero.resolve()))
        if not hero_target:
            hero_target = f"/p/{post_id}/{source_hero.name}"
            shutil.copy2(source_hero, root / hero_target.lstrip("/"))
        profile["heroImage"] = hero_target
    data_path.parent.mkdir(parents=True, exist_ok=True)
    data_path.write_text(
        json.dumps(profiles, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return profiles


def heading(title: str) -> str:
    return f'<h2 id="{esc(title)}"><a href="#{esc(title)}" class="headerlink" title="{esc(title)}"></a>{esc(title)}</h2>'


def render_photo(photo: dict) -> str:
    return (
        f'<p><img src="{LAZY_PLACEHOLDER}" data-original="{esc(photo["src"])}" alt="{esc(photo["alt"])}"></p>'
        f'<center style="font-size:13px;color:#666;line-height:1.8">{esc(photo["caption"])}<br>'
        f'摄影 / 作者：{esc(photo["credit"])}；'
        f'<a target="_blank" rel="noopener" href="{esc(photo["sourceUrl"])}">原始来源</a>；'
        f'<a target="_blank" rel="noopener license" href="{esc(photo["licenseUrl"])}">{esc(photo["license"])}</a></center>'
    )


def render_article(profile: dict) -> str:
    facts = "".join(
        f'<tr><th>{esc(item["label"])}</th><td>{esc(item["value"])}'
        + (f'<br><small>{esc(item["note"])}</small>' if item.get("note") else "")
        + "</td></tr>"
        for item in profile["facts"]
    )
    timeline = "".join(
        f'<li><strong>{esc(item["year"])}</strong>：{esc(item["event"])}</li>'
        for item in profile["timeline"]
    )
    design = "".join(f"<li>{esc(item)}</li>" for item in profile["designPoints"])
    variants = "".join(
        f'<tr><th>{esc(item["name"])}</th><td>{esc(item["description"])}</td></tr>'
        for item in profile["variants"]
    )
    strengths = "".join(f"<li>{esc(item)}</li>" for item in profile["strengths"])
    limits = "".join(f"<li>{esc(item)}</li>" for item in profile["limits"])
    sources = "".join(
        f'<li><a target="_blank" rel="noopener" href="{esc(item["url"])}">{esc(item["label"])}</a></li>'
        for item in profile["sources"]
    )
    license_rows = "".join(
        f'<tr><td>{index}</td><td>{esc(photo["caption"])}</td><td>{esc(photo["credit"])}</td>'
        f'<td><a target="_blank" rel="noopener" href="{esc(photo["sourceUrl"])}">来源</a> / '
        f'<a target="_blank" rel="noopener license" href="{esc(photo["licenseUrl"])}">{esc(photo["license"])}</a></td></tr>'
        for index, photo in enumerate(profile["photos"], start=1)
    )

    parts = [
        f'<p>&emsp;&emsp;{esc(profile["summary"])}</p>',
        f'<blockquote><p>{esc(profile["statement"])}</p></blockquote>',
        render_photo(profile["photos"][0]),
        heading("基本资料"),
        '<table><thead><tr><th>项目</th><th>公开资料口径</th></tr></thead><tbody>' + facts + "</tbody></table>",
        f'<p>英文名称：<strong>{esc(profile["nameEn"])}</strong>；国家 / 地区：{esc(profile["nation"])}；类别：{esc(profile["category"])}；年代：{esc(profile["era"])}；当前状态：{esc(profile["status"])}。</p>',
        heading("研制背景与时间线"),
        '<p>&emsp;&emsp;下列节点用于说明该机从研制、首飞到运营或服役演进的主要脉络。不同来源日期口径存在差异时，以原始资料定义为准。</p>',
        f"<ul>{timeline}</ul>",
        heading("总体布局与设计特点"),
        f"<ul>{design}</ul>",
    ]
    if len(profile["photos"]) > 1:
        parts.append(render_photo(profile["photos"][1]))
    parts += [
        heading("动力系统"),
        f'<p>&emsp;&emsp;{esc(profile["power"])}</p>',
    ]
    if len(profile["photos"]) > 2:
        parts.append(render_photo(profile["photos"][2]))
    parts += [
        heading("主要型号与改型"),
        '<table><thead><tr><th>型号 / 称呼</th><th>定位与说明</th></tr></thead><tbody>' + variants + "</tbody></table>",
    ]
    if len(profile["photos"]) > 3:
        parts.extend(render_photo(photo) for photo in profile["photos"][3:])
    parts += [
        heading("优势与局限"),
        "<h3>主要优势</h3>",
        f"<ul>{strengths}</ul>",
        "<h3>局限与公开资料不足</h3>",
        f"<ul>{limits}</ul>",
        heading("参考资料与图片许可"),
        '<p>主要参考资料均为可点击链接：</p>',
        f"<ol>{sources}</ol>",
        '<h3>图片来源与许可</h3>',
        '<table><thead><tr><th>图</th><th>内容</th><th>摄影 / 作者</th><th>来源与许可</th></tr></thead><tbody>' + license_rows + "</tbody></table>",
        '<p><small>本文依据公开资料整理。涉及不同型号、批次、运营条件或统计口径的数值，不应脱离来源条件直接比较。</small></p>',
    ]
    return "".join(parts)


def render_toc(post: dict) -> str:
    items = []
    headings = post.get("headings") or [{"id": title, "title": title} for title in HEADINGS]
    for index, item in enumerate(headings, start=1):
        title = item["title"]
        heading_id = item.get("id", title)
        items.append(
            f'<li class="toc-item toc-level-2"><a class="toc-link" href="#{quote(heading_id, safe="")}">'
            f'<span class="toc-number">{index}.</span> <span class="toc-text">{esc(title)}</span></a></li>'
        )
    return '<ol class="toc">' + "".join(items) + "</ol>"


def render_post_info(profile: dict, article: str) -> str:
    published = f"{profile['date']}T01:00:00.000Z"
    text_length = len(re.sub(r"<[^>]+>", "", article))
    count = f"{text_length / 1000:.1f}k" if text_length >= 1000 else str(text_length)
    minutes = max(1, math.ceil(text_length / 430))
    title = post_title(profile)
    return f"""<h1 class="post-title">{esc(title)}</h1><div id="post-meta"><div class="meta-firstline"><span class="post-meta-date"><i class="far fa-calendar-alt fa-fw post-meta-icon"></i><span class="post-meta-label">发表于</span><time class="post-meta-date-created" datetime="{published}" title="发表于 {esc(profile['date'])} 09:00:00">{esc(profile['date'])}</time><span class="post-meta-separator">|</span><i class="fas fa-history fa-fw post-meta-icon"></i><span class="post-meta-label">更新于</span><time class="post-meta-date-updated" datetime="{published}" title="更新于 {esc(profile['date'])} 09:00:00">{esc(profile['date'])}</time></span><span class="post-meta-categories"><span class="post-meta-separator">|</span><i class="fas fa-inbox fa-fw post-meta-icon"></i><a class="post-meta-categories" href="{post_category_url(profile)}">{esc(post_category(profile))}</a></span></div><div class="meta-secondline"><span class="post-meta-separator">|</span><span class="post-meta-wordcount"><i class="far fa-file-word fa-fw post-meta-icon"></i><span class="post-meta-label">字数总计:</span><span class="word-count">{count}</span><span class="post-meta-separator">|</span><i class="far fa-clock fa-fw post-meta-icon"></i><span class="post-meta-label">阅读时长:</span><span>{minutes}分钟</span></span><span class="post-meta-separator">|</span><span class="post-meta-pv-cv" data-flag-title="{esc(title)}"><i class="far fa-eye fa-fw post-meta-icon"></i><span class="post-meta-label">阅读量:</span><span id="busuanzi_value_page_pv"></span></span></div></div>"""


def pagination_side(post: dict, side: str) -> str:
    css = "prev-post pull-left" if side == "prev" else "next-post pull-right"
    image_css = "prev-cover" if side == "prev" else "next-cover"
    info_css = "prev_info" if side == "prev" else "next_info"
    label = "上一篇" if side == "prev" else "下一篇"
    return f'<div class="{css}"><a href="{post_url(post)}"><img class="{image_css}" src="{esc(post["heroImage"])}" onerror="onerror=null;src=\'/img/404.jpg\'" alt="cover"><div class="pagination-info"><div class="label">{label}</div><div class="{info_css}">{esc(post_title(post))}</div></div></a></div>'


def render_pagination(profile: dict, ordered: list[dict]) -> str:
    index = next(i for i, item in enumerate(ordered) if item["postId"] == profile["postId"])
    previous = pagination_side(ordered[index - 1], "prev") if index > 0 else ""
    following = pagination_side(ordered[index + 1], "next") if index + 1 < len(ordered) else ""
    return f'<nav class="pagination-post" id="pagination">{previous}{following}</nav>'


def replace_meta(text: str, profile: dict, article: str) -> str:
    title = post_title(profile)
    description = profile["summary"][:220]
    url = f"{SITE_URL}{post_url(profile)}"
    published = f"{profile['date']}T01:00:00.000Z"
    replacements = [
        (r"<title>.*?</title>", f"<title>{esc(title)} | Qzl's Blog</title>"),
        (r'<meta name="description" content=".*?">', f'<meta name="description" content="{esc(description)}">'),
        (r'<meta property="og:title" content=".*?">', f'<meta property="og:title" content="{esc(title)}">'),
        (r'<meta property="og:url" content=".*?">', f'<meta property="og:url" content="{url}">'),
        (r'<meta property="og:description" content=".*?">', f'<meta property="og:description" content="{esc(description)}">'),
        (r'<meta property="og:image" content=".*?">', f'<meta property="og:image" content="{SITE_URL}{esc(profile["heroImage"])}">'),
        (r'<meta property="article:published_time" content=".*?">', f'<meta property="article:published_time" content="{published}">'),
        (r'<meta property="article:modified_time" content=".*?">', f'<meta property="article:modified_time" content="{published}">'),
        (r'<meta name="twitter:image" content=".*?">', f'<meta name="twitter:image" content="{SITE_URL}{esc(profile["heroImage"])}">'),
        (r'<link rel="canonical" href=".*?">', f'<link rel="canonical" href="{url[:-5]}">'),
    ]
    for pattern, value in replacements:
        text = re.sub(pattern, value, text, count=1, flags=re.S)
    text = re.sub(r"title: '.*?',\n  isPost", f"title: '{title}',\n  isPost", text, count=1)
    text = re.sub(r"postUpdate: '.*?'", f"postUpdate: '{profile['date']} 09:00:00'", text, count=1)
    text = re.sub(
        r'<header class="post-bg" id="page-header" style="background-image: url\(\'.*?\'\)">',
        f'<header class="post-bg" id="page-header" style="background-image: url(\'{esc(profile["heroImage"])}\')">',
        text,
        count=1,
    )
    post_info = render_post_info(profile, article)
    text = re.sub(
        r'<div id="post-info">.*?</div></div></header>',
        f'<div id="post-info">{post_info}</div></div></header>',
        text,
        count=1,
        flags=re.S,
    )
    text = re.sub(
        r'<article class="post-content" id="article-container">.*?</article>',
        f'<article class="post-content" id="article-container">{article}</article>',
        text,
        count=1,
        flags=re.S,
    )
    text = re.sub(r'<ol class="toc">.*?</ol>', render_toc(profile), text, count=1, flags=re.S)
    text = text.replace(
        "https://qizl19.github.io/p/ed3590dd.html",
        f"{SITE_URL}{post_url(profile)}",
    )
    text = re.sub(
        r'(<div class="social-share" data-image=").*?(" data-sites=)',
        rf'\g<1>{esc(profile["heroImage"])}\g<2>',
        text,
        count=1,
    )
    text = text.replace('data-flag-title="欧洲直升机"', f'data-flag-title="{esc(title)}"')
    text = re.sub(
        r'<a class="post-meta__tags" href=".*?">.*?</a>',
        f'<a class="post-meta__tags" href="{post_tag_url(profile)}">{esc(post_tag(profile))}</a>',
        text,
        count=1,
    )
    text = re.sub(
        r'<meta property="article:tag" content=".*?">',
        f'<meta property="article:tag" content="{esc(post_tag(profile))}">',
        text,
        count=1,
    )
    return text


def render_home_card(post: dict, index: int) -> str:
    side = "left" if index % 2 == 0 else "right"
    excerpt = esc(post["summary"][:100])
    title = post_title(post)
    tag_html = ""
    if post_tag(post):
        tag_html = f'<span class="article-meta tags"><span class="article-meta-separator">|</span><i class="fas fa-tag"></i><a class="article-meta__tags" href="{post_tag_url(post)}">{esc(post_tag(post))}</a></span>'
    return f'<div class="recent-post-item"><div class="post_cover {side}"><a href="{post_url(post)}" title="{esc(title)}"><img class="post_bg" src="{esc(post["heroImage"])}" onerror="this.onerror=null;this.src=\'/img/404.jpg\'" alt="{esc(title)}"></a></div><div class="recent-post-info"><a class="article-title" href="{post_url(post)}" title="{esc(title)}">{esc(title)}</a><div class="article-meta-wrap"><span class="post-meta-date"><i class="far fa-calendar-alt"></i><span class="article-meta-label">发表于</span><time datetime="{esc(post["date"])}T01:00:00.000Z" title="发表于 {esc(post["date"])} 09:00:00">{esc(post["date"])}</time></span><span class="article-meta"><span class="article-meta-separator">|</span><i class="fas fa-inbox"></i><a class="article-meta__categories" href="{post_category_url(post)}">{esc(post_category(post))}</a></span>{tag_html}</div><div class="content">{excerpt}</div></div></div>'


def render_sort_item(post: dict) -> str:
    title = post_title(post)
    return f'<div class="article-sort-item"><a class="article-sort-item-img" href="{post_url(post)}" title="{esc(title)}"><img src="{esc(post["heroImage"])}" alt="{esc(title)}" onerror="this.onerror=null;this.src=\'/img/404.jpg\'"></a><div class="article-sort-item-info"><div class="article-sort-item-time"><i class="far fa-calendar-alt"></i><time class="post-meta-date-created" datetime="{esc(post["date"])}T01:00:00.000Z" title="发表于 {esc(post["date"])} 09:00:00">{esc(post["date"])}</time></div><a class="article-sort-item-title" href="{post_url(post)}" title="{esc(title)}">{esc(title)}</a></div></div>'


def render_aside_item(post: dict) -> str:
    title = post_title(post)
    return f'<div class="aside-list-item"><a class="thumbnail" href="{post_url(post)}" title="{esc(title)}"><img src="{esc(post["heroImage"])}" onerror="this.onerror=null;this.src=\'/img/404.jpg\'" alt="{esc(title)}"></a><div class="content"><a class="title" href="{post_url(post)}" title="{esc(title)}">{esc(title)}</a><time datetime="{esc(post["date"])}T01:00:00.000Z" title="发表于 {esc(post["date"])} 09:00:00">{esc(post["date"])}</time></div></div>'


def replace_block(text: str, marker: str, content: str, anchor: str) -> str:
    start = f"<!-- {marker}_START -->"
    end = f"<!-- {marker}_END -->"
    block = start + content + end
    if start in text:
        return re.sub(re.escape(start) + r".*?" + re.escape(end), block, text, count=1, flags=re.S)
    if anchor not in text:
        raise RuntimeError(f"Missing insertion anchor for {marker}")
    return text.replace(anchor, block + anchor, 1)


def remove_block(text: str, marker: str) -> str:
    start = f"<!-- {marker}_START -->"
    end = f"<!-- {marker}_END -->"
    if start not in text:
        return text
    return re.sub(re.escape(start) + r".*?" + re.escape(end), "", text, count=1, flags=re.S)


def render_grouped_listing(posts: list[dict]) -> str:
    chunks: list[str] = []
    current_year = None
    for post in sorted(posts, key=lambda item: item["date"], reverse=True):
        year = post["date"][:4]
        if year != current_year:
            chunks.append(f'<div class="article-sort-item year">{year}</div>')
            current_year = year
        chunks.append(render_sort_item(post))
    return "".join(chunks)


def build_taxonomy_page(
    root: Path,
    source_relative: Path,
    target_relative: Path,
    kind: str,
    label: str,
    canonical_url: str,
    listing: str,
) -> None:
    text = (root / source_relative).read_text(encoding="utf-8")
    display = f"{kind} - {label}"
    text = re.sub(r"<title>.*? \| Qzl's Blog</title>", f"<title>{esc(display)} | Qzl's Blog</title>", text, count=1)
    text = re.sub(r'<meta property="og:title" content=".*?">', f'<meta property="og:title" content="{esc(display)}">', text, count=1)
    text = re.sub(r'<meta property="og:url" content=".*?">', f'<meta property="og:url" content="{SITE_URL}{canonical_url}index.html">', text, count=1)
    text = re.sub(r'<link rel="canonical" href=".*?">', f'<link rel="canonical" href="{SITE_URL}{canonical_url}">', text, count=1)
    text = re.sub(r"title: '.*?',\n  isPost", f"title: '{display}',\n  isPost", text, count=1)
    text = re.sub(r'<div class="article-sort-title">.*?</div>', f'<div class="article-sort-title">{esc(display)}</div>', text, count=1)
    text = re.sub(
        r'<div class="article-sort">.*?(?=<nav id="pagination">)',
        f'<div class="article-sort"><!-- CAD_CAE_POSTS_START -->{listing}<!-- CAD_CAE_POSTS_END --></div>',
        text,
        count=1,
        flags=re.S,
    )
    target = root / target_relative
    target.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(line.rstrip() for line in text.splitlines()) + "\n"
    target.write_text(text, encoding="utf-8")


def update_index_pages(root: Path, profiles: list[dict], weekly_posts: list[dict]) -> None:
    aircraft_listing = render_grouped_listing(profiles)
    weekly_listing = render_grouped_listing(weekly_posts)
    managed_posts = sorted(profiles + weekly_posts, key=lambda item: item["date"], reverse=True)
    managed_listing = render_grouped_listing(managed_posts)
    year_anchor = '<div class="article-sort-item year">2022</div>'

    homepage_path = root / "index.html"
    homepage = homepage_path.read_text(encoding="utf-8")
    old_home_anchor = '<div class="recent-post-item"><div class="post_cover left"><a href="/p/330e82f5.html"'
    homepage = remove_block(homepage, "AIRCRAFT_POSTS")
    homepage = replace_block(
        homepage,
        "MANAGED_POSTS",
        "".join(render_home_card(post, index) for index, post in enumerate(managed_posts)),
        old_home_anchor,
    )
    category_cards = (
        '<li class="categoryBar-list-item category-code"><a class="categoryBar-list-link" href="/categories/code%E8%AE%B0%E5%BD%95/">code记录</a><span class="categoryBar-list-count">1</span></li>'
        f'<li class="categoryBar-list-item category-aircraft"><a class="categoryBar-list-link" href="{CATEGORY_URL}">飞机资料整理</a><span class="categoryBar-list-count">{len(profiles) + 2}</span></li>'
        f'<li class="categoryBar-list-item category-cad-cae"><a class="categoryBar-list-link" href="{WEEKLY_CATEGORY_URL}">{WEEKLY_CATEGORY}</a><span class="categoryBar-list-count">{len(weekly_posts)}</span></li>'
    )
    homepage = re.sub(
        r'(<ul class="categoryBar-list">).*?(</ul>)',
        rf"\g<1>{category_cards}\g<2>",
        homepage,
        count=1,
        flags=re.S,
    )
    homepage_path.write_text(homepage, encoding="utf-8")

    archive_path = root / "archives" / "index.html"
    archive = archive_path.read_text(encoding="utf-8")
    archive = remove_block(archive, "AIRCRAFT_POSTS")
    archive = replace_block(archive, "MANAGED_POSTS", managed_listing, year_anchor)
    archive = re.sub(r"文章总览 - \d+", f"文章总览 - {len(managed_posts) + len(OLD_POSTS)}", archive, count=1)
    archive_path.write_text(archive, encoding="utf-8")

    for relative in [Path("categories/飞机资料整理/index.html"), Path("tags/航空/index.html")]:
        path = root / relative
        content = path.read_text(encoding="utf-8")
        content = replace_block(content, "AIRCRAFT_POSTS", aircraft_listing, year_anchor)
        path.write_text(content, encoding="utf-8")

    build_taxonomy_page(
        root,
        Path("categories/飞机资料整理/index.html"),
        Path("categories/CAD-CAE生态周报/index.html"),
        "分类",
        WEEKLY_CATEGORY,
        WEEKLY_CATEGORY_URL,
        weekly_listing,
    )
    build_taxonomy_page(
        root,
        Path("tags/航空/index.html"),
        Path("tags/CAD-CAE/index.html"),
        "标签",
        WEEKLY_TAG,
        WEEKLY_TAG_URL,
        weekly_listing,
    )

    categories_path = root / "categories" / "index.html"
    categories = categories_path.read_text(encoding="utf-8")
    categories = re.sub(
        r'(<a class="category-list-link" href="/categories/%E9%A3%9E%E6%9C%BA%E8%B5%84%E6%96%99%E6%95%B4%E7%90%86/">飞机资料整理</a><span class="category-list-count">)\d+(</span>)',
        rf"\g<1>{len(profiles) + 2}\g<2>",
        categories,
        count=1,
    )
    weekly_category_item = f'<li class="category-list-item"><a class="category-list-link" href="{WEEKLY_CATEGORY_URL}">{WEEKLY_CATEGORY}</a><span class="category-list-count">{len(weekly_posts)}</span></li>'
    if WEEKLY_CATEGORY_URL in categories:
        categories = re.sub(
            rf'<li class="category-list-item"><a class="category-list-link" href="{re.escape(WEEKLY_CATEGORY_URL)}">.*?</a><span class="category-list-count">\d+</span></li>',
            weekly_category_item,
            categories,
            count=1,
        )
    else:
        categories = categories.replace("</ul></div></div>", weekly_category_item + "</ul></div></div>", 1)
    categories_path.write_text(categories, encoding="utf-8")


def update_search(root: Path, profiles: list[dict], weekly_posts: list[dict]) -> None:
    entries = []
    for profile in profiles + weekly_posts:
        article = profile.get("articleHtml") or render_article(profile)
        article = article.replace("]]>", "] ]>")
        entries.append(
            f'<entry><title>{esc(post_title(profile))}</title><link href="{post_url(profile)}"/><url>{post_url(profile)}</url>'
            f'<content type="html"><![CDATA[{article}]]></content><categories><category> {esc(post_category(profile))} </category></categories>'
            f'<tags><tag> {esc(post_tag(profile))} </tag></tags></entry>'
        )
    path = root / "search.xml"
    text = path.read_text(encoding="utf-8")
    text = remove_block(text, "AIRCRAFT_POSTS")
    start = "<!-- MANAGED_POSTS_START -->"
    end = "<!-- MANAGED_POSTS_END -->"
    block = start + "".join(entries) + end
    if start in text:
        text = re.sub(re.escape(start) + r".*?" + re.escape(end), block, text, count=1, flags=re.S)
    elif "<search>" in text:
        text = text.replace("<search>", "<search>" + block, 1)
    else:
        raise RuntimeError("Missing <search> root element")
    text = "\n".join(line.rstrip() for line in text.splitlines()) + "\n"
    path.write_text(text, encoding="utf-8")


def update_global_shell(root: Path, profiles: list[dict], weekly_posts: list[dict]) -> None:
    managed_posts = sorted(profiles + weekly_posts, key=lambda item: item["date"], reverse=True)
    total_posts = len(managed_posts) + len(OLD_POSTS)
    recent_posts = (managed_posts + OLD_POSTS)[:5]
    aside = "".join(render_aside_item(post) for post in recent_posts)
    menu_item = '<div class="menus_item"><a class="site-page" href="/aircraft/"><i class="fa-fw fa fa-plane"></i><span> 飞机资料库</span></a></div>'
    category_item = '<li class="categoryBar-list-item"><a class="categoryBar-list-link" href="/aircraft/">飞机资料库</a><span class="categoryBar-list-count">4</span></li>'
    recent_prefix = '<div class="card-widget card-recent-post"><div class="item-headline"><i class="fas fa-history"></i><span>最新文章</span></div><div class="aside-list">'
    for path in root.rglob("*.html"):
        if ".git" in path.parts or "aircraft" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        text = text.replace(menu_item, "").replace(category_item, "")
        text = re.sub(
            r'<div class="headline">文章</div><div class="length-num">\d+</div>',
            f'<div class="headline">文章</div><div class="length-num">{total_posts}</div>',
            text,
        )
        text = re.sub(
            r'(<a class="categoryBar-list-link" href="/categories/%E9%A3%9E%E6%9C%BA%E8%B5%84%E6%96%99%E6%95%B4%E7%90%86/">飞机资料整理</a><span class="categoryBar-list-count">)\d+(</span>)',
            rf"\g<1>{len(profiles) + 2}\g<2>",
            text,
        )
        text = re.sub(
            rf'(<a class="categoryBar-list-link" href="{re.escape(WEEKLY_CATEGORY_URL)}">{re.escape(WEEKLY_CATEGORY)}</a><span class="categoryBar-list-count">)\d+(</span>)',
            rf"\g<1>{len(weekly_posts)}\g<2>",
            text,
        )
        text = re.sub(
            r'(<a href="/tags/"><div class="headline">标签</div><div class="length-num">)\d+(</div>)',
            r"\g<1>3\g<2>",
            text,
        )
        text = re.sub(
            r'(<a href="/categories/"><div class="headline">分类</div><div class="length-num">)\d+(</div>)',
            r"\g<1>3\g<2>",
            text,
        )
        text = re.sub(
            r'<div class="item-name">📔文章数目 :</div><div class="item-count">\d+</div>',
            f'<div class="item-name">📔文章数目 :</div><div class="item-count">{total_posts}</div>',
            text,
        )
        text = re.sub(
            r'<div class="item-name">🐌本站总字数 :</div><div class="item-count">.*?</div>',
            '<div class="item-name">🐌本站总字数 :</div><div class="item-count">约 33k</div>',
            text,
        )
        start = text.find(recent_prefix)
        if start >= 0:
            content_start = start + len(recent_prefix)
            tail = text[content_start:]
            end_match = re.search(
                r'(?=</div></div>(?:<div class="card-widget card-webinfo">|</div></div></main>))',
                tail,
                flags=re.S,
            )
            if end_match:
                text = text[:content_start] + aside + tail[end_match.start():]
        path.write_text(text, encoding="utf-8")


def build_posts(root: Path, profiles: list[dict], weekly_posts: list[dict]) -> None:
    template = (root / "p" / "ed3590dd.html").read_text(encoding="utf-8")
    managed_posts = sorted(profiles + weekly_posts, key=lambda item: item["date"], reverse=True)
    ordered = managed_posts + OLD_POSTS
    for profile in managed_posts:
        article = profile.get("articleHtml") or render_article(profile)
        page = replace_meta(template, profile, article)
        page = re.sub(
            r'<nav class="pagination-post" id="pagination">.*?</nav>',
            render_pagination(profile, ordered),
            page,
            count=1,
            flags=re.S,
        )
        page = "\n".join(line.rstrip() for line in page.splitlines()) + "\n"
        target = root / "p" / f"{profile['postId']}.html"
        target.write_text(page, encoding="utf-8")


def load_weekly_posts(root: Path) -> list[dict]:
    data_path = root / "data" / "cad_cae_weekly_posts.json"
    if not data_path.is_file():
        return []
    posts = [normalize_weekly(post) for post in json.loads(data_path.read_text(encoding="utf-8"))]
    for post in posts:
        content_path = root / post["contentFile"]
        post["articleHtml"] = content_path.read_text(encoding="utf-8")
    return sorted(posts, key=lambda item: item["date"], reverse=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build aircraft profiles as ordinary Butterfly blog posts.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.root.resolve()
    data_path = root / "data" / "aircraft_posts.json"
    profiles = (
        json.loads(data_path.read_text(encoding="utf-8"))
        if data_path.is_file()
        else import_archive(root, data_path)
    )
    profiles = [normalize_aircraft(profile) for profile in profiles]
    profiles.sort(key=lambda item: item["date"], reverse=True)
    weekly_posts = load_weekly_posts(root)
    build_posts(root, profiles, weekly_posts)
    update_index_pages(root, profiles, weekly_posts)
    update_search(root, profiles, weekly_posts)
    update_global_shell(root, profiles, weekly_posts)
    print(f"Built {len(profiles)} aircraft articles and {len(weekly_posts)} CAD/CAE weekly articles")


if __name__ == "__main__":
    main()
