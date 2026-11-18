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


## トップの写真館・富士ヶ丘サービス相談案内（2026-11-19）

`parts/community-links.html` がトップページの案内の原本です。`index.html` の `PART:community-links` マーカーへ同期してください。写真館は実在する市町だけに掲載し、他市町の館をその市町の写真館として表示しません。実家カルテと介護相談は市町別UTM・クリック計測付きです。行政案内・既存のガイド・各自治体公式へのリンクを保持してください。相談写真は運営会社の既存サイトに掲載された写真です。
