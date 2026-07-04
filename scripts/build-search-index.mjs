// data/topics_master.json（title/synonyms/category の手動管理データ）から
// 本文冒頭リードを実ページHTMLから抽出し、検索用の search-index.json を生成する。
// 本文全文は含めない（意図的）。実行: node scripts/build-search-index.mjs
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..');
const LEAD_MAX_CHARS = 300;

function stripTags(html) {
  return html
    .replace(/<[^>]+>/g, '')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/\s+/g, ' ')
    .trim();
}

function pageFilePath(href) {
  if (href === '/') return path.join(ROOT, 'index.html');
  return path.join(ROOT, href.replace(/^\//, '').replace(/\/$/, ''), 'index.html');
}

function extractLead(href) {
  const filePath = pageFilePath(href);
  if (!fs.existsSync(filePath)) {
    return null; // life/未公開（draft・_staging行き）のため検索対象外
  }
  const html = fs.readFileSync(filePath, 'utf8');
  const m = html.match(/<p class="lead">([\s\S]*?)<\/p>/);
  if (!m) {
    console.warn(`[warn] leadが見つかりません（空扱い）: ${href}`);
    return '';
  }
  return stripTags(m[1]).slice(0, LEAD_MAX_CHARS);
}

function main() {
  const topicsMaster = JSON.parse(fs.readFileSync(path.join(ROOT, 'data/topics_master.json'), 'utf8'));
  const searchIndex = topicsMaster
    .map((topic) => {
      const lead = extractLead(topic.href);
      if (lead === null) return null; // 未公開ページは検索インデックスから除外
      return {
        href: topic.href,
        icon: topic.icon,
        title: topic.title,
        category: topic.category,
        synonyms: topic.synonyms || [],
        lead,
      };
    })
    .filter(Boolean);

  const outPath = path.join(ROOT, 'search-index.json');
  const json = JSON.stringify(searchIndex);
  fs.writeFileSync(outPath, json);

  const totalWords = searchIndex.reduce((sum, t) => {
    const text = `${t.title} ${t.category} ${t.synonyms.join(' ')} ${t.lead}`;
    return sum + text.split(/\s+|(?=[　-鿿])/).filter(Boolean).length;
  }, 0);

  console.log(`生成完了: ${outPath}`);
  console.log(`項目数: ${searchIndex.length}`);
  console.log(`ファイルサイズ: ${(json.length / 1024).toFixed(1)} KB`);
  console.log(`概算語数（参考値）: ${totalWords}`);
}

main();
