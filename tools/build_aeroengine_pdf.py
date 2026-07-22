from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)


SECTION_RE = re.compile(
    r'<h2 id="([^"]+)">.*?</h2>(.*?)(?=<h2 id=|\Z)', re.S
)
BLOCK_RE = re.compile(
    r'(<p>.*?</p>|<blockquote>.*?</blockquote>|<ol>.*?</ol>|<ul>.*?</ul>|'
    r'<div class="aeroengine-formula">.*?</div>|<figure class="aeroengine-figure">.*?</figure>)',
    re.S,
)


def register_fonts() -> None:
    regular = Path(r"C:\Windows\Fonts\msyh.ttc")
    bold = Path(r"C:\Windows\Fonts\msyhbd.ttc")
    if not regular.is_file():
        raise FileNotFoundError("Microsoft YaHei font is required for Chinese PDF output")
    pdfmetrics.registerFont(TTFont("MicrosoftYaHei", str(regular), subfontIndex=0))
    if bold.is_file():
        pdfmetrics.registerFont(TTFont("MicrosoftYaHei-Bold", str(bold), subfontIndex=0))
    else:
        pdfmetrics.registerFont(TTFont("MicrosoftYaHei-Bold", str(regular), subfontIndex=0))
    pdfmetrics.registerFontFamily(
        "MicrosoftYaHei",
        normal="MicrosoftYaHei",
        bold="MicrosoftYaHei-Bold",
    )


def clean_inline(value: str) -> str:
    value = re.sub(
        r'<a [^>]*href="([^"]+)"[^>]*>(.*?)</a>',
        r'<link href="\1" color="#17689a"><u>\2</u></link>',
        value,
        flags=re.S,
    )
    value = value.replace("<code>", '<font color="#173b57">').replace("</code>", "</font>")
    value = re.sub(r"<br\s*/?>", "<br/>", value)
    return value.strip()


def image_flowable(root: Path, figure_html: str, caption_style: ParagraphStyle):
    image_match = re.search(r'<img src="([^"]+)"', figure_html)
    caption_match = re.search(r'<figcaption>(.*?)</figcaption>', figure_html, flags=re.S)
    if not image_match:
        return []
    source = image_match.group(1)
    if source.endswith(".svg"):
        source = source[:-4] + ".png"
    path = root / source.lstrip("/")
    if not path.is_file():
        raise FileNotFoundError(path)
    width, height = Image(str(path)).imageWidth, Image(str(path)).imageHeight
    max_width = 170 * mm
    max_height = 88 * mm
    scale = min(max_width / width, max_height / height)
    result = [Spacer(1, 2 * mm), Image(str(path), width=width * scale, height=height * scale)]
    if caption_match:
        result.extend([Spacer(1, 1.5 * mm), Paragraph(clean_inline(caption_match.group(1)), caption_style)])
    return result


def render_section(root: Path, body: str, styles: dict[str, ParagraphStyle]):
    flows = []
    for block in BLOCK_RE.findall(body):
        if block.startswith("<figure"):
            flows.extend(image_flowable(root, block, styles["caption"]))
        elif block.startswith("<blockquote"):
            inner = re.sub(r"^<blockquote>|</blockquote>$", "", block, flags=re.S)
            inner = re.sub(r"^\s*<p>|</p>\s*$", "", inner, flags=re.S)
            flows.append(Paragraph(clean_inline(inner), styles["quote"]))
        elif block.startswith("<ol>") or block.startswith("<ul>"):
            ordered = block.startswith("<ol>")
            items = re.findall(r"<li>(.*?)</li>", block, flags=re.S)
            for index, item in enumerate(items, 1):
                marker = f"{index}." if ordered else "•"
                flows.append(Paragraph(f"{marker}　{clean_inline(item)}", styles["list"]))
        elif block.startswith('<div class="aeroengine-formula">'):
            inner = re.sub(r"^<div[^>]*>|</div>$", "", block, flags=re.S)
            flows.append(Paragraph(clean_inline(inner), styles["formula"]))
        else:
            inner = re.sub(r"^<p>|</p>$", "", block, flags=re.S)
            flows.append(Paragraph(clean_inline(inner), styles["body"]))
    return flows


def page_footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("MicrosoftYaHei", 8)
    canvas.setFillColor(colors.HexColor("#607487"))
    canvas.drawString(20 * mm, 11 * mm, "航空发动机学习简报 · 第 01 期")
    canvas.drawRightString(190 * mm, 11 * mm, f"{doc.page}")
    canvas.restoreState()


def build(root: Path, post: dict, output: Path) -> None:
    register_fonts()
    source = (root / post["contentFile"]).read_text(encoding="utf-8")
    sections = SECTION_RE.findall(source)
    if len(sections) != len(post["headings"]):
        raise RuntimeError("Heading count does not match structured metadata")

    sample = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle(
            "TitleZh", parent=sample["Title"], fontName="MicrosoftYaHei-Bold",
            fontSize=24, leading=34, textColor=colors.HexColor("#0d2d45"), alignment=TA_CENTER,
        ),
        "subtitle": ParagraphStyle(
            "SubtitleZh", parent=sample["Normal"], fontName="MicrosoftYaHei",
            fontSize=12, leading=20, textColor=colors.HexColor("#4c6476"), alignment=TA_CENTER,
        ),
        "h2": ParagraphStyle(
            "H2Zh", parent=sample["Heading2"], fontName="MicrosoftYaHei-Bold",
            fontSize=15, leading=22, textColor=colors.HexColor("#0e4d72"),
            spaceBefore=4 * mm, spaceAfter=2 * mm,
        ),
        "body": ParagraphStyle(
            "BodyZh", parent=sample["BodyText"], fontName="MicrosoftYaHei",
            fontSize=9.4, leading=15.4, textColor=colors.HexColor("#263746"),
            spaceAfter=2.2 * mm, wordWrap="CJK",
        ),
        "list": ParagraphStyle(
            "ListZh", parent=sample["BodyText"], fontName="MicrosoftYaHei",
            fontSize=9.2, leading=14.7, leftIndent=5 * mm, firstLineIndent=-4 * mm,
            textColor=colors.HexColor("#263746"), spaceAfter=1.4 * mm, wordWrap="CJK",
        ),
        "quote": ParagraphStyle(
            "QuoteZh", parent=sample["BodyText"], fontName="MicrosoftYaHei",
            fontSize=10, leading=16, leftIndent=5 * mm, rightIndent=3 * mm,
            borderColor=colors.HexColor("#2f80b9"), borderWidth=1.2,
            borderPadding=7, backColor=colors.HexColor("#edf6fb"),
            textColor=colors.HexColor("#18384e"), spaceAfter=3 * mm, wordWrap="CJK",
        ),
        "formula": ParagraphStyle(
            "FormulaZh", parent=sample["BodyText"], fontName="MicrosoftYaHei",
            fontSize=10, leading=16, leftIndent=5 * mm, rightIndent=5 * mm,
            borderColor=colors.HexColor("#b8cbd8"), borderWidth=0.6,
            borderPadding=6, backColor=colors.HexColor("#f4f8fa"),
            textColor=colors.HexColor("#173b57"), spaceAfter=2.5 * mm, wordWrap="CJK",
        ),
        "caption": ParagraphStyle(
            "CaptionZh", parent=sample["BodyText"], fontName="MicrosoftYaHei",
            fontSize=7.8, leading=12, textColor=colors.HexColor("#63798b"),
            alignment=TA_CENTER, spaceAfter=2 * mm, wordWrap="CJK",
        ),
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(output), pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm,
        topMargin=17 * mm, bottomMargin=18 * mm,
        title=post["title"], author="Qzl's Blog",
    )
    hero = root / post["heroImage"].lstrip("/")
    story = [
        Spacer(1, 10 * mm),
        Paragraph("航空发动机学习简报", styles["title"]),
        Spacer(1, 3 * mm),
        Paragraph("第 01 期 · Brayton 循环与部件匹配", styles["subtitle"]),
        Spacer(1, 8 * mm),
        Image(str(hero), width=170 * mm, height=95.625 * mm),
        Spacer(1, 8 * mm),
        Paragraph(post["summary"], styles["quote"]),
        Spacer(1, 5 * mm),
        Paragraph("基础与前置知识　｜　2026-07-22　｜　预计学习 12-15 分钟", styles["subtitle"]),
        PageBreak(),
    ]
    page_break_after = {2, 4, 5, 7, 9}
    for index, ((_, body), heading) in enumerate(zip(sections, post["headings"]), 1):
        story.append(Paragraph(f"{index:02d}　{html.escape(heading['title'])}", styles["h2"]))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#b8cbd8")))
        story.append(Spacer(1, 2 * mm))
        story.extend(render_section(root, body, styles))
        if index in page_break_after:
            story.append(PageBreak())

    doc.build(story, onFirstPage=page_footer, onLaterPages=page_footer)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a Chinese aeroengine briefing PDF.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--post-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    posts = json.loads((root / "data" / "aeroengine_posts.json").read_text(encoding="utf-8"))
    post = next((item for item in posts if item["postId"] == args.post_id), None)
    if not post:
        raise SystemExit(f"Unknown postId: {args.post_id}")
    build(root, post, args.output.resolve())
    print(args.output.resolve())


if __name__ == "__main__":
    main()
