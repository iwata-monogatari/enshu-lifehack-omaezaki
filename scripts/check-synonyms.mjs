// synonyms未登録（または登録数が少ない）項目を検出する検査スクリプト。
// 遠州9市町への横展開時も、各市固有の topics_master.json に対してそのまま使える。
// 実行: node scripts/check-synonyms.mjs
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..');
const MIN_SYNONYMS = 1;

function isCategoryIndex(href) {
  return /^\/life\/[^/]+\/$/.test(href);
}

function main() {
  const topicsMaster = JSON.parse(fs.readFileSync(path.join(ROOT, 'data/topics_master.json'), 'utf8'));
  const leafItems = topicsMaster.filter((t) => !isCategoryIndex(t.href));
  const missing = leafItems.filter((t) => (t.synonyms || []).length < MIN_SYNONYMS);

  console.log(`中項目数（カテゴリindexを除く）: ${leafItems.length}`);
  console.log(`synonyms未登録: ${missing.length}件`);
  if (missing.length) {
    for (const t of missing) console.log(`  - ${t.href}\t${t.title}`);
  }
  process.exitCode = missing.length > 0 ? 1 : 0;
}

main();
