import { searchTopics } from '/assets/search-core.mjs';

let indexPromise = null;
function loadIndex() {
  if (!indexPromise) {
    indexPromise = fetch('/search-index.json').then((res) => res.json());
  }
  return indexPromise;
}

function escapeHtml(text) {
  return text.replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
}

async function runSearch(query) {
  const resultsEl = document.getElementById('search-results');
  if (!resultsEl) return;
  const value = (query || '').trim();
  if (!value) {
    resultsEl.innerHTML = '';
    return;
  }
  const items = await loadIndex();
  const matched = searchTopics(items, value);
  const safeQuery = escapeHtml(value);
  resultsEl.innerHTML = matched.length
    ? `<h2>「${safeQuery}」の候補</h2><ul>${matched
        .map(
          (page) =>
            `<li><a class="search-hit" href="${page.href}"><span class="result-ic" aria-hidden="true">${page.icon}</span><span><strong>${page.title}</strong><span>${page.category}</span></span><span aria-hidden="true">›</span></a></li>`
        )
        .join('')}</ul>`
    : `<h2>「${safeQuery}」の候補</h2><p class="mini">サイト内に一致する項目が見つかりませんでした。言葉を短くして検索してください。</p>`;
}

window.iwataSiteSearch = function iwataSiteSearch(event) {
  event.preventDefault();
  const input = document.getElementById('site-search-input');
  runSearch(input ? input.value : '');
  return false;
};

document.addEventListener('DOMContentLoaded', () => {
  const input = document.getElementById('site-search-input');
  const initial = new URLSearchParams(window.location.search).get('q') || '';
  loadIndex();
  if (input && initial) {
    input.value = initial;
    runSearch(initial);
  }
  input?.addEventListener('input', () => runSearch(input.value));
});
