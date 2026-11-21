# enshu-lifehack-omaezaki

御前崎ライフハック（遠州ライフハック 御前崎市版）の **静的サイト** リポジトリ。
公開先：`https://omaezaki.enshu-lifehack.com/`（Cloudflare Workers Static Assets）

菊川版から手動クローン・履歴を切って新設。横展開の設計原則は袋井版の指示書（`enshu-lifehack-fukuroi` リポジトリ `docs/fukuroi-lifehack-design-spec.md`）に準拠する。

## 構成

静的HTMLのみ。Cloudflare の **Build output directory = `/`**（ビルド不要）で配信する。

```
index.html              トップ（くらしの場面・目的から選ぶ）
data/city.json          市プロファイル（市名・公式窓口・CVフラグ等の差分を集約）
data/topics_master.json 中項目マスター台帳（磐田155項目が起点）
data/content/<category>.json 中項目ごとの執筆済みコンテンツ（qa/steps/tabs等）
life/<大項目>/           くらしの大項目ページ
life/<大項目>/<中項目>/   個別ページ
sitemap.xml             サイトマップ
robots.txt
_redirects              旧 /iwata/ 配下 → 直下への 301
404.html                カスタム404
favicon.svg
```

## 生成方法

本サイトは公式サイトのクロール・静的化ではなく、`data/topics_master.json` の中項目台帳をもとに、公式情報を1件ずつ調査した上でAIが執筆する「台帳駆動」の生成物である（掛川版・森町版と同じ方式）。

## 免責

本サイトは御前崎市公式サイトではありません。最新・正確な情報は御前崎市公式サイトをご確認ください。
運営：富士ヶ丘サービス ／ 代表：大石浩之

## 暮らし・地域ガイドと検索（2026-11-21）

`data/enrichment-guides.json` は一次資料から整理した詳細ガイド、`data/places.json` は施設・店舗・公園と確認先、`data/checklists.json` は状況別の確認手順、`data/outing-routes.json` はお出かけの組み合わせ例、`data/updates.json` は日付付きの更新案内です。写真の利用条件は `data/image-credits.json` に記録しています。

全体の再生成と検査：

```sh
python scripts/build_all.py
node scripts/test-search.mjs
node scripts/check-synonyms.mjs
python scripts/inspect_all.py
```

`build_all.py` は既存ページの本文更新範囲、共通部品、詳細ガイド、質問検索用データ、サイト内検索、サイトマップを同期します。既存の相談案内と13カテゴリを保持します。単独で `build-index-accordion.mjs` を実行して新しいトップを置き換えないでください。

既存記事の公式窓口情報は `data/fact-labels.json` で日本語表示します。質問検索は既存記事と追加ガイドの回答を参照し、新規記事数を表すものではありません。チェック状態はブラウザ内だけに保存し、行政への申請は行いません。画像・施設掲載は現地訪問や営業の電話確認を意味しません。

情報確認日は2026-11-21です。旧記事は元の確認日を維持し、修正した範囲を別に表示します。イベント・期間限定の案内は年月日を保持し、後日の更新時は期限を再確認してください。未発表の催事や予約の空き状況を推測で補いません。


## トップの写真館・富士ヶ丘サービス相談案内（2026-11-19）

`parts/community-links.html` がトップページの案内の原本です。`index.html` の `PART:community-links` マーカーへ同期してください。写真館は実在する市町だけに掲載し、他市町の館をその市町の写真館として表示しません。実家カルテと介護相談は市町別UTM・クリック計測付きです。行政案内・既存のガイド・各自治体公式へのリンクを保持してください。相談写真は運営会社の既存サイトに掲載された写真です。
