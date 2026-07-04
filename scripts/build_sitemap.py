#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""topics_master.json + トップページ/利用規約からsitemap.xmlを生成する。
実行: python3 scripts/build_sitemap.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = 'https://omaezaki.enshu-lifehack.com'
PUBLISHABLE_STATUSES = ('ai-checked', 'machine-verified', 'human-verified', 'published')

def main():
    ledger = json.loads((ROOT / 'data/topics_master.json').read_text(encoding='utf-8'))
    published = [t for t in ledger if t.get('status') in PUBLISHABLE_STATUSES]
    urls = ['/', '/terms/'] + sorted(t['href'] for t in published)
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        lines.append(f'<url><loc>{SITE}{u}</loc></url>')
    lines.append('</urlset>')
    out = ROOT / 'sitemap.xml'
    out.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'生成完了: {out}（{len(urls)}件）')

if __name__ == '__main__':
    main()
