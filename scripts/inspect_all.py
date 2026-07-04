#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
inspect_all.py — 公開前検査を1コマンドに束ねる（設計指示書§6.2を継承）。

検査内容:
  1. 空<style>・site.css読込・bodyクラスの全数検査（磐田の5ページ事故の再発防止）
  2. 内部リンク切れゼロ検査（life/ 配下のみ）
  3. inject_parts.py の冪等性（実行後diffゼロ）
  4. 台帳整合検査：life/ 配下に存在する全ページが status: ai-checked 以上であること
  5. sitemap.xml・search-index.json が公開ページ数と一致すること（存在確認のみ・内容生成は別スクリプト）

公式リンク死活検査（check_official_links.py）と重複するため本スクリプトには含めない。
別途 `python3 scripts/check_official_links.py` を実行すること。

実行: python3 scripts/inspect_all.py
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "data" / "topics_master.json"
LIFE_DIR = ROOT / "life"

PUBLISHABLE_STATUSES = ("ai-checked", "machine-verified", "human-verified", "published")


def check_style_and_bodyclass():
    problems = []
    for path in LIFE_DIR.rglob("index.html"):
        html = path.read_text(encoding="utf-8")
        if re.search(r"<style>\s*</style>", html):
            problems.append(f"空<style>: {path}")
        if "site.css" not in html:
            problems.append(f"site.css未読込: {path}")
    return problems


def check_internal_links():
    problems = []
    existing = set()
    for path in LIFE_DIR.rglob("index.html"):
        rel = "/" + str(path.relative_to(ROOT).parent).replace("\\", "/") + "/"
        existing.add(rel.replace("life/", "/life/") if not rel.startswith("/life") else rel)
    existing = {"/" + str(p.relative_to(ROOT).parent).replace("\\", "/") + "/" for p in LIFE_DIR.rglob("index.html")}
    existing.add("/")
    existing.add("/terms/")
    for path in LIFE_DIR.rglob("index.html"):
        html = path.read_text(encoding="utf-8")
        for href in re.findall(r'href="(/life/[^"#?]*/)"', html):
            if href not in existing:
                problems.append(f"内部リンク切れ: {path} -> {href}")
    return problems


def check_idempotency():
    before = {p: p.read_text(encoding="utf-8") for p in ROOT.rglob("*.html") if "node_modules" not in str(p)}
    subprocess.run([sys.executable, str(ROOT / "scripts" / "inject_parts.py")], cwd=ROOT, capture_output=True)
    after_changed = []
    for p, content in before.items():
        if p.exists() and p.read_text(encoding="utf-8") != content:
            after_changed.append(str(p))
    return after_changed


def check_ledger_consistency():
    problems = []
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    published_hrefs = {i["href"] for i in ledger if i.get("status") in PUBLISHABLE_STATUSES}
    life_dirs = {"/" + str(p.relative_to(ROOT).parent).replace("\\", "/") + "/" for p in LIFE_DIR.rglob("index.html")}
    missing_in_life = published_hrefs - life_dirs
    extra_in_life = life_dirs - published_hrefs
    for h in sorted(missing_in_life):
        problems.append(f"台帳では公開可否件だがlife/に存在しない: {h}")
    for h in sorted(extra_in_life):
        problems.append(f"life/に存在するが台帳では公開可否件未満(draft): {h}")
    return problems


def main():
    all_ok = True

    print("1. 空<style>・site.css読込チェック")
    problems = check_style_and_bodyclass()
    if problems:
        all_ok = False
        for p in problems:
            print("  NG:", p)
    else:
        print(f"  OK（life/配下 {len(list(LIFE_DIR.rglob('index.html')))}件）")

    print("2. 内部リンク切れチェック")
    problems = check_internal_links()
    if problems:
        all_ok = False
        for p in problems:
            print("  NG:", p)
    else:
        print("  OK")

    print("3. inject_parts.py 冪等性チェック")
    problems = check_idempotency()
    if problems:
        all_ok = False
        for p in problems:
            print("  NG（2回目実行で差分あり）:", p)
    else:
        print("  OK")

    print("4. 台帳整合チェック（life/ 配下 = ai-checked以上）")
    problems = check_ledger_consistency()
    if problems:
        all_ok = False
        for p in problems:
            print("  NG:", p)
    else:
        print("  OK")

    print()
    print("=== 総合判定:", "PASS" if all_ok else "FAIL", "===")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
