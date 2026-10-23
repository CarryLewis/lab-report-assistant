// One source of truth for the map badges, feedback cards and source highlights.
const reviewFindings = [
  {id:1, kind:'strength', section:'results', evidence:'resultsObservation', title:'结果与数据分析', summary:'提供了具体观测数值与增长趋势。', detail:'报告给出了起始及后期 OD₆₀₀ 数值，并指出增长最快的时间段，便于读者理解数据变化。', feedback:'Your report presents specific OD measurements and identifies the period of fastest growth, making the observed trend clear.'},
  {id:2, kind:'issue', section:'results', evidence:'resultEvidence', title:'结果与数据分析', summary:'缺少重复测量与误差范围。', detail:'报告未展示重复测量或误差范围，需进一步核实结果变异以及进入稳定期的判断依据。', feedback:'Include replicate measurements and estimates of variability to support your interpretation of the growth pattern.'},
  {id:3, kind:'strength', section:'methods', evidence:'methodsDescription', title:'实验方法与可重复性', summary:'说明了培养与采样条件。', detail:'方法描述了培养温度、采样间隔、测量波长及空白对照，为理解实验过程提供了基础。', feedback:'The incubation temperature, sampling interval, measurement wavelength and blank are clearly described.'},
  {id:4, kind:'issue', section:'methods', evidence:'methodEvidence', title:'实验方法与可重复性', summary:'单次测量；校准步骤待核实。', detail:'原文说明每次只测量一次；同时未见仪器校准流程的说明。请核对重复性及校准信息是否充分。', feedback:'Use replicate measurements and clarify the instrument calibration procedure to improve reproducibility.'}
];
document.getElementById('results').nextElementSibling.id='resultsObservation';
document.getElementById('methods').nextElementSibling.id='methodsDescription';
document.querySelectorAll('.paper .evidence').forEach(n=>n.classList.remove('evidence'));
let activeFinding=null, pinnedFinding=null, hoverTimer;
const labelFor=f=>f.kind==='strength'?'优点':'问题';
function badge(f){return `<span class="finding-number ${f.kind}">${f.id}</span>`;}
const pane=document.getElementById('reviewPane');
pane.querySelectorAll('.rubric').forEach(n=>n.remove());
const finalLabel=[...pane.querySelectorAll('.sectionlabel')].find(n=>n.textContent.includes('学生反馈')||n.textContent.includes('最终反馈'));
const hint=document.createElement('p');hint.className='link-hint';hint.textContent='悬停建议，同步定位原文与导图；点击编号可固定定位。';finalLabel.before(hint);
reviewFindings.forEach(f=>{
  const card=document.createElement('article');card.className=`rubric finding-card ${f.kind}`;card.id=`finding-${f.id}`;card.dataset.finding=f.id;card.tabIndex=0;
  card.innerHTML=`<div class="rubric-top"><b>${badge(f)} ${f.title}</b><span class="score">待教师评分</span></div><div class="review-status">审核状态：待教师判断 · ${labelFor(f)}</div><p>${f.detail}</p><div class="evidence-summary"><span class="evidence-pill">${labelFor(f)}证据 · ${f.section==='results'?'Results':'Methods'}</span><span class="evidence-pill">原文编号 ${f.id}</span></div><button class="evidence-link">查看原文与导图定位 →</button><div class="confidence">${f.kind==='strength'?'高':'中等'}置信度 · 仅基于当前报告可见内容，需教师结合 rubric 确认。</div><div class="level-label">教师选择该 criterion 等级</div><div class="level-picker" role="group" aria-label="${f.title}等级"><button data-score="4">优秀</button><button data-score="3">良好</button><button data-score="2">合格</button><button data-score="1">需改进</button></div><div class="feedback-example"><b>学生反馈草稿 · AI 生成</b><div class="feedback-text">${f.feedback}</div><small>尚未确认 · 发布前由教师编辑</small></div><div class="actions"><button class="accept">采用并确认</button><button>编辑理由</button><button>不采用</button></div>`;
  finalLabel.before(card);
  const status=card.querySelector('.review-status'), text=card.querySelector('.feedback-text'), buttons=card.querySelectorAll('.actions button');
  card.querySelectorAll('.level-picker button').forEach(level=>level.onclick=()=>{card.querySelectorAll('.level-picker button').forEach(n=>n.classList.remove('active'));level.classList.add('active');card.querySelector('.score').textContent=`${level.textContent} · ${level.dataset.score}/4`;status.textContent='审核状态：教师已选择等级';status.style.color='#245f8f';document.getElementById('saveState').textContent='正在保存…';setTimeout(()=>document.getElementById('saveState').textContent='所有更改已保存',450);});
  buttons[0].onclick=()=>{if(!card.querySelector('.level-picker .active')){showToast('请先选择该评分项的等级');return;}status.textContent='审核状态：教师已确认';status.style.color='#18794e';const t=pane.querySelector('textarea[placeholder]');if(!t.value.includes(text.textContent))t.value+=(t.value?'\n\n':'')+text.textContent;confirmedCriteria.add(f.title);updateReviewProgress();buttons[0].textContent='已确认';showToast('已确认评分项并加入学生反馈草稿');};
  buttons[1].onclick=()=>{text.contentEditable='true';text.focus();status.textContent='审核状态：正在编辑理由';};
  buttons[2].onclick=()=>{status.textContent='审核状态：教师未采用此建议';card.classList.add('dismissed');};
  card.querySelector('.evidence-link').onclick=()=>pinFinding(f.id);
  card.addEventListener('pointerenter',()=>{clearTimeout(hoverTimer);hoverTimer=setTimeout(()=>activateFinding(f.id,'card'),140);});
  card.addEventListener('pointerleave',()=>{clearTimeout(hoverTimer);activateFinding(pinnedFinding,'none');});
  card.addEventListener('focusin',()=>activateFinding(f.id,'card'));
  card.addEventListener('focusout',e=>{if(!card.contains(e.relatedTarget))activateFinding(pinnedFinding,'none');});
});
const legend=document.createElement('div');legend.className='finding-legend';legend.innerHTML='<span><i class="legend-dot strength"></i>优点</span><span><i class="legend-dot issue"></i>问题</span><small>编号对应右侧建议</small>';switcher.after(legend);
function renderMapLinks(){
  const isArgument=switcher.querySelectorAll('button')[1].classList.contains('active');
  if(isArgument){
    // Give the argument view explicit section anchors as well as claim relationships.
    map.innerHTML='<div class="rootnode">主旨：菌群增长，后期增速放缓</div>'+[
      ['methods','实验设计与方法','培养、采样与 OD₆₀₀ 测量为论证提供方法基础'],
      ['results','分论点：观测到菌群增长','OD₆₀₀ 数值变化支持增长趋势'],
      ['discussion','解释与局限','作者提出营养限制等解释，证据充分性需核实'],
      ['conclusion','结论','增加重复测量可提高结果可信度']
    ].map(([section,title,desc])=>`<div class="argument-node" data-section="${section}"><b>${title}</b><small>${desc}</small><div class="map-findings"></div><button onclick="jumpTo('${section}')">定位原文 ↗</button></div>`).join('');
  }else{
    map.innerHTML=outline;
    map.querySelectorAll('.branch').forEach(branch=>{branch.dataset.section=branch.querySelector('.leaf').dataset.target;const wrap=document.createElement('div');wrap.className='map-findings';branch.querySelector('.branch-title').after(wrap);});
  }
  map.querySelectorAll('[data-section]').forEach(node=>{
    const wrap=node.querySelector('.map-findings');
    reviewFindings.filter(f=>f.section===node.dataset.section).forEach(f=>{
      const button=document.createElement('button');button.className=`map-finding ${f.kind}`;button.dataset.finding=f.id;button.innerHTML=badge(f)+`<span>${labelFor(f)} · ${f.summary}</span>`;button.setAttribute('aria-label',`${f.id}号${labelFor(f)}：${f.summary}`);
      button.onmouseenter=()=>activateFinding(f.id,'map');button.onmouseleave=()=>activateFinding(pinnedFinding,'none');button.onfocus=()=>activateFinding(f.id,'map');button.onblur=()=>activateFinding(pinnedFinding,'none');button.onclick=()=>pinFinding(f.id);wrap.append(button);
    });
  });
  activateFinding(activeFinding,'none');
}
switcher.querySelectorAll('button').forEach(b=>b.onclick=()=>{switcher.querySelectorAll('button').forEach(x=>x.classList.remove('active'));b.classList.add('active');renderMapLinks();});
function revealWithin(container,node){
  if(!node||!container)return;
  const c=container.getBoundingClientRect(),n=node.getBoundingClientRect();
  if(n.top<c.top+20||n.bottom>c.bottom-20)container.scrollTo({top:Math.max(0,container.scrollTop+n.top-c.top-container.clientHeight/2+Math.min(n.height,container.clientHeight)/2),behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});
}
function activateFinding(id,origin){
  activeFinding=id;
  document.querySelectorAll('.linked-active,.source-strength,.source-issue').forEach(n=>n.classList.remove('linked-active','source-strength','source-issue'));
  if(!id)return;
  const f=reviewFindings.find(x=>x.id===id),source=document.getElementById(f.evidence),card=document.getElementById(`finding-${id}`),bubble=map.querySelector(`[data-finding="${id}"]`);
  card.classList.add('linked-active');if(bubble)bubble.classList.add('linked-active');source.classList.add(`source-${f.kind}`);
  if(origin!=='none'){
    revealWithin(document.querySelector('.document'),source);
    if(origin==='card')revealWithin(map,bubble);
    if(origin==='map')revealWithin(document.querySelector('.rightbody'),card);
  }
}
function pinFinding(id){pinnedFinding=pinnedFinding===id?null:id;activateFinding(pinnedFinding,'map');document.querySelectorAll('.finding-card').forEach(n=>n.classList.toggle('pinned',Number(n.dataset.finding)===pinnedFinding));}
document.addEventListener('keydown',e=>{if(e.key==='Escape'){pinnedFinding=null;activateFinding(null,'none');document.querySelectorAll('.pinned').forEach(n=>n.classList.remove('pinned'));}});
renderMapLinks();
