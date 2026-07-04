from pathlib import Path
import re

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
)


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "pdf" / "omaezaki-lifehack-category-items.pdf"
FONT_PATHS = [
    Path(r"C:\Windows\Fonts\NotoSansJP-VF.ttf"),
    Path(r"C:\Windows\Fonts\yumin.ttf"),
]


def register_font() -> str:
    for path in FONT_PATHS:
        if path.exists():
            pdfmetrics.registerFont(TTFont("Japanese", str(path)))
            return "Japanese"
    return "Helvetica"


def extract_items() -> list[dict]:
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    categories = []
    pattern = re.compile(
        r'<div class="category-block" id="([^"]+)" data-code="([^"]+)".*?'
        r'<span class="c-title">(.*?)</span>.*?'
        r'<ul class="topic-list">(.*?)</ul>',
        re.S,
    )
    item_pattern = re.compile(
        r'<li data-code="([^"]+)".*?'
        r'<a href="([^"]+)".*?'
        r'<span class="t-title">(.*?)</span>',
        re.S,
    )
    for match in pattern.finditer(html):
        _, code, title, ul = match.groups()
        clean_title = re.sub(r"<.*?>", "", title).strip()
        items = []
        for item in item_pattern.finditer(ul):
            item_code, href, item_title = item.groups()
            clean_item_title = re.sub(r"<.*?>", "", item_title).strip()
            items.append({"code": item_code, "title": clean_item_title, "href": href})
        categories.append({"code": code, "title": clean_title, "items": items})
    return categories


def page_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Japanese", 8)
    canvas.setFillColor(colors.HexColor("#6b7280"))
    canvas.drawRightString(200 * mm, 10 * mm, f"{doc.page}")
    canvas.restoreState()


def build_pdf() -> None:
    font = register_font()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "TitleJP",
        parent=styles["Title"],
        fontName=font,
        fontSize=18,
        leading=25,
        textColor=colors.HexColor("#174c3c"),
        spaceAfter=8,
        wordWrap="CJK",
    )
    subtitle = ParagraphStyle(
        "SubtitleJP",
        parent=styles["Normal"],
        fontName=font,
        fontSize=9,
        leading=14,
        textColor=colors.HexColor("#4b5563"),
        spaceAfter=12,
        wordWrap="CJK",
    )
    heading = ParagraphStyle(
        "HeadingJP",
        parent=styles["Heading2"],
        fontName=font,
        fontSize=13,
        leading=18,
        textColor=colors.white,
        backColor=colors.HexColor("#176b55"),
        borderPadding=(5, 7, 5, 7),
        spaceBefore=8,
        spaceAfter=5,
        wordWrap="CJK",
    )
    body = ParagraphStyle(
        "BodyJP",
        parent=styles["Normal"],
        fontName=font,
        fontSize=9.2,
        leading=14,
        leftIndent=8,
        firstLineIndent=-8,
        textColor=colors.HexColor("#1f2937"),
        spaceAfter=2.3,
        wordWrap="CJK",
    )

    doc = BaseDocTemplate(
        str(OUT),
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=16 * mm,
        title="磐田ライフハック 大項目・中項目一覧",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    doc.addPageTemplates([PageTemplate(id="page", frames=[frame], onPage=page_footer)])

    story = [
        Paragraph("磐田ライフハック 大項目・中項目一覧", title),
        Paragraph("トップページに掲載している「くらしの場面・目的から選ぶ」の現在構成です。番号は管理用の内部番号で、サイト上には表示していません。", subtitle),
    ]
    for idx, category in enumerate(extract_items(), start=1):
        if idx in (6, 10):
            story.append(PageBreak())
        story.append(Paragraph(f'{category["code"]}　{category["title"]}', heading))
        for item in category["items"]:
            story.append(Paragraph(f'{item["code"]}　{item["title"]}<br/><font color="#6b7280">{item["href"]}</font>', body))
        story.append(Spacer(1, 4))

    doc.build(story)
    print(OUT)


if __name__ == "__main__":
    build_pdf()
