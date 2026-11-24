#!/usr/bin/env python3
"""Build curated guides, search tools, checklists and the home page from reviewed data."""
import json,re,html,hashlib
from urllib.parse import quote
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timedelta, timezone
ROOT=Path(__file__).resolve().parent.parent
SITE='https://omaezaki.enshu-lifehack.com';DATE='2026-11-21'
def read(name,default=None):
 p=ROOT/'data'/name
 return json.loads(p.read_text(encoding='utf-8')) if p.exists() else default
def esc(v):return html.escape(str(v or ''),quote=True)
def write(href,content):
 p=ROOT/(href.strip('/')+'/index.html' if href!='/' else 'index.html');p.parent.mkdir(parents=True,exist_ok=True);p.write_text(content,encoding='utf-8',newline='\n')
def part(name):return (ROOT/'parts'/f'{name}.html').read_text(encoding='utf-8').strip()
def marker(name):return f'<!-- PART:{name}:START -->{part(name)}<!-- PART:{name}:END -->'
NAV=[('/guide/','手続き・暮らし'),('/discover/','御前崎を知る'),('/places/','施設を探す'),('/questions/','質問から探す'),('/checklists/','チェックリスト'),('/updates/','最新の案内')]
manifest=[]
def navlinks():return ''.join(f'<a href="{href}">{label}</a>' for href,label in NAV)
def page(href,title,lead,body,category='暮らしガイド',icon='📖',home=False):
 meta={'href':href,'title':title,'lead':lead,'category':category,'icon':icon,'synonyms':[]}
 if href!='/':manifest.append(meta)
 classes='hub home enriched-home' if home else 'enriched-page'
 intro='' if home else f'<nav class="breadcrumb" aria-label="現在地"><a href="/">御前崎ライフハック</a> ／ {esc(category)}</nav><div class="page-intro"><p class="kicker">{esc(category)}</p><h1>{esc(title)}</h1><p class="lead">{esc(lead)}</p></div>'
 footer=marker('footer')
 # Footer source already contains the shared analytics tag. Do not add a second copy.
 return f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)} | 御前崎ライフハック</title><meta name="description" content="{esc(lead)}"><link rel="canonical" href="{SITE}{href}"><link rel="icon" href="/favicon.svg" type="image/svg+xml">{marker('head-css')}<meta property="og:type" content="website"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(lead)}"><meta property="og:url" content="{SITE}{href}"></head><body class="{classes}"><a class="skip-link" href="#main-content">本文へ進む</a>{marker('header')}{marker('disclaimer')}<main id="main-content"><div class="wrap">{intro}{body}</div></main><nav class="enrichment-footer-nav" aria-label="主な案内"><div class="wrap">{navlinks()}<a href="/about/">運営者・編集方針</a></div></nav>{footer}<script type="module" src="/assets/enrichment.js?v=20261121b"></script>{'<script type="module" src="/assets/search-app.js"></script>' if home else ''}</body></html>'''
def linklist(links):
 def item(link):
  tracked = f' data-track-click="{esc(link["track"])}"' if link.get('track') else ''
  return f'<li><a href="{esc(link["href"])}"{tracked}>{esc(link["label"])}</a></li>'
 return '<ul class="link-list">' + ''.join(item(link) for link in links) + '</ul>'
def card(href,title,text='',icon='📖',eyebrow='',image=None):
 return f'<a class="browse-card" href="{esc(href)}">'+(f'<img src="/assets/omaezaki/{image}.webp" alt="" width="600" height="400" loading="lazy">' if image else f'<span class="card-icon" aria-hidden="true">{icon}</span>')+(f'<span class="eyebrow">{esc(eyebrow)}</span>' if eyebrow else '')+f'<h3>{esc(title)}</h3><p>{esc(text)}</p><span class="card-action">詳しく見る</span></a>'
def album_note():
 links = [
  {"href":"https://omaezakialb.atawi.link/features/cape/","label":"御前埼灯台の昔の写真","track":"photo_album_cape"},
  {"href":"https://omaezakialb.atawi.link/features/old-photos/","label":"御前崎の古写真・絵葉書","track":"photo_album_old_photos"},
  {"href":"https://omaezakialb.atawi.link/features/hamaoka/","label":"旧浜岡町の写真（池新田・佐倉・新野）","track":"photo_album_hamaoka"},
  {"href":"https://omaezakialb.atawi.link/features/port/","label":"御前崎港の昔の写真","track":"photo_album_port"},
  {"href":"https://omaezakialb.atawi.link/features/aerial/","label":"御前崎・浜岡の昔の航空写真","track":"photo_album_aerial"},
  {"href":"https://omaezakialb.atawi.link/features/sakuragaike/","label":"桜ヶ池のお櫃納めの古写真","track":"photo_album_sakuragaike"},
 ]
 return (
  '<section class="answer-first" id="photo-memories"><h2>写真でたどる、御前崎の記憶</h2>'
  '<p>いま訪ねたい場所の昔の姿を、御前崎懐かし写真館の写真で見てみませんか。撮影時期や出典は写真ごとに確認できます。</p>'
  + linklist(links) + '</section>'
 )

def sources(items, checked=DATE):
 return '<section class="sources-panel"><h2>公式の確認先</h2><p class="source-note">内容確認：'+esc(checked)+'。料金・受付・休業状況は、利用前に各公式窓口でご確認ください。</p><ul>'+''.join(f'<li><a href="{esc(x["url"])}" target="_blank" rel="noopener">{esc(x.get("label",x.get("title","公式案内")))}</a> — {esc(x.get("publisher",""))}</li>' for x in items)+'</ul></section>'
def photo(slug):
 credit=next(x for x in read('image-credits.json',[]) if x['slug']==slug)
 return f'<figure class="guide-photo"><img src="{credit["file"]}" alt="{esc(credit["title"].strip("【】"))}" width="1200" height="800" loading="lazy"><figcaption>写真：御前崎市「{esc(credit["title"])}」／<a href="{credit["source"]}">静岡県オープンデータ</a>／<a href="{credit["license_url"]}">CC BY 4.0</a>。縮小・形式変換。2018年公開の資料写真です。</figcaption></figure>'
def guide(g):
 href=g['href'];sections=[];toc=[]
 checked=g.get('checked', DATE)
 for i,s in enumerate(g['sections']):
  sid=f'section-{i+1}';toc.append(f'<a href="#{sid}">{esc(s["heading"])}</a>')
  body=''.join(f'<p>{esc(p)}</p>' for p in s.get('paragraphs',[]))
  items=s.get('items',s.get('bullets',[]))
  if items:body+='<ul>'+''.join(f'<li>{esc(p)}</li>' for p in items)+'</ul>'
  if s.get('links'):body+=linklist([{'href':x.get('href',x.get('url')),'label':x.get('label',x.get('title')),'track':x.get('track')} for x in s['links']])
  sections.append(f'<section class="guide-section" id="{sid}"><h2>{esc(s["heading"])}</h2>{body}</section>')
 qs=g.get('questions',g.get('qa',[]));qa=''
 if qs:qa='<section><h2>よくある質問</h2><div class="filter-results">'+''.join(f'<details><summary>{esc(q["question"])}</summary><p class="answer">{esc(q["answer"])}</p></details>' for q in qs)+'</div></section>'
 labels={**{h:t.get('search_title',t['title']) for h,t in TOPIC.items()},**{x['href']:x['title'] for x in GUIDES}}
 related=[{'href':h,'label':labels[h]} for h in g.get('related',[]) if h in labels]
 body=(photo(g['image']) if g.get('image') else '')+f'<div class="guide-layout"><article>'+(''.join(sections))+qa+(f'<h2>次に確認すること</h2>{linklist(related)}' if related else '')+sources(g['sources'], checked)+f'</article><aside class="guide-aside"><h2>このページで分かること</h2><nav>{"".join(toc)}</nav><p class="mini">確認：{esc(checked)}</p></aside></div>'
 write(href,page(href,g['title'],g['lead'],body,g['category'],g.get('icon','📖')))
 manifest[-1]['synonyms']=g.get('keywords',[])+g.get('tags',[])+[s['heading'] for s in g['sections']]
def checklist(c):
 href='/checklists/'+c['slug']+'/'
 items=''.join(f'<li class="check-item"><label><input type="checkbox" value="{esc(t["id"])}"><span>{esc(t["title"])}</span></label><p>{esc(t["description"])}</p><a class="task-link" href="{esc(t["href"])}">{esc(t.get("link_label","手続き・確認先を見る"))}</a></li>' for t in c['tasks'])
 body=f'<section data-checklist="{esc(c["slug"])}"><div class="check-progress"><p data-progress-label aria-live="polite">進捗を読み込んでいます</p><progress value="0" max="{len(c["tasks"])}" aria-label="確認した項目の割合"></progress></div><p class="mini" data-storage-note>チェック状態はこのブラウザに保存されます。住所・氏名などの入力は不要です。チェックしても行政への申請は行われません。</p><ol class="check-items">{items}</ol><div class="check-actions"><button type="button" data-print>印刷する</button><button type="button" data-reset>このチェックをすべて外す</button></div></section><p class="mini">各手続きの期限・対象条件は、リンク先の公式案内で確認してください。該当しない項目は飛ばせます。</p>'
 write(href,page(href,c['title'],c['lead'],body,'状況別チェックリスト',c.get('icon','✅')))
def browser(kind,title,lead,data,filename):
 categories=list(dict.fromkeys(x['category'] for x in data));options=''.join(f'<option value="{esc(c)}">{esc(c)}</option>' for c in categories)
 fallback='<h2>分野から探す</h2><div class="browse-grid">'+''.join(card('/life/'+x['href'].split('/')[2]+'/',x['category'],icon=x.get('icon','📖')) for x in LEDGER if x['href'].count('/')==3)+'</div>'
 if kind=='places':fallback='<h2>目的別のガイド</h2><div class="browse-grid">'+''.join(card(g['href'],g['title'],g['lead'],g.get('icon','📍')) for g in GUIDES if g['category']=='御前崎を知る')+'</div>'
 body=f'<section data-browser="{kind}" data-source="/data/{filename}"><form class="filter-panel" onsubmit="return false" role="search"><label>キーワード<input type="search" placeholder="{("灯台、子ども、白羽、休館" if kind=="places" else "水道、児童手当、親の介護")}" aria-label="キーワード"></label><label>分野<select aria-label="分野"><option value="">すべて</option>{options}</select></label><button type="button" data-clear>条件をクリア</button></form><p class="result-count" data-count role="status">検索データを読み込んでいます</p><div data-results class="{("place-grid" if kind=="places" else "filter-results")}"></div><button type="button" class="load-more" data-more hidden>続きを表示</button><noscript><p>検索にはJavaScriptを使用します。下の分野別リンクからも各案内へ進めます。</p></noscript></section>{fallback}'
 href='/places/' if kind=='places' else '/questions/'
 write(href,page(href,title,lead,body,'施設検索' if kind=='places' else '質問検索','📍' if kind=='places' else '💬'))

LEDGER=read('topics_master.json',[]);TOPIC={x['href']:x for x in LEDGER};GUIDES=read('enrichment-guides.json',[]);CHECKLISTS=read('checklists.json',[]);UPDATES=read('updates.json',[])
def current_update(update, today):
 return not update.get('end') or update['end'] >= today

def expiry_attribute(update):
 return f' data-update-end="{esc(update["end"])}"' if update.get('end') else ''

EXPIRY_SCRIPT = '<script type="module" src="/assets/update-expiry.js"></script>'

def update_html(update):
 sources = ''.join(
  f'<a href="{esc(source["url"])}" target="_blank" rel="noopener">{esc(source.get("label","公式案内"))}</a> '
  for source in update.get('sources', [])
 )
 return (
  f'<article class="update-card"{expiry_attribute(update)}>'
  f'<p class="update-meta">{esc(update.get("date",DATE))}確認 ／ {esc(update.get("status","案内"))}</p>'
  f'<h2><a href="{esc(update["href"])}">{esc(update["title"])}</a></h2>'
  f'<p>{esc(update["summary"])}</p>{sources}</article>'
 )

def main():
 for g in GUIDES:guide(g)
 for c in CHECKLISTS:checklist(c)
 bycat=defaultdict(list)
 for g in GUIDES:bycat[g['category']].append(g)
 for path,category,title,lead in [('/guide/','暮らしガイド','御前崎の手続き・暮らしガイド','申請の前に知りたい条件、持ち物、相談先を、今の状況から選べます。'),('/discover/','御前崎を知る','御前崎を知る・出かける','海辺、食、歴史、公園。場所を並べるだけでなく、訪問前の確認と組み合わせ方まで案内します。')]:
  body='<div class="browse-grid">'+''.join(card(g['href'],g['title'],g['lead'],g.get('icon','📖'),image=g.get('image')) for g in bycat[category])+'</div>'
  if path=='/guide/':
   body+='<h2>暮らしの場面からすべての案内を探す</h2><div class="browse-grid">'+''.join(card(t['href'],t['category'],t.get('title',''),t.get('icon','📖')) for t in LEDGER if t['href'].count('/')==3)+'</div>'
  else:body+='<h2>場所を決めてから調べたいとき</h2>'+linklist([{'href':'/discover/outing-plans/','label':'目的別に、出かける場所を組み合わせる'},{'href':'/places/','label':'施設・公園・観光スポットを名称と分野で探す'},{'href':'/life/start-living/public-transit/','label':'オンモビ・路線バスの使い方を確認する'}])
  if path=='/discover/':body+=album_note()
  write(path,page(path,title,lead,body,category))
 routes=[]
 for r in read('outing-routes.json',[]):
  links=[{'href':'/places/?q='+quote(n),'label':n+'の施設案内を探す'} for n in r['stops']]
  body=f'<section class="guide-section"><h2>{esc(r["title"])}</h2><p>{esc(r["intro"])}</p>'+linklist(links)+'<ul>'+''.join(f'<li>{esc(n)}</li>' for n in r['notes'])+'</ul>'+linklist([{'href':'/discover/'+s+'/','label':next(g['title'] for g in GUIDES if g['slug']==s)} for s in r['guides']])+'</section>'
  routes.append(body)
 write('/discover/outing-plans/',page('/discover/outing-plans/','御前崎のお出かけを、目的から組み立てる','初めての訪問、子ども連れ、雨の日、食と買物。行き先の組み合わせ例から、自分たちに合う予定を選べます。',''.join(routes),'御前崎を知る','🗺️'))
 body='<div class="browse-grid">'+''.join(card('/checklists/'+c['slug']+'/',c['title'],c['lead'],c.get('icon','✅')) for c in CHECKLISTS)+'</div>'
 write('/checklists/',page('/checklists/','状況別チェックリスト','引っ越し、出産、退職、親の介護。必要な行動を順番に確認し、済んだ項目を記録できます。',body,'状況別チェックリスト','✅'))
 contents={}
 for p in (ROOT/'data/content').glob('*.json'):
  if not p.name.startswith('_'):
   for row in json.loads(p.read_text(encoding='utf-8')):contents[row['href']]=row
 questions=[];seen=set()
 for href,row in contents.items():
  t=TOPIC.get(href)
  if not t or t.get('status') not in ['published','human-verified','machine-verified','ai-checked']:continue
  for q in row.get('qa',[]):
   key=(re.sub(r'\s+','',q['question']),re.sub(r'\s+','',q['answer']))
   if key in seen:continue
   seen.add(key);questions.append({'question':q['question'],'answer':q['answer'],'topic':t.get('search_title',t['title']),'href':href,'category':t['category'],'dateLabel':('更新：'+t['content_updated_date']+'（確認範囲は元ページに記載）' if t.get('content_updated_date') else '確認日と対象条件は元の案内をご確認ください。')})
 for g in GUIDES:
  for q in g.get('questions',g.get('qa',[])):questions.append({'question':q['question'],'answer':'<p>'+esc(q['answer'])+'</p>','topic':g['title'],'href':g['href'],'category':g['category'],'dateLabel':'確認：'+DATE})
 (ROOT/'data/questions-index.json').write_text(json.dumps(questions,ensure_ascii=False),encoding='utf-8')
 browser('questions','御前崎の暮らしを、質問から探す','制度名が分からなくても、疑問の言葉から回答へ。詳しい条件・手続き・公式窓口は各案内につながっています。',questions,'questions-index.json')
 places=read('places.json',[]);browser('places','御前崎の施設・公園・観光スポット','名称、地区、目的で場所を探せます。休館・利用制限のある施設も区別し、営業や予約の確認先へ案内します。',places,'places.json')
 today = datetime.now(timezone(timedelta(hours=9))).date().isoformat()
 current_updates = [u for u in UPDATES if current_update(u, today)]
 archived_updates = [u for u in UPDATES if not current_update(u, today)]
 update_body = (
  '<h2>受付中・開催予定・利用案内</h2>'
  '<div class="update-list" id="current-updates">' + ''.join(map(update_html, current_updates)) + '</div>'
  '<details id="past-updates" class="guide-section"><summary>終了した案内・過去の記録</summary>'
  '<div class="update-list" id="past-update-list">' + ''.join(map(update_html, reversed(archived_updates))) + '</div></details>'
  '<p class="mini">各項目に確認日を表示しています。受付・日程の変更は<a href="https://www.city.omaezaki.shizuoka.jp/news.html">市公式の新着情報</a>と各施設の案内をご確認ください。</p>'
  + EXPIRY_SCRIPT
 )
 write('/updates/',page('/updates/','暮らし・お出かけの最新確認情報','申込期限、制度の変更、施設の休館などを、確認日とともに整理しています。開催日と申込締切は別々に確認してください。',update_body,'更新情報','🗓️'))
 tools='<div class="browse-grid">'+card('/questions/','質問検索','困りごとの言葉で回答を探す。','💬')+card('/places/','施設検索','名前、地区、目的から場所と確認先を探す。','📍')+card('/checklists/','手続きチェックリスト','進捗の保存と印刷。個人情報の入力は不要。','✅')+'</div>'
 write('/tools/',page('/tools/','暮らしを調べる便利ツール','検索とチェックリストで、必要な情報と次にすることを整理できます。',tools,'便利ツール','🧰'))
 about='<section class="guide-section"><h2>運営者</h2><p>御前崎ライフハックは、富士ヶ丘サービス株式会社（代表 大石浩之）が運営する非公式の情報案内サイトです。御前崎市の行政窓口ではありません。</p><p>運営会社の介護・住まいの相談案内は、制度の申請窓口と区別して表示しています。</p><h2>編集・更新の方針</h2><ul><li>市・県・国・施設運営者などの一次資料を優先し、出典と確認日を記載します。</li><li>制度の対象・料金・期限を、利用者が次の行動を選べる言葉に整理します。</li><li>古い公式ページと新しい案内が異なる場合は、相違点と確認先を示します。</li><li>確認日は、そのページで明示する確認範囲のものです。空き状況や個別の利用可否を保証するものではありません。</li><li>体験談や現地訪問を、実施記録なしに創作しません。写真の撮影・公開時期と現在の状況を区別します。</li></ul><h2>写真の出典</h2><p>地域写真は、御前崎市が静岡県オープンデータで公開した資料を、表示条件に従って縮小・形式変換して使用しています。</p>'+''.join(photo(x['slug']) for x in read('image-credits.json',[]))+'<h2>利用条件・訂正の連絡</h2>'+linklist([{'href':'/terms/','label':'利用条件・免責・お問い合わせの案内'},{'href':'https://www.fujigaoka-service.co.jp/','label':'運営会社：富士ヶ丘サービス'}])+'</section>'
 write('/about/',page('/about/','運営者・編集方針・写真の出典','公式情報と民間サービスを区別し、確認できた範囲と出典を明示して案内します。',about,'運営者・編集方針','📝'))
 # Keep the existing category accordion and business/photograph-gallery block intact.
 old=(ROOT/'index.html').read_text(encoding='utf-8')
 categories=re.search(r'<section id="category-links">.*?</section>',old,re.S)
 if not categories:raise ValueError('Existing category navigation not found')
 community=marker('community-links')
 hero=f'<section class="enrich-hero"><div class="hero-copy"><p class="kicker">海のまち、御前崎の暮らしとお出かけ</p><h1>御前崎を知る。<br><span>暮らしの疑問に、</span><span>答えを。</span></h1><p>市役所の手続きから、親の介護、子どもの預け先、週末のお出かけまで。知りたいことを、次の行動につながる案内にまとめました。</p><div class="hero-actions"><a href="/guide/">暮らしのガイドを探す</a><a class="secondary" href="/discover/">御前崎を知る</a></div></div><figure><img src="/assets/omaezaki/lighthouse.webp" alt="夕暮れに明かりがともる御前埼灯台" width="800" height="1200" fetchpriority="high"><figcaption>写真：御前崎市／CC BY 4.0・<a href="/about/">出典と加工内容</a></figcaption></figure></section>'
 urgent='<section class="urgent-strip"><h2>急いでいるとき</h2><div class="urgent-links"><a href="tel:119">緊急時は119番</a><a href="/life/emergency/emergency-medical/">救急相談・夜間診療</a><a href="/life/emergency/evacuation-hazard-map/">避難所・ハザード</a><a href="/life/emergency/road-river-info/">道路・河川情報</a></div><p>命に関わるときは119番。避難の必要があるときは、情報を探すより安全確保を優先してください。</p></section>'
 shortcuts=[
  ('/life/start-living/garbage-sorting-calendar/','地区別ごみカレンダー'),
  ('/life/start-living/bulky-garbage-dropoff/','粗大ごみの持ち込み'),
  ('/life/start-living/public-transit/','オンモビの予約・運賃'),
  ('/life/play-out/visit-library/','図書館アスパルの開館日'),
  ('/life/family-grow/child-allowance/','児童手当の申請'),
  ('/life/education/after-school-club/','学童の申込み'),
  ('/life/start-living/moving-address-change/','引っ越しの住所変更'),
  ('/life/start-living/water-start-stop-fees/','水道の開始・中止'),
 ]
 quick_links='<nav class="hero-actions" aria-label="暮らしの手続き・施設へ直接進む">'+''.join(f'<a href="{esc(href)}">{esc(label)}</a>' for href,label in shortcuts)+'</nav>'
 search='<section class="site-search" aria-labelledby="search-title"><label id="search-title" for="site-search-input">調べたいことは何ですか？</label><form class="search-row" role="search" action="/" method="get" onsubmit="return iwataSiteSearch(event)"><input type="search" id="site-search-input" name="q" placeholder="例：オンモビ、子どもを預けたい、補聴器、灯台"><button type="submit">探す</button></form><div id="search-results" class="search-results" aria-live="polite"></div>'+quick_links+'</section>'
 feature='<div class="section-heading"><h2>目的から探す</h2></div><div class="browse-grid">'+card('/discover/','遊び・食・景色を楽しむ','灯台、海辺、公園、食と買物。行く前に知りたいことを整理。',image='dunes')+card('/guide/care-consultation-route/','親・実家のことを考える','離れて暮らす家族の相談、介護の申請、住まいを確認。','🏡')+card('/life/living-soon/want-to-live/','御前崎で暮らす','移住の支援、交通、子育て。家族の生活に合わせて確かめる。',image='tea-fields')+'</div>'
 home_updates = [u for u in current_updates if u.get('home')]
 update_cards = ''.join(
  card(u['href'],u['title'],u['summary'],'🗓️',u.get('status','')).replace(
   '<a class="browse-card"', '<a class="browse-card"' + expiry_attribute(u), 1
  )
  for u in home_updates
 )
 latest = (
  '<div class="section-heading"><h2 id="current-info-title">いま確認したい情報</h2><a href="/updates/">確認した情報をすべて見る</a></div>'
  '<div class="browse-grid two" id="home-updates">' + update_cards + '</div>' + EXPIRY_SCRIPT
 )
 guidecards='<div class="section-heading"><h2>詳しく知ってから動きたい</h2><a href="/guide/">暮らしガイド一覧</a></div><div class="browse-grid">'+''.join(card(g['href'],g['title'],g['lead'],g.get('icon','📖')) for g in GUIDES if g.get('home'))+'</div>'
 utilities='<div class="section-heading"><h2>答えと次の行動を探す</h2></div>'+tools
 closing='<section class="sources-panel"><h2>情報の見方</h2><p>各案内に出典と確認範囲を記載しています。新しい条件や空き状況は、掲載した公式窓口でご確認ください。</p><p><a href="/about/">運営者・編集方針・写真の出典</a> ／ <a href="https://www.city.omaezaki.shizuoka.jp/">御前崎市公式サイト</a></p></section>'
 homebody=hero+urgent+search+feature+album_note()+latest+guidecards+utilities+categories.group(0)+closing+community
 write('/',page('/','御前崎の暮らし・手続き・お出かけガイド','御前崎の手続き、子育て、介護、防災から海辺・食・観光まで。公式情報を整理し、検索とチェックリストで次の行動を案内します。',homebody,home=True))
 (ROOT/'data/enrichment-pages.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'extra_pages':len(manifest),'guides':len(GUIDES),'questions':len(questions),'places':len(places),'checklists':len(CHECKLISTS)},ensure_ascii=False))
if __name__=='__main__':main()

