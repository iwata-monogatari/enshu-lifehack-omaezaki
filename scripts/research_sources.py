#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
research_sources.py — 御前崎市公式サイトをクロールしてページインベントリを作り、
台帳(topics_master.json)のdraft項目に出典URL候補を自動マッチングする。

工程（袋井版で確立した「AI下調べ」の機械化方針を継承）:
  1) クロール: www.city.omaezaki.shizuoka.jp をトップからBFSで巡回し、
     全HTMLページの URL・<title>・見出し(h1) を data/omaezaki_pages.json に保存。
     礼法: 間隔0.5秒・UA明示・robots.txt尊重・HTMLのみ(PDF等はURLだけ記録)。
     中断再開可（キャッシュに追記）。目安30〜60分/初回、2回目以降は差分のみ。
  2) マッチング: 各draft項目の (title_iwata + synonyms + 磐田側ラベル語) と
     インベントリの (title + h1) のトークン重なりをスコア化し、
     上位候補(スコア閾値以上・最大4本)を sources_omaezaki に登録 → status: ai-checked。
     候補ゼロの項目は facts に「確認中（対応ページ候補なし）」を付与。
  3) 出力: data/topics_master.json 更新 ＋ reports/research-YYYYMMDD.md
     （項目ごとの候補とスコア一覧。チャット側レビュー用）
  4) 続けて verify_sources.py を実行すれば、候補URLの実在・本文突合まで自動。

注意: 自動マッチングは誤マッチが一定数発生する（袋井版での実績で確認済み）。
      ai-checked止まりの項目は必ずWebSearch/WebFetch等で人力再調査すること。

実行:
  python3 scripts/research_sources.py --crawl          # インベントリ構築(初回)
  python3 scripts/research_sources.py --match --all    # 全draft項目をマッチング
  python3 scripts/research_sources.py --match --category 家・住まい
"""
import json, re, sys, time, argparse, urllib.request, urllib.error, urllib.robotparser
from collections import deque
from datetime import date
from pathlib import Path
from html.parser import HTMLParser

BASE = 'https://www.city.omaezaki.shizuoka.jp'
LEDGER = Path('data/topics_master.json')
INVENTORY = Path('data/omaezaki_pages.json')
REPORT_DIR = Path('reports')
UA = 'enshu-lifehack-research/1.0 (+https://omaezaki.enshu-lifehack.com/)'
WAIT = 0.5
MAX_PAGES = 6000
SCORE_MIN = 3          # 採用最低スコア(ストップワード除去後の固有語一致数)
MAX_SOURCES = 4        # 1項目あたりの候補上限
KAKUNIN = '確認中'

STOP = set(('御前崎市 磐田 磐田市 について ご案内 案内 一覧 情報 お知らせ ページ ホーム サイト 公式 '
            '相談 支援 申請 手続 手続き 利用 確認 サービス 制度 窓口 センター 事業 対応 実施 受付 登録 '
            'まず 整理 先に 分ける 進める 始める 確かめる 迷わず 困った 困らず する ある いる こと もの ため よう').split())

class PageParse(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title=''; self.h1=''; self.links=[]
        self._in=None; self._skip=0
    def handle_starttag(self, tag, attrs):
        d=dict(attrs)
        if tag=='title': self._in='title'
        elif tag=='h1': self._in='h1'
        elif tag in ('script','style'): self._skip+=1
        if tag=='a' and d.get('href'): self.links.append(d['href'])
    def handle_endtag(self, tag):
        if tag in ('title','h1'): self._in=None
        if tag in ('script','style') and self._skip: self._skip-=1
    def handle_data(self, data):
        if self._skip: return
        if self._in=='title': self.title+=data
        elif self._in=='h1': self.h1+=data

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            ct = r.headers.get('Content-Type','')
            if 'html' not in ct.lower():
                return None
            return r.read().decode('utf-8', errors='replace')
    except Exception:
        return None

def crawl():
    rp = urllib.robotparser.RobotFileParser(BASE + '/robots.txt')
    try: rp.read()
    except Exception: rp = None
    inv = json.loads(INVENTORY.read_text(encoding='utf-8')) if INVENTORY.exists() else {}
    seen = set(inv.keys())
    q = deque([BASE + '/'])
    skip_ext = re.compile(r'\.(pdf|docx?|xlsx?|pptx?|zip|jpe?g|png|gif|csv|rtf|mp4)(\?|$)', re.I)
    n_fetched = 0
    while q and len(inv) < MAX_PAGES:
        url = q.popleft()
        url = url.split('#')[0]
        if url in seen or not url.startswith(BASE): continue
        if skip_ext.search(url): seen.add(url); continue
        if rp and not rp.can_fetch(UA, url): seen.add(url); continue
        seen.add(url)
        body = fetch(url); time.sleep(WAIT); n_fetched += 1
        if body is None: continue
        p = PageParse()
        try: p.feed(body)
        except Exception: continue
        inv[url] = {'title': re.sub(r'\s+',' ',p.title).strip(),
                    'h1': re.sub(r'\s+',' ',p.h1).strip()}
        for href in p.links:
            if href.startswith('/'): href = BASE + href
            if href.startswith(BASE): q.append(href)
        if n_fetched % 200 == 0:
            INVENTORY.write_text(json.dumps(inv, ensure_ascii=False), encoding='utf-8')
            print(f'  …{len(inv)}ページ収集 (キュー残{len(q)})')
    INVENTORY.write_text(json.dumps(inv, ensure_ascii=False), encoding='utf-8')
    print(f'クロール完了: {len(inv)}ページ → {INVENTORY}')

def tokens(*texts):
    out=set()
    for t in texts:
        if not t: continue
        t = re.sub(r'[（(※].*?[)）]', '', str(t))
        for w in re.findall(r'[ァ-ヶ一-龥]{2,}', t):
            for i in range(len(w)-1):
                out.add(w[i:i+2])          # 漢字/カナ2-gramで表記揺れに強く
            if len(w)>=2 and w not in STOP: out.add(w)
    return out - STOP

def match(args):
    if not INVENTORY.exists():
        print('先に --crawl を実行してください'); return 1
    inv = json.loads(INVENTORY.read_text(encoding='utf-8'))
    pages = [(u, d, tokens(d['title'], d['h1'])) for u, d in inv.items() if d.get('title')]
    ledger = json.loads(LEDGER.read_text(encoding='utf-8'))
    today = str(date.today())
    REPORT_DIR.mkdir(exist_ok=True)
    lines = [f'# 出典自動マッチングレポート {today}', '']
    n_ok = n_none = 0
    for item in ledger:
        if item.get('status') != 'draft': continue
        if not args.all and args.category and item['category'] != args.category: continue
        qtok = tokens(item['title_iwata'], *item.get('synonyms', []),
                      *[s['label'] for s in item.get('source_iwata', [])])
        scored = []
        for u, d, ptok in pages:
            sc = len(qtok & ptok)
            if sc >= SCORE_MIN: scored.append((sc, u, d['title']))
        scored.sort(reverse=True)
        if scored:
            top = scored[0][0]
            scored = [x for x in scored if x[0]*2 >= top]  # 首位の半分未満は除外
        lines.append(f"## {item['title_iwata']} ({item['href']})")
        if scored:
            item['sources_omaezaki'] = [
                {'url': u, 'label': t, 'match_score': sc,
                 'confidence': 'high' if sc >= 5 else 'low'}
                for sc, u, t in scored[:MAX_SOURCES]]
            item['status'] = 'ai-checked'
            item['ai_checked_date'] = today
            item['ai_notes'] = ('自動マッチング候補。verify_sources.pyで本文突合すること。'
                + ('【低信頼候補を含む・チャット側レビュー必須】' if any(x[0] < 5 for x in scored[:MAX_SOURCES]) else ''))
            n_ok += 1
            for sc, u, t in scored[:MAX_SOURCES]:
                mark = '' if sc >= 5 else ' ⚠低信頼'
                lines.append(f'- [{sc}]{mark} {t} : {u}')
        else:
            item.setdefault('facts', {})['taiou_page'] = f'{KAKUNIN}（対応ページ候補なし・チャット側で個別調査）'
            n_none += 1
            lines.append(f'- 候補なし → {KAKUNIN}')
        lines.append('')
    LEDGER.write_text(json.dumps(ledger, ensure_ascii=False, indent=1), encoding='utf-8')
    rp = REPORT_DIR / f"research-{today.replace('-','')}.md"
    lines.insert(2, f'結果: 候補あり {n_ok}件 ／ 候補なし {n_none}件\n')
    rp.write_text('\n'.join(lines), encoding='utf-8')
    print(f'マッチング完了: 候補あり {n_ok} / 候補なし {n_none} → {rp}')
    return 0

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--crawl', action='store_true')
    ap.add_argument('--match', action='store_true')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--category')
    a = ap.parse_args()
    if a.crawl: crawl()
    if a.match: sys.exit(match(a))
    if not (a.crawl or a.match): print(__doc__)
