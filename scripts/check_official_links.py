#!/usr/bin/env python3
"""公式リンク死活監視。

全HTMLから href="https://..." の外部リンクを抽出・重複排除し、
HEAD(失敗時GETフォールバック)で到達性を確認して
reports/link-check-YYYYMMDD.md にレポートを出力する。

- タイムアウト10秒 / リトライ1回 / リクエスト間隔0.5秒(市サイトへの配慮)
- User-Agent: enshu-lifehack-linkcheck/1.0
- 分類: OK(2xx) / リダイレクト(3xx→遷移先併記) / エラー(4xx,5xx) / タイムアウト・接続不可
- エラー(4xx/5xx/接続不可)が1件以上あれば exit code 1 (CI組み込み用)

使い方: python3 scripts/check_official_links.py
"""
import datetime
import glob
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXCLUDE_DIRS = ("parts", "tmp", "output", "scratchpad", "node_modules", ".git", ".wrangler", "docs", "reports")
TIMEOUT = 10
INTERVAL = 0.5
UA = "enshu-lifehack-linkcheck/1.0"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


OPENER = urllib.request.build_opener(NoRedirect)


def collect_links():
    """{url: set(ページ相対パス)}"""
    url_pages = defaultdict(set)
    for path in sorted(glob.glob(os.path.join(ROOT, "**", "*.html"), recursive=True)):
        rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
        if rel.split("/")[0] in EXCLUDE_DIRS:
            continue
        with open(path, encoding="utf-8") as f:
            html = f.read()
        for m in re.finditer(r'href="(https://[^"]+)"', html):
            url_pages[m.group(1)].add(rel)
    return url_pages


def request_once(url, method):
    req = urllib.request.Request(url, method=method, headers={"User-Agent": UA})
    try:
        with OPENER.open(req, timeout=TIMEOUT) as res:
            return res.status, None
    except urllib.error.HTTPError as e:
        if e.code in (301, 302, 303, 307, 308):
            return e.code, e.headers.get("Location", "(Location不明)")
        return e.code, None
    except Exception as e:
        return None, str(e)[:120]


def check(url):
    """(分類, ステータス/理由, 遷移先) 分類: ok/redirect/error/unreachable"""
    for attempt in range(2):  # リトライ1回
        status, extra = request_once(url, "HEAD")
        if status is not None and status >= 400:
            time.sleep(INTERVAL)
            status, extra = request_once(url, "GET")  # HEAD拒否(405/403等)フォールバック
        if status is None:
            if attempt == 0:
                time.sleep(INTERVAL)
                continue
            return "unreachable", extra, None
        if 200 <= status < 300:
            return "ok", status, None
        if status in (301, 302, 303, 307, 308):
            return "redirect", status, extra
        return "error", status, None
    return "unreachable", extra, None


def main():
    url_pages = collect_links()
    urls = sorted(url_pages)
    print("外部リンク %d 本(ユニーク)を検査します" % len(urls))
    results = {}
    for i, url in enumerate(urls, 1):
        results[url] = check(url)
        cat = results[url][0]
        if cat != "ok":
            print("  [%s] %s %s" % (cat, results[url][1], url))
        if i % 25 == 0:
            print("  ... %d/%d" % (i, len(urls)))
        time.sleep(INTERVAL)

    today = datetime.date.today().strftime("%Y%m%d")
    os.makedirs(os.path.join(ROOT, "reports"), exist_ok=True)
    report_path = os.path.join(ROOT, "reports", "link-check-%s.md" % today)

    ok = [u for u in urls if results[u][0] == "ok"]
    redirects = [u for u in urls if results[u][0] == "redirect"]
    errors = [u for u in urls if results[u][0] == "error"]
    unreachable = [u for u in urls if results[u][0] == "unreachable"]

    lines = []
    lines.append("# 公式リンク死活チェック %s" % datetime.date.today().isoformat())
    lines.append("")
    lines.append("| 分類 | 件数 |")
    lines.append("|---|---|")
    lines.append("| OK (2xx) | %d |" % len(ok))
    lines.append("| リダイレクト (3xx) | %d |" % len(redirects))
    lines.append("| エラー (4xx/5xx) | %d |" % len(errors))
    lines.append("| タイムアウト・接続不可 | %d |" % len(unreachable))
    lines.append("| 合計(ユニークURL) | %d |" % len(urls))
    lines.append("")
    if redirects:
        lines.append("## リダイレクト (遷移先の確認・差し替え候補)")
        lines.append("")
        for u in redirects:
            cat, status, loc = results[u]
            lines.append("- [%s] %s" % (status, u))
            lines.append("  - → %s" % loc)
            lines.append("  - 使用ページ: %s" % ", ".join(sorted(url_pages[u])))
        lines.append("")
    if errors or unreachable:
        lines.append("## エラー・接続不可 (要対応)")
        lines.append("")
        for u in errors + unreachable:
            cat, status, _ = results[u]
            lines.append("- [%s] %s" % (status, u))
            lines.append("  - 使用ページ: %s" % ", ".join(sorted(url_pages[u])))
        lines.append("")
        lines.append("### ページ別逆引き")
        lines.append("")
        page_errors = defaultdict(list)
        for u in errors + unreachable:
            for p in url_pages[u]:
                page_errors[p].append(u)
        for p in sorted(page_errors):
            lines.append("- %s" % p)
            for u in page_errors[p]:
                lines.append("  - [%s] %s" % (results[u][1], u))
        lines.append("")
    if not (errors or unreachable):
        lines.append("エラーはありません。")
        lines.append("")

    with open(report_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))
    print("レポート出力:", os.path.relpath(report_path, ROOT))
    print("OK %d / リダイレクト %d / エラー %d / 接続不可 %d" % (len(ok), len(redirects), len(errors), len(unreachable)))
    return 1 if (errors or unreachable) else 0


if __name__ == "__main__":
    sys.exit(main())
