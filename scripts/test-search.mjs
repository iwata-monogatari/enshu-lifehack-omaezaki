// search-index.json + data/test-cases.json を使い、スコアリングが受け入れ基準を満たすか検証する。
// 「上位N件以内に期待ページが含まれるか」「防災項目などの無関係ページが1位にならないか」を確認する。
// 実行: node scripts/test-search.mjs
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { searchTopics } from '../assets/search-core.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..');
const TOP_N = 3;

function main() {
  const items = JSON.parse(fs.readFileSync(path.join(ROOT, 'search-index.json'), 'utf8'));
  const cases = JSON.parse(fs.readFileSync(path.join(ROOT, 'data/test-cases.json'), 'utf8'));

  let failCount = 0;
  for (const testCase of cases) {
    const results = searchTopics(items, testCase.query, { limit: TOP_N });
    const hrefs = results.map((r) => r.href);
    const ok = hrefs.some((h) => testCase.expectedHrefIncludesAny.includes(h));
    const status = ok ? 'PASS' : 'FAIL';
    if (!ok) failCount++;
    console.log(`[${status}] "${testCase.query}" -> top${TOP_N}: ${hrefs.join(', ') || '(該当なし)'}`);
    if (!ok) {
      console.log(`         期待: ${testCase.expectedHrefIncludesAny.join(' / ')}`);
    }
  }

  console.log('---');
  console.log(`${cases.length}件中 ${cases.length - failCount}件PASS / ${failCount}件FAIL`);
  process.exitCode = failCount > 0 ? 1 : 0;
}

main();
