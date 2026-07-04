// 磐田ライフハック 検索スコアリング（構造化キーワード方式）
// title/synonyms/category/lead のみを対象にし、本文全文は評価しない。
// ブラウザ（search-app.js）と Node（scripts/test-search.mjs）の双方から同一ロジックを import する。

const WEIGHTS = { title: 3.0, synonyms: 2.5, category: 1.5, lead: 0.5 };
const SHORT_QUERY_MAX = 4;

export function normalizeQuery(text) {
  return (text || '')
    .toLowerCase()
    .replace(/\s+/g, '')
    .replace(/[・、，,／/]/g, '');
}

function fieldMatchScore(fieldText, compactQuery, weight, allowNgram) {
  const norm = normalizeQuery(fieldText);
  if (!norm || !compactQuery) return 0;
  if (norm === compactQuery) return weight * 4;
  if (norm.includes(compactQuery)) return weight * 2;
  if (!allowNgram) return 0;

  // 部分一致（N-gram）は誤爆を避けるため大幅に減衰させたフォールバック
  const maxSize = Math.min(4, compactQuery.length);
  let best = 0;
  for (let size = maxSize; size >= 2; size--) {
    for (let i = 0; i <= compactQuery.length - size; i++) {
      const part = compactQuery.slice(i, i + size);
      if (norm.includes(part)) {
        best = Math.max(best, size);
      }
    }
    if (best) break;
  }
  return best ? weight * 0.3 * best : 0;
}

/**
 * @param {{title:string, category:string, synonyms:string[], lead:string}} item
 * @param {string} rawQuery
 */
export function scoreItem(item, rawQuery) {
  const compact = normalizeQuery(rawQuery);
  if (!compact) return 0;
  const isShort = compact.length <= SHORT_QUERY_MAX;

  let synonymScore = 0;
  for (const syn of item.synonyms || []) {
    synonymScore = Math.max(synonymScore, fieldMatchScore(syn, compact, WEIGHTS.synonyms, true));
  }
  const titleScore = fieldMatchScore(item.title, compact, WEIGHTS.title, true);
  const categoryScore = fieldMatchScore(item.category, compact, WEIGHTS.category, isShort ? false : true);
  // 短語入力時は synonyms/title の完全一致・前方一致を最優先し、lead 由来の弱いN-gram一致は使わない
  const leadScore = fieldMatchScore(item.lead, compact, WEIGHTS.lead, !isShort);

  return synonymScore + titleScore + categoryScore + leadScore;
}

/**
 * @param {Array} items search-index.json の配列
 * @param {string} rawQuery
 * @param {{limit?: number, threshold?: number}} opts
 */
export function searchTopics(items, rawQuery, opts = {}) {
  const limit = opts.limit ?? 8;
  const threshold = opts.threshold ?? 1.0;
  return items
    .map((item) => ({ item, score: scoreItem(item, rawQuery) }))
    .filter((r) => r.score >= threshold)
    .sort((a, b) => b.score - a.score)
    .slice(0, limit)
    .map((r) => ({ ...r.item, score: r.score }));
}
