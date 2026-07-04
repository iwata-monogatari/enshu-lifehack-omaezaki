// data/categories.json から index.html の「暮らしの場面・目的から選ぶ」アコーディオンを機械生成する。
// 中項目の追加・削除・名称変更は data/categories.json を更新し、本スクリプトを再実行して反映する。
// 実行: node scripts/build-index-accordion.mjs
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..');
const ORIGIN = 'https://omaezaki.enshu-lifehack.com';

function toRelative(url) {
  return url.startsWith(ORIGIN) ? url.slice(ORIGIN.length) : url;
}

function buildCategoryHtml(cat) {
  const items = cat.items
    .map((item) => `<li><a href="${toRelative(item.url)}">${item.label}</a></li>`)
    .join('');
  const more = `<li class="subitems-more"><a href="${toRelative(cat.url)}">この分野についてもっと詳しく見る</a></li>`;
  return (
    `<details class="category" data-id="${cat.id}">` +
    `<summary><span class="topic-icon" aria-hidden="true">${cat.emoji}</span>` +
    `<span class="card-text"><span class="card-title">${cat.title}</span>` +
    `<span class="card-desc">${cat.description}</span></span>` +
    `<span class="acc-arrow" aria-hidden="true"></span></summary>` +
    `<ul class="subitems">${items}${more}</ul>` +
    `</details>`
  );
}

function main() {
  const data = JSON.parse(fs.readFileSync(path.join(ROOT, 'data/categories.json'), 'utf8'));
  const accordionHtml = data.categories.map(buildCategoryHtml).join('');
  const wrapped = `<div class="category-accordion">${accordionHtml}</div>`;

  const indexPath = path.join(ROOT, 'index.html');
  const html = fs.readFileSync(indexPath, 'utf8');
  const re = /(<section id="category-links"><h2>[^<]*<\/h2><p class="lead">[^<]*<\/p>)<div class="cat-grid">[\s\S]*?<\/div>(<\/section>)/;
  if (!re.test(html)) {
    throw new Error('category-links セクションのcat-gridが見つかりません');
  }
  const newHtml = html.replace(re, `$1${wrapped}$2`);
  fs.writeFileSync(indexPath, newHtml);

  const itemCount = data.categories.reduce((sum, c) => sum + c.items.length, 0);
  console.log(`生成完了: ${data.categories.length}カテゴリ / 中項目${itemCount}件`);
}

main();
