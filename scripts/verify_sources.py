#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_sources.py — 台帳(topics_master.json)の掛川出典URLとfactsを
御前崎市公式ページ本文と自動突合する機械検証スクリプト。

方針（袋井版で確定した全市共通ルールを継承）:
  御前崎市役所およびWEBから取れる事実だけを掲載する。
  機械突合で確認できた事実 → そのまま掲載可（status: machine-verified）
  確認できない事実         → 値を「確認中」にする（掲載時も「確認中」と表示）
  人力検証ゲートは廃止。人の役割は mismatch レポートの確認のみ。

検証内容（URL1本ごと）:
  1) HTTP 200 で取得できるか（301/302は遷移先を記録して追跡）
  2) ページ<title>にラベルの主要語が含まれるか（取り違え検知）
     ※ ドメイン直下のトップページは装飾的ラベルが付くだけで<title>と一致しないため対象外
  3) facts内の電話番号・金額・時間等の文字列が本文に実在するか
  4) 本文から電話番号を自動抽出し、facts未登録の番号を候補として記録

判定:
  全URL 200 かつ 電話番号系factsが全て本文一致 → status: machine-verified
  一部不一致・未取得                         → status: ai-checked のまま、
                                               該当factに「確認中」を付与し
                                               reports/verify-YYYYMMDD.md に理由を出力

実行: python3 scripts/verify_sources.py [--category 親のこと] [--all]
     リクエスト間隔0.5秒・UA明示・タイムアウト15秒・リトライ1回。
     PDFはスキップし該当factを確認中にする（本文突合はHTMLのみ）。
"""
import json, re, sys, time, argparse, urllib.request, urllib.error
from datetime import date
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlparse

LEDGER = Path('data/topics_master.json')
REPORT_DIR = Path('reports')
UA = 'enshu-lifehack-verify/1.0 (+https://omaezaki.enshu-lifehack.com/)'
WAIT = 0.5
KAKUNIN = '確認中'

TEL_RE = re.compile(r'0\d{1,4}[-−ー–]\d{1,4}[-−ー–]\d{3,4}')

class TextExtract(HTMLParser):
    def __init__(self):
        super().__init__(); self.buf = []; self.title = ''; self._in_title = False; self._skip = 0
    def handle_starttag(self, tag, attrs):
        if tag == 'title': self._in_title = True
        if tag in ('script', 'style'): self._skip += 1
    def handle_endtag(self, tag):
        if tag == 'title': self._in_title = False
        if tag in ('script', 'style') and self._skip: self._skip -= 1
    def handle_data(self, d):
        if self._in_title: self.title += d
        elif not self._skip: self.buf.append(d)
    @property
    def text(self): return re.sub(r'\s+', ' ', ' '.join(self.buf))

def norm(s: str) -> str:
    """全角数字・各種ハイフンを正規化して突合精度を上げる"""
    t = str(s).translate(str.maketrans('０１２３４５６７８９：〜', '0123456789:~'))
    return re.sub(r'[-−ー–―]', '-', t)

def fetch(url: str):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                final = r.geturl()
                ctype = r.headers.get('Content-Type', '')
                if 'pdf' in ctype.lower() or url.lower().endswith('.pdf'):
                    return {'status': r.status, 'final': final, 'pdf': True, 'text': '', 'title': ''}
                body = r.read().decode('utf-8', errors='replace')
                p = TextExtract(); p.feed(body)
                return {'status': r.status, 'final': final, 'pdf': False,
                        'text': norm(p.text), 'title': p.title.strip()}
        except urllib.error.HTTPError as e:
            return {'status': e.code, 'final': url, 'pdf': False, 'text': '', 'title': ''}
        except Exception as e:
            if attempt == 0:
                time.sleep(2); continue
            return {'status': 0, 'final': url, 'pdf': False, 'text': '', 'title': '', 'error': str(e)}

def label_keywords(label: str):
    """ラベルから取り違え検知用の主要語を抽出（括弧・注記を除去し2文字以上の語）"""
    base = re.sub(r'[（(※].*', '', label)
    words = re.findall(r'[ぁ-んァ-ヶ一-龥a-zA-Z]{2,}', base)
    return words[:3]

def iter_fact_tokens(facts):
    """facts内の突合対象トークン（電話番号・金額・時間表現）を列挙。確認中は対象外。"""
    def walk(v, path):
        if isinstance(v, dict):
            for k, x in v.items(): yield from walk(x, path + [k])
        elif isinstance(v, list):
            for i, x in enumerate(v): yield from walk(x, path + [str(i)])
        else:
            s = str(v)
            if KAKUNIN in s: return
            for tel in TEL_RE.findall(norm(s)):
                yield ('.'.join(path), tel)
            for money in re.findall(r'\d{2,3},?\d{3}円|\d{2,4}円', norm(s)):
                yield ('.'.join(path), money)
    yield from walk(facts, [])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--category'); ap.add_argument('--all', action='store_true')
    args = ap.parse_args()

    ledger = json.loads(LEDGER.read_text(encoding='utf-8'))
    targets = [i for i in ledger if i.get('status') == 'ai-checked'
               and (args.all or not args.category or i['category'] == args.category)]
    if not targets:
        print('対象なし（status=ai-checked の項目がありません）'); return 0

    REPORT_DIR.mkdir(exist_ok=True)
    today = str(date.today())
    lines = [f'# 機械検証レポート {today}', '']
    page_cache = {}
    ok_items = mismatch_items = 0

    for item in targets:
        lines.append(f"## {item['title_iwata']}  ({item['href']})")
        all_url_ok, notes = True, []
        corpus = ''  # この項目の全ページ本文を連結してfactsを突合
        for s in item.get('sources_omaezaki', []):
            url = s['url']
            if url not in page_cache:
                page_cache[url] = fetch(url); time.sleep(WAIT)
            r = page_cache[url]
            if r['status'] != 200:
                all_url_ok = False
                notes.append(f"- ❌ HTTP {r['status']}: {url}")
                continue
            if r['final'].split('#')[0] != url.split('#')[0]:
                notes.append(f"- ↪ リダイレクト: {url} → {r['final']}（台帳の差し替え候補）")
            if r['pdf']:
                notes.append(f"- ⏭ PDFのためスキップ（本文突合対象外）: {url}")
                continue
            is_site_root = urlparse(url).path in ('', '/')
            kws = label_keywords(s.get('label', ''))
            hit = [k for k in kws if k in r['title'] or k in r['text']]
            if kws and not hit and not is_site_root:
                all_url_ok = False
                notes.append(f"- ⚠ ラベル語不一致（取り違えの可能性）: 「{s['label']}」 vs <title>{r['title']}> : {url}")
            corpus += ' ' + r['text']

        fact_ok, fact_ng = [], []
        for path, token in iter_fact_tokens(item.get('facts', {})):
            (fact_ok if token in corpus else fact_ng).append((path, token))
        for path, token in fact_ng:
            notes.append(f"- ⚠ facts不一致: {path} = {token} が公式本文に見つからず → 確認中に変更")
            # 該当factを確認中に落とす（最上位キーのみ簡易対応）
            key = path.split('.')[0]
            if key in item['facts'] and isinstance(item['facts'][key], str):
                item['facts'][key] += f'（{KAKUNIN}: 本文未確認 {token}）'
        found_tels = set(TEL_RE.findall(corpus))
        known_tels = {t for _, t in fact_ok} | {t for _, t in fact_ng}
        extra = sorted(found_tels - known_tels)[:5]
        if extra:
            notes.append(f"- ℹ 本文から追加抽出した電話番号候補: {', '.join(extra)}")

        if all_url_ok and not fact_ng:
            item['status'] = 'machine-verified'
            item['verified_date'] = today
            item['verified_by'] = 'machine'
            ok_items += 1
            lines.append(f"- ✅ machine-verified（URL {len(item.get('sources_omaezaki', []))}本・facts一致 {len(fact_ok)}件）")
        else:
            mismatch_items += 1
        lines += notes + ['']

    LEDGER.write_text(json.dumps(ledger, ensure_ascii=False, indent=1), encoding='utf-8')
    rp = REPORT_DIR / f'verify-{today.replace("-", "")}.md'
    lines.insert(2, f'結果: machine-verified {ok_items}件 ／ 要確認 {mismatch_items}件\n')
    rp.write_text('\n'.join(lines), encoding='utf-8')
    print(f'machine-verified: {ok_items} / 要確認: {mismatch_items} → {rp}')
    return 1 if mismatch_items else 0

if __name__ == '__main__':
    sys.exit(main())
