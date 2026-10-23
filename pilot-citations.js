// Phase-one citation review integrated with the report's revision history.
const citationPanel = document.createElement('section');
citationPanel.className = 'panel';
citationPanel.innerHTML = '<h3>引用基础检查</h3><label>指定格式<select id="citationStyle"><option value="unspecified">未指定：仅检查关联及字段</option><option value="apa-7">APA 7 基础字段规则</option></select></label><label>输入范围<select id="citationScope"><option value="complete">完整报告</option><option value="fragment">报告片段</option></select></label><button id="runCitationCheck">检查当前报告引用</button><div id="liveCitations"></div>';
document.querySelector('#workspacePage').append(citationPanel);
const originalRenderReport = renderReport;
renderReport = function(report) { originalRenderReport(report); renderLiveCitations(); };
function renderLiveCitations() {
  const box = document.getElementById('liveCitations');
  box.replaceChildren();
  const check = state.report?.citation_check;
  if (!check) { box.append(node('p', 'muted', '尚未执行引用检查。')); return; }
  box.append(node('p', null, `${check.citations.length} 处引文 / ${check.references.length} 条参考文献；${check.citations.filter(c=>c.link_status!=='matched').length} 处关联待复核。`));
  check.limitations.forEach(t=>box.append(node('p','muted',t)));
  check.citations.forEach(c=>{const button=node('button',null,c.text+' · '+c.link_status);button.onclick=()=>reveal(c.paragraph_id);box.append(button);});
  check.references.forEach(ref=>{
    const card=node('article','panel');card.append(node('p',null,ref.text));
    const locate=node('button',null,'定位条目');locate.onclick=()=>reveal(ref.paragraph_id);card.append(locate);
    ref.format_issues.forEach(t=>card.append(node('p',null,t)));
    check.issues.filter(i=>i.reference_id===ref.id).forEach(i=>card.append(node('p',null,i.kind==='duplicate_doi'?'重复 DOI':'未识别到正文对应引文，请复核')));
    const search=node('button',null,'检索来源');const results=node('div');
    search.onclick=safeAction(async()=>{
      search.disabled=true;results.textContent='三库检索中…';
      try { const response=await fetch('/api/scholarly/search?q='+encodeURIComponent(ref.doi||ref.text.slice(0,300)));const data=await response.json();if(!response.ok)throw Error(data.error);results.replaceChildren();data.results.forEach(work=>{results.append(node('p',null,work.title+' · '+(work.sources||[]).join('/')),node('p',null,work.abstract||'没有可用摘要'));});if(!data.results.length)results.textContent='未找到候选。'; } finally {search.disabled=false;}
    });card.append(search,results);
    const note=node('textarea');note.placeholder='教师修正或复核理由（保留原条目）';note.value=check.reviews?.[ref.id]?.note||'';
    const saveReview=node('button',null,'保存此条复核');saveReview.onclick=safeAction(async()=>{if(state.dirty)await save('save');const r=await api('reports/'+state.report.id+'/citation-review',{revision:state.report.revision,reference_id:ref.id,note:note.value});renderReport(r);message('引用复核已保存。');});card.append(note,saveReview);box.append(card);
  });
}
document.getElementById('runCitationCheck').onclick=safeAction(async()=>{if(state.dirty)await save('save');const r=await api('reports/'+state.report.id+'/citations',{revision:state.report.id?state.report.revision:0,style:document.getElementById('citationStyle').value,completeness:document.getElementById('citationScope').value});renderReport(r);message('引用基础检查完成，请复核结果。');});
