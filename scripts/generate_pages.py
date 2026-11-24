#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_pages.py — data/topics_master.json + data/city.json から中項目詳細ページを生成する。

実装範囲（2026-07-03改訂）:
  骨組み（見出し・リード文・公式窓口ボックス・出典リンク・関連リンク・CVブロック・
  フィードバック欄・フッター）に加え、data/content/<category-slug>.json に格納された
  個別執筆済みコンテンツ（real_cards / qa / tabs / steps / action_grid）があれば
  本文セクションとして組み込む。当該JSONが存在しない項目は骨組みのみで出力する。

公開ゲート（2026-07-03改訂）:
  大石による人力目視チェック(human-verified)は個別ゲートとして設けない。
  status が ai-checked 以上（＝出典調査済み。値の裏取りができなかったfactsは
  「確認中」と表示する運用で安全側に倒す）の項目を life/ 配下に出力する。
  draft のみ _staging/（.assetsignore対象・非配信）に出力する。

実行:
  python3 scripts/generate_pages.py            # 全項目を再生成
  python3 scripts/generate_pages.py --category 親のこと
"""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "data" / "topics_master.json"
CITY = ROOT / "data" / "city.json"
CONTENT_DIR = ROOT / "data" / "content"
LIFE_DIR = ROOT / "life"
STAGING_DIR = ROOT / "_staging"

PUBLISHABLE_STATUSES = ("ai-checked", "machine-verified", "human-verified", "published")

CATEGORY_ICON = {
    "困った・相談したい": "🧩", "暮らし始めた": "🧭", "働く・暮らす": "💴",
    "家族が増える": "👶", "健康・医療": "🏥", "もしもの時": "⚠️",
    "人生の終わり": "🕊️", "家・住まい": "🏠", "学ぶ・育つ": "🎒",
    "親のこと": "👵", "遊ぶ・使う・出かける": "🌳", "これから暮らす": "🏡",
    "新しい場所へ": "📦",
}


def esc(s):
    if s is None:
        return ""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def load():
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    city = json.loads(CITY.read_text(encoding="utf-8"))
    return ledger, city


def load_content_map():
    """data/content/<slug>.json（_input_*/_reference_*を除く）を href -> content の辞書にまとめる"""
    content = {}
    if not CONTENT_DIR.exists():
        return content
    for path in CONTENT_DIR.glob("*.json"):
        if path.stem.startswith("_"):
            continue
        items = json.loads(path.read_text(encoding="utf-8"))
        for it in items:
            href = it.get("href")
            if href:
                content[href] = it
    return content


def real_cards_html(cards):
    if not cards:
        return ""
    parts = []
    for c in cards:
        parts.append(
            f'<div class="card real-card"><h3><span aria-hidden="true">{esc(c.get("icon",""))}</span> {esc(c.get("title",""))}</h3>'
            f'<p>{esc(c.get("body",""))}</p></div>'
        )
    return f'<h2 class="sec">先に知っておきたいこと</h2><div class="grid">{"".join(parts)}</div>'


def qa_html(qa):
    if not qa:
        return ""
    parts = []
    for item in qa:
        # answerはHTML(<a>等)を含む想定のため、questionのみエスケープする
        parts.append(
            f'<details><summary>{esc(item.get("question",""))}</summary>'
            f'<p>{item.get("answer","")}</p></details>'
        )
    return f'<h2 class="sec">不安を先につぶすQ&amp;A</h2><div class="qa">{"".join(parts)}</div>'


def tabs_html(tabs):
    if not tabs:
        return ""
    tab_links = []
    panels = []
    for i, t in enumerate(tabs):
        tid = t.get("id", f"type-{i}")
        tab_links.append(f'<a href="#{esc(tid)}">{esc(t.get("label",""))}</a>')
        bullets = "".join(f"<li>{esc(b)}</li>" for b in t.get("bullets", []))
        actions = "".join(
            f'<a class="official-link" href="{esc(a.get("href",""))}"'
            + (' target="_blank" rel="noopener"' if a.get("href", "").startswith("http") else "")
            + f'>{esc(a.get("label",""))} <span>{esc(a.get("source",""))}</span></a>'
            for a in t.get("actions", [])
        )
        panels.append(
            f'<section class="type-panel" id="{esc(tid)}"><span class="label">{esc(t.get("label",""))}</span>'
            f'<h3>{esc(t.get("heading",""))}</h3><ul>{bullets}</ul>'
            f'<div class="type-actions">{actions}</div></section>'
        )
    return (
        '<h2 class="sec">タイプ別・最初の一歩</h2><p class="lead">あてはまるタイプを選ぶと、先に確認することと動けるリンクが表示されます。</p>'
        f'<div class="type-tabs" aria-label="状況を選ぶ">{"".join(tab_links)}</div>'
        f'<div class="type-panels">{"".join(panels)}</div>'
    )


def steps_html(steps):
    if not steps:
        return ""
    today = "".join(f"<li>{esc(s)}</li>" for s in steps.get("today", []))
    this_week = "".join(f"<li>{esc(s)}</li>" for s in steps.get("this_week", []))
    outside = "".join(f"<li>{esc(s)}</li>" for s in steps.get("outside", []))
    return (
        '<h2 class="sec">行動のステップ</h2><p class="lead">行動順と、市役所でできること／市役所以外で必要なことを分けています。</p>'
        '<div class="steps">'
        f'<div class="step today"><span class="label">今日やること</span><ul>{today}</ul></div>'
        f'<div class="step"><span class="label">今週〜後日やること</span><ul>{this_week}</ul></div>'
        f'<div class="step outside"><span class="label">市役所以外で必要なこと</span><ul>{outside}</ul></div>'
        "</div>"
    )


def action_grid_html(grid):
    if not grid:
        return ""
    links = []
    for a in grid:
        href = a.get("href", "")
        external = href.startswith("http")
        attr = ' target="_blank" rel="noopener"' if external else ""
        links.append(f'<a class="btn" href="{esc(href)}"{attr}>{esc(a.get("label",""))}</a>')
    return f'<h2 class="sec">今日動けること</h2><div class="action-grid">{"".join(links)}</div>'


def facts_html(facts):
    if not facts:
        return ""
    rows = []
    labels = json.loads((ROOT / 'data/fact-labels.json').read_text(encoding='utf-8'))
    for k, v in facts.items():
        if k not in labels:
            raise ValueError(f'公開用の日本語項目名が未登録です: {k}')
        rows.append(f'<dt>{esc(labels[k])}</dt><dd>{esc(v)}</dd>')
    return '<dl class="fact-list">' + "".join(rows) + '</dl>'


def sources_html(sources, city_name):
    if not sources:
        return f"<p class=\"mini\">出典URL未確定（{esc(city_name)}公式サイトでの個別確認が必要）</p>"
    links = []
    for s in sources:
        links.append(
            f'<a class="official-link" href="{esc(s["url"])}" target="_blank" rel="noopener">'
            f'{esc(s["label"])} <span>{esc(s.get("publisher", city_name + "公式"))}</span></a>'
        )
    return "".join(links)


def related_links_html(item, category_items):
    others = [i for i in category_items
              if i["href"] != item["href"] and i.get("status") in PUBLISHABLE_STATUSES][:8]
    if not others:
        return ""
    links = []
    for o in others:
        title = o.get("title") or o.get("title_iwata") or o["href"]
        links.append(f'<a class="official-link" href="{esc(o["href"])}">{esc(title)}</a>')
    return "".join(links)


def quick_guide_html(sections):
    if not sections:
        return ""
    blocks = []
    for section in sections:
        links = "".join(
            f'<li><a href="{esc(link["href"])}">{esc(link["label"])}</a></li>'
            for link in section["links"]
        )
        blocks.append(
            '<section class="guide-section">'
            f'<h2>{esc(section["heading"])}</h2><p>{esc(section["text"])}</p>'
            f'<ul class="link-list">{links}</ul></section>'
        )
    return "".join(blocks)


def cv_block_html(city):
    cv = city.get("cv", {})
    if not cv.get("kaigo_lead") and not cv.get("fudosan_link"):
        return ""
    cards = []
    if cv.get("kaigo_lead") or cv.get("fudosan_link"):
        cards.append(
            '<div class="company-card"><h3>介護・住まいの相談</h3>'
            f'<p>{esc(city["city_name"])}で、介護施設さがしや高齢の親の住まいについての相談をお受けしています。</p>'
            '<a class="official-link" href="https://www.fujigaoka-service.co.jp/" target="_blank" rel="noopener" style="margin-top:8px">相談先を見る <span>富士ヶ丘サービス</span></a></div>'
        )
    if not cards:
        return ""
    return (
        '<div class="company-strip"><h2 class="sec" style="margin-top:0">迷ったときの相談先</h2>'
        f'<div class="company-grid">{"".join(cards)}</div></div>'
    )


def render_page(item, city, category_items, content_map):
    title = item.get("search_title") or item.get("title") or item.get("title_iwata") or item["href"]
    city_name = city["city_name"]
    site_name = city["site_name"]
    category = item["category"]
    description = item.get("search_description") or (
        f"{city_name}の{category}に関する情報を整理する非公式ナビです。"
        f"最新・正確な情報は必ず{city_name}公式ページで確認してください。"
    )
    icon = CATEGORY_ICON.get(category, "")
    status = item.get("status", "draft")
    verified = status in PUBLISHABLE_STATUSES
    verified_date = item.get("verified_date") or item.get("ai_checked_date") or "確認中"
    update_html = ""
    verified_label = "最終確認日"
    if item.get("content_updated_date"):
        update_html = (f'<p class="content-updated">情報更新：{esc(item["content_updated_date"])}'
                       f' ／ 今回の確認範囲：{esc(item.get("update_scope", ""))}</p>')
        verified_label = "従来掲載内容の確認日"

    hub_href = min((i["href"] for i in category_items), key=len)
    is_hub = item["href"] == hub_href
    if is_hub:
        breadcrumb = f'<p class="breadcrumb"><a href="/">{esc(site_name)}</a> ／ <span aria-hidden="true">{esc(icon)}</span> {esc(category)}</p>'
    else:
        breadcrumb = (
            f'<p class="breadcrumb"><a href="/">{esc(site_name)}</a> ／ '
            f'<a href="{esc(hub_href)}"><span aria-hidden="true">{esc(icon)}</span> {esc(category)}</a> ／ {esc(title)}</p>'
        )

    content = content_map.get(item["href"])

    if content and content.get("lead"):
        lead = esc(content["lead"])
    else:
        facts = item.get("facts") or {}
        window = facts.get("window")
        if window:
            lead = f"{esc(city_name)}で「{esc(title)}」について確認するときの窓口は{esc(window)}です。詳細は下記の公式ページで確認してください。"
        else:
            lead = f"{esc(city_name)}の{esc(category)}に関する「{esc(title)}」について、公式ページの情報を整理しています。"

    note_html = f'<div class="note">{esc(content["note"])}</div>' if content and content.get("note") else ""
    rich_html = ""
    if content:
        rich_html = "".join([
            quick_guide_html(content.get("quick_guide")),
            real_cards_html(content.get("real_cards")),
            qa_html(content.get("qa")),
            tabs_html(content.get("tabs")),
            steps_html(content.get("steps")),
            action_grid_html(content.get("action_grid")),
        ])

    html = f"""<!doctype html><html lang="ja"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} | {esc(site_name)}</title>
<meta name="description" content="{esc(description)}">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<!-- PART:head-css:START --><link rel="stylesheet" href="/assets/site.css?v=20260702"><!-- PART:head-css:END --></head><body>
<!-- PART:header:START --><header class="site"><div class="wrap"><a class="logo" href="/">{esc(site_name)}</a></div></header><!-- PART:header:END -->
<!-- PART:disclaimer:START --><div class="disclaimer"><div class="wrap">{esc(site_name)}は{esc(city_name)}公式サイトではありません。最新・正確な情報は必ず公式ページで確認してください。</div></div><!-- PART:disclaimer:END -->
<main><div class="wrap">
{breadcrumb}
<section class="hero"><div class="hero-visual"><h1>{esc(title)}</h1></div><div class="hero-body"><p class="lead">{lead}</p></div></section>
{note_html}
{rich_html}
<h2 class="sec">公式窓口・確認先</h2><div class="official">{facts_html(item.get('facts'))}{sources_html(item.get('sources_omaezaki'), city_name)}</div>
<h2 class="sec">あわせて確認したい{esc(category)}のリンク</h2><div class="official">{related_links_html(item, category_items)}</div>
{cv_block_html(city)}
<section class="feedback-box" id="feedback"><h2 class="sec" style="margin-top:0">これで解決しそうですか？</h2><p class="mini" style="margin:0 0 10px">いただいた反応は、ページ改善のためだけに使います。お名前や連絡先は取得しません。</p><div class="fb-actions"><button type="button" class="fb-btn" data-feedback="solved">解決しそう</button><button type="button" class="fb-btn" data-feedback="still_worried">まだ不安</button><button type="button" class="fb-btn" data-feedback="could_not_find">探している情報がなかった</button></div><p class="fb-thanks">ありがとうございました。いただいた声は今後のページ改善に役立てます。</p></section>
{update_html}
<p class="verified">{verified_label}：{esc(verified_date)} ／ 本ページは公式情報を整理したものです。最新・正確な情報は必ず{esc(city_name)}公式ページで確認してください。</p>
</div></main><!-- PART:footer:START --><!-- PART:footer:END -->
</body></html>
"""
    return html, verified


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--category")
    ap.add_argument("--updated-only", action="store_true", help="更新範囲を記録した項目のみ生成")
    ap.add_argument("--refresh-existing", action="store_true", help="既存の共通部品・canonical・導線を保持して本文と出典を更新")
    args = ap.parse_args()

    ledger, city = load()
    content_map = load_content_map()
    items = [i for i in ledger if (not args.category or i["category"] == args.category)
             and (not args.updated_only or i.get("content_updated_date"))]

    by_category = {}
    for i in ledger:
        by_category.setdefault(i["category"], []).append(i)

    n_staged = n_published = n_rich = 0
    for item in items:
        html, verified = render_page(item, city, by_category[item["category"]], content_map)
        if item["href"] in content_map:
            n_rich += 1
        rel = item["href"].strip("/")  # 例: life/education/after-school-club
        out_base = ROOT if verified else STAGING_DIR
        out_path = out_base / rel / "index.html"
        if args.refresh_existing and out_path.exists():
            previous = out_path.read_text(encoding="utf-8")
            # 独立に管理されているヘッダー、canonical、相談導線、フッター等はそのまま保持。
            pattern = r'<section class="hero">.*?(?=<h2 class="sec">あわせて確認したい)'
            fresh = re.search(pattern, html, re.S)
            if not fresh or not re.search(pattern, previous, re.S):
                raise ValueError(f"本文更新境界が見つかりません: {out_path}")
            old_title = re.search(r'<h1>(.*?)</h1>', previous, re.S)
            new_title = re.search(r'<h1>(.*?)</h1>', html, re.S)
            previous = re.sub(pattern, lambda m: fresh.group(0), previous, count=1, flags=re.S)
            if old_title and new_title and old_title.group(1) != new_title.group(1):
                previous = previous.replace(old_title.group(1), new_title.group(1))
            if item.get("search_title") and item.get("search_description"):
                for metadata in (r"<title>.*?</title>", r'<meta name="description" content="[^"]*">'):
                    fresh_metadata = re.search(metadata, html, re.S).group(0)
                    previous, count = re.subn(metadata, lambda m: fresh_metadata, previous, count=1, flags=re.S)
                    if count != 1:
                        raise ValueError(f"検索用の情報が見つかりません: {out_path}")
            if item.get("content_updated_date"):
                update = (f'<p class="content-updated">情報更新：{esc(item["content_updated_date"])}'
                          f' ／ 今回の確認範囲：{esc(item.get("update_scope", ""))}</p>')
                previous = re.sub(r'<p class="content-updated">.*?</p>\s*', '', previous, flags=re.S)
                previous = previous.replace('<p class="verified">', update + '\n<p class="verified">', 1)
                previous = previous.replace('<p class="verified">最終確認日：', '<p class="verified">従来掲載内容の確認日：', 1)
            html = previous
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(html, encoding="utf-8", newline="\n")
        if verified:
            n_published += 1
        else:
            n_staged += 1

    print(f"生成完了: life/ へ {n_published}件・_staging/ へ {n_staged}件（うち本文リッチ化済み {n_rich}件）")
    if n_published == 0:
        print("注意: human-verified以上の項目が0件のため、life/ には何も出力されていません。")


if __name__ == "__main__":
    main()

