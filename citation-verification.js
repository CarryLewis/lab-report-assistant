// Citation review prototype. Results are deliberately split into metadata,
// formatting and claim-support checks so a lookup is never presented as proof.
const citationChecks = [
  {
    id: 'madigan2018', level: 'ok', label: '可定位 · 内容待复核',
    title: 'Madigan et al. (2018) — 教材条目',
    claim: '用于支持细菌生长的四阶段模式。',
    detail: '正文引文与参考文献一一对应；作者、年份、书名、版本和出版社字段完整。教材没有 DOI，不应因此判为错误。当前原型未取得可核对的章节原文。',
    tags: [['正文↔条目匹配','ok'],['APA 字段完整','ok'],['内容需人工核对','warn']],
    query: 'Brock Biology of Microorganisms 15th Madigan 2018'
  },
  {
    id: 'monod1949', level: 'warn', label: '身份匹配 · 支持范围待复核',
    title: 'Monod (1949) — 期刊文章',
    claim: '用于支持后期增速降低可能来自营养限制或代谢产物积累。',
    detail: 'DOI 与题名可用于高置信度身份解析，但“文献存在”不等于“这句话被文献支持”。需打开摘要或全文，检查该来源是否同时支持两个机制。',
    tags: [['正文↔条目匹配','ok'],['DOI 可解析','ok'],['主张范围可能过宽','warn']],
    query: 'The growth of bacterial cultures Monod 1949'
  },
  {
    id: 'missing2020', level: 'error', label: '缺少参考文献条目',
    title: 'Lee (2020) — 正文孤立引文',
    claim: '用于支持“无重复实验时无法估计随机测量变异”。',
    detail: '正文中出现作者—年份引文，但 References 没有对应条目。无法唯一识别来源，也无法核对格式或被引内容。应先让学生补充完整条目。',
    tags: [['正文存在','ok'],['参考条目缺失','warn'],['不可进行内容核验','warn']],
    query: 'replicate measurements random variation experimental design Lee 2020'
  }
];

const citationsPane = document.getElementById('citationsPane');
citationsPane.innerHTML = `
  <div class="sectionlabel">引用核验概览 · 示例分析</div>
  <div class="citation-summary">
    <div class="citation-metric"><b>3</b><span>正文引文</span></div>
    <div class="citation-metric"><b>2</b><span>参考条目</span></div>
    <div class="citation-metric"><b>2</b><span>需人工复核</span></div>
  </div>
  <div class="citation-note">核验顺序：先检查正文与参考文献的对应关系，再核对书目信息和指定格式，最后用摘要或全文判断引用内容是否真的支持学生的主张。外部检索命中本身不能证明引用恰当。</div>
  <div id="citationCards"></div>
  <div class="sectionlabel">外部文献检索 · Crossref</div>
  <div class="citation-search"><input id="citationQuery" maxlength="300" aria-label="文献检索词" placeholder="输入题名、作者、DOI 或关键词"><button id="citationSearchButton">检索</button></div>
  <div id="citationSearchStatus" class="screen-reader-status">仅发送当前检索词，不发送学生报告全文。</div>
  <div id="citationResults"></div>`;

const citationCards = document.getElementById('citationCards');
function renderCitationCards() {
  citationCards.innerHTML = citationChecks.map(item => `
    <article class="citation-card ${item.level}" id="citation-${item.id}" data-citation="${item.id}">
      <h3>${item.title}</h3>
      <div class="citation-tags">${item.tags.map(([text, kind]) => `<span class="citation-tag ${kind}">${text}</span>`).join('')}</div>
      <p><b>学生主张：</b>${item.claim}</p><p>${item.detail}</p>
      <div class="citation-actions"><button data-action="locate">定位原文</button><button data-action="search">带入检索</button><button data-action="review">标记已复核</button></div>
      <div class="review-status">审核状态：${item.label}</div>
    </article>`).join('');
}
renderCitationCards();

function openCitation(id) {
  document.querySelector('[data-tab="citations"]').click();
  document.querySelectorAll('.citation-mark,.references li').forEach(node => node.classList.remove('citation-active','reference-active'));
  const mark = document.querySelector(`.citation-mark[data-citation="${id}"]`);
  const reference = document.getElementById(`ref-${id}`);
  if (mark) {
    mark.classList.add('citation-active');
    mark.scrollIntoView({behavior:'smooth', block:'center'});
  }
  if (reference) reference.classList.add('reference-active');
  const card = document.getElementById(`citation-${id}`);
  if (card) card.scrollIntoView({behavior:'smooth', block:'nearest'});
}
document.querySelectorAll('.citation-mark').forEach(mark => {
  mark.setAttribute('role','button'); mark.tabIndex = 0;
  mark.onclick = () => openCitation(mark.dataset.citation);
  mark.onkeydown = event => { if (event.key === 'Enter' || event.key === ' ') openCitation(mark.dataset.citation); };
});

citationCards.addEventListener('click', event => {
  const button = event.target.closest('button');
  if (!button) return;
  const card = button.closest('.citation-card');
  const item = citationChecks.find(check => check.id === card.dataset.citation);
  if (button.dataset.action === 'locate') openCitation(item.id);
  if (button.dataset.action === 'search') {
    document.getElementById('citationQuery').value = item.query;
    document.getElementById('citationQuery').focus();
  }
  if (button.dataset.action === 'review') {
    card.querySelector('.review-status').textContent = '审核状态：教师已复核';
    button.disabled = true;
    showToast('已记录教师复核状态');
  }
});

function escapeText(value) {
  return String(value || '').replace(/[&<>"']/g, character => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[character]));
}
function safeExternalUrl(value) {
  try {
    const url = new URL(value);
    return ['https:', 'http:'].includes(url.protocol) ? url.href : null;
  } catch (_) { return null; }
}
async function searchCitations() {
  const query = document.getElementById('citationQuery').value.trim();
  const status = document.getElementById('citationSearchStatus');
  const results = document.getElementById('citationResults');
  if (!query) { status.textContent = '请输入题名、作者、DOI 或关键词。'; return; }
  status.textContent = '正在查询 Crossref 元数据…'; results.innerHTML = '';
  try {
    const response = await fetch(`/api/scholarly/search?q=${encodeURIComponent(query)}&limit=5`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || '检索失败');
    status.textContent = `找到 ${data.results.length} 条候选。元数据匹配不代表内容支持。`;
    results.innerHTML = data.results.map(work => {
      const meta = [work.authors.slice(0,3).join(', '), work.year, work.container_title, work.doi ? `DOI: ${work.doi}` : null].filter(Boolean).join(' · ');
      const abstract = work.abstract ? work.abstract.slice(0,260) + (work.abstract.length > 260 ? '…' : '') : '未取得摘要；不能据此判断是否支持学生主张。';
      const sourceUrl = safeExternalUrl(work.url);
      return `<article class="search-result"><b>${escapeText(work.title)}</b><small>${escapeText(meta)}</small><p>${escapeText(abstract)}</p>${sourceUrl ? `<button data-url="${escapeText(sourceUrl)}">打开来源页面 ↗</button>` : ''}</article>`;
    }).join('') || '<div class="citation-note">没有检索到候选。请检查拼写、补充 DOI，或改用学校图书馆数据库。</div>';
  } catch (error) {
    status.textContent = `${error.message}。可稍后重试或使用学校已授权的数据库。`;
  }
}
document.getElementById('citationSearchButton').onclick = searchCitations;
document.getElementById('citationQuery').onkeydown = event => { if (event.key === 'Enter') searchCitations(); };
document.getElementById('citationResults').onclick = event => {
  const button = event.target.closest('button[data-url]');
  if (button) window.open(button.dataset.url, '_blank', 'noopener,noreferrer');
};
