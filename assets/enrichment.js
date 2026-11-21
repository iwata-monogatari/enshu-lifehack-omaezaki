const normalize = value => (value || '').normalize('NFKC').toLowerCase().replace(/[\s\u3000]+/g,' ').trim();
const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

async function initializeSearch(root) {
  const input=root.querySelector('input[type="search"]'), category=root.querySelector('select'), list=root.querySelector('[data-results]'), count=root.querySelector('[data-count]'), more=root.querySelector('[data-more]');
  let data,limit=20;
  try { const response=await fetch(root.dataset.source); if(!response.ok)throw Error(response.status);data=await response.json(); }
  catch {count.textContent='検索データを読み込めませんでした。下の分野別リンクからお探しください。';more.hidden=true;return;}
  const kind=root.dataset.browser;
  const questionTemplate = item => `<details><summary>${escapeHtml(item.question)}</summary><div class="result-context">${escapeHtml(item.category)} ／ ${escapeHtml(item.topic)}</div><div class="answer">${item.answer}</div><p class="mini">${escapeHtml(item.dateLabel || '')}</p><a href="${escapeHtml(item.href)}">手続きの流れ・公式の確認先を見る</a></details>`;
  const placeTemplate = item => `<article class="place-card"><span class="pill">${escapeHtml(item.category)}</span><h2>${escapeHtml(item.name)}</h2><p class="place-meta">${escapeHtml(item.area || '')}</p><p>${escapeHtml(item.summary)}</p>${item.notice?`<p class="place-notice">${escapeHtml(item.notice)}</p>`:''}<dl>${[['所在地',item.address],['連絡先',item.tel],['利用案内',item.hours],['料金等',item.fee]].filter(x=>x[1]).map(([k,v])=>`<dt>${k}</dt><dd>${escapeHtml(v)}</dd>`).join('')}</dl>${(item.sources || []).map(s=>`<a href="${escapeHtml(s.url)}" target="_blank" rel="noopener">${escapeHtml(s.label || '公式の施設案内')}（別タブ）</a>`).join('<br>')}<p class="mini">${escapeHtml(item.verificationLabel || "")} 確認：${escapeHtml(item.checked || '2026-11-21')}。休業・開催状況は出発前に公式案内でご確認ください。</p></article>`;
  function render(reset=true) {
    if(reset)limit=20;
    const words=normalize(input.value).split(' ').filter(Boolean),selected=category.value;
    const results=data.filter(item=>(!selected||item.category===selected)&&words.every(w=>normalize([item.question,item.topic,item.answer,item.name,item.summary,item.area,item.address,item.category,item.notice,item.hours,...(item.keywords||[])].join(' ')).includes(w)));
    count.textContent=`${results.length}件${selected?' ／ '+selected:''}${words.length?' ／ 「'+input.value.trim()+'」':''}`;
    list.innerHTML=results.length?results.slice(0,limit).map(kind==='places'?placeTemplate:questionTemplate).join(''):'<p class="no-results">一致する項目がありません。別の言葉で検索するか、分類を「すべて」に戻してください。</p>';
    more.hidden=results.length<=limit;more.textContent=`続きを表示（残り${Math.max(0,results.length-limit)}件）`;
  }
  input.addEventListener('input',()=>render());category.addEventListener('change',()=>render());root.querySelector('[data-clear]')?.addEventListener('click',()=>{input.value='';category.value='';render();input.focus();});more.addEventListener('click',()=>{limit+=20;render(false);});
  const params=new URLSearchParams(location.search);input.value=params.get('q')||'';if([...category.options].some(o=>o.value===params.get('category')))category.value=params.get('category');render();
}

function initializeChecklist(root) {
  const boxes=[...root.querySelectorAll('input[type="checkbox"]')],key=`omaezaki-checklist-v1:${root.dataset.checklist}`,label=root.querySelector('[data-progress-label]'),bar=root.querySelector('progress'),notice=root.querySelector('[data-storage-note]');
  let stored={};try {stored=JSON.parse(localStorage.getItem(key)||'{}');}catch {notice.textContent='この環境では進捗を保存できません。画面上でチェックすることはできます。';}
  boxes.forEach(box=>{box.checked=stored[box.value]===true;});
  function update(save=true){const completed=boxes.filter(b=>b.checked).length;label.textContent=`${boxes.length}項目中 ${completed}項目を確認済み`;bar.max=boxes.length;bar.value=completed;if(save)try{localStorage.setItem(key,JSON.stringify(Object.fromEntries(boxes.map(b=>[b.value,b.checked]))));}catch{notice.textContent='進捗はこの画面だけに反映されます。ブラウザを閉じると失われる場合があります。';}}
  boxes.forEach(b=>b.addEventListener('change',()=>update()));root.querySelector('[data-reset]')?.addEventListener('click',()=>{boxes.forEach(b=>b.checked=false);update();});root.querySelector('[data-print]')?.addEventListener('click',()=>window.print());update(false);
}
document.querySelectorAll('[data-browser]').forEach(initializeSearch);
document.querySelectorAll('[data-checklist]').forEach(initializeChecklist);
