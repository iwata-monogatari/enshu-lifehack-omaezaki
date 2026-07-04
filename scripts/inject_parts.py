#!/usr/bin/env python3
"""共通部品(parts/*.html)を全HTMLのマーカー間へ一括反映する。

各HTML内の
  <!-- PART:<name>:START --> ... <!-- PART:<name>:END -->
を parts/<name>.html の内容で置換する。マーカーが無いページは対象外。
冪等: 2回目以降の実行では差分ゼロになる。

使い方: python3 scripts/inject_parts.py
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARTS_DIR = os.path.join(ROOT, "parts")
EXCLUDE_DIRS = ("parts", "tmp", "output", "scratchpad", "node_modules", ".git", ".wrangler", "docs")


def load_parts():
    parts = {}
    for path in sorted(glob.glob(os.path.join(PARTS_DIR, "*.html"))):
        name = os.path.splitext(os.path.basename(path))[0]
        with open(path, encoding="utf-8", newline="") as f:
            parts[name] = f.read().strip()
    return parts


def target_files():
    for path in sorted(glob.glob(os.path.join(ROOT, "**", "*.html"), recursive=True)):
        rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
        if rel.split("/")[0] in EXCLUDE_DIRS:
            continue
        yield path, rel


def main():
    parts = load_parts()
    if not parts:
        print("parts/ に部品がありません", file=sys.stderr)
        return 1
    changed = []
    total_markers = {name: 0 for name in parts}
    for path, rel in target_files():
        with open(path, encoding="utf-8", newline="") as f:
            html = f.read()
        new_html = html
        for name, content in parts.items():
            pattern = re.compile(
                r"<!-- PART:%s:START -->.*?<!-- PART:%s:END -->" % (re.escape(name), re.escape(name)),
                re.S,
            )
            replacement = "<!-- PART:%s:START -->%s<!-- PART:%s:END -->" % (name, content, name)
            new_html, n = pattern.subn(lambda m: replacement, new_html)
            total_markers[name] += n
        if new_html != html:
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(new_html)
            changed.append(rel)
    for name in sorted(total_markers):
        print("part '%s': マーカー %d 箇所" % (name, total_markers[name]))
    if changed:
        print("更新 %d ファイル:" % len(changed))
        for rel in changed:
            print("  " + rel)
    else:
        print("更新 0 ファイル（全ページ最新・冪等OK）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
