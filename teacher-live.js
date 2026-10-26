'use strict';
/* BEGIN DOCUMENT OUTLINE */
/* Source-anchored document hierarchy. Review findings are deliberately not TOC nodes. */
(function(root){'use strict';
function heading(paragraph){
 const text=paragraph.text.trim();if(text.length>150||/^[+\-\d\s.,%]+$/.test(text))return null;
 const numbered=text.match(/^(\d+(?:\.\d+)*)(?:\.\s*|\s+)(\S.*)$/);
 if(numbered&&text.length<110&&!/[;?!。；]$/.test(text)&&!/^\d+\s+(?:minutes?|hours?|species|samples?|points?)\b/i.test(text))return {title:text,level:Math.min(5,numbered[1].split('.').length)};
 if(paragraph.heading||/^(abstract|introduction|background|aims?|objectives?|materials(?: and methods)?|methods|results|discussion|conclusions?|references|appendi(?:x|ces))$/i.test(text))return {title:text,level:1};
 return null;
}
function build(report){
 const paragraphs=report.paragraphs||[],index=new Map(paragraphs.map((p,i)=>[p.id,i]));
 const aiOutline=report.teacher_maps?.outline??report.analysis?.outline??[];
 const aiClaims=report.teacher_maps?.claims??report.analysis?.claims??[];
 const nodes=[];
 for(let i=0;i<paragraphs.length;i++){const h=heading(paragraphs[i]);if(h)nodes.push({...h,start:i,paragraph_ids:[paragraphs[i].id],quote:paragraphs[i].text,page:paragraphs[i].page,kind:'heading',children:[]});}
 if(!nodes.length){for(const entry of aiOutline){const refs=(entry.paragraph_ids||[]).filter(id=>index.has(id));if(refs.length)nodes.push({...entry,level:1,start:Math.min(...refs.map(id=>index.get(id))),paragraph_ids:refs,kind:'heading',children:[]});}nodes.sort((a,b)=>a.start-b.start);}
 if(!nodes.length&&paragraphs.length)nodes.push({title:'正文',level:1,start:0,paragraph_ids:[paragraphs[0].id],kind:'heading',children:[]});
 for(let i=0;i<nodes.length;i++){
  const n=nodes[i];n.key='outline:'+n.paragraph_ids.join(',');
  const ai=aiOutline.find(e=>e.paragraph_ids?.[0]===n.paragraph_ids[0]);
  n.title=report.map_edits?.[n.key]??(ai&&report.map_edits?.['outline:'+ai.paragraph_ids.join(',')])??n.title;
  n.end=nodes.slice(i+1).find(next=>next.level<=n.level)?.start??paragraphs.length;
 }
 const before=paragraphs.slice(0,nodes[0]?.start||0);const titleParagraph=before.find(p=>p.text.length>25&&!p.visual_only);
 const tree={title:titleParagraph?.text||report.filename||'文章框架',paragraph_ids:titleParagraph?[titleParagraph.id]:[],children:[],sections:nodes.length,claims:0};
 const stack=[];
 for(const node of nodes){while(stack.length&&stack.at(-1).level>=node.level)stack.pop();(stack.at(-1)?.children||tree.children).push(node);stack.push(node);}
 for(const entry of aiClaims){
  const refs=(entry.paragraph_ids||[]).filter(id=>index.has(id));if(!refs.length)continue;
  const positions=refs.map(id=>index.get(id));
  const owner=nodes.filter(n=>positions.every(pos=>pos>=n.start&&pos<n.end)).sort((a,b)=>b.level-a.level)[0];
  const key='claims:'+refs.join(',');
  const point={...entry,title:report.map_edits?.[key]??entry.title,key,kind:'claim',paragraph_ids:refs,quote:entry.quote||paragraphs[index.get(refs[0])].text,page:entry.page||paragraphs[index.get(refs[0])].page};
  (owner?.children||tree.children).push(point);tree.claims++;
 }
 return tree;
}
function markdown(tree){const clean=value=>String(value).replace(/[\r\n]+/g,' ').replace(/([\\`*_\[\]<>])/g,'\\$1');const lines=['# '+clean(tree.title),''];
 function walk(nodes,depth){for(const n of [...nodes.filter(n=>n.kind==='claim'),...nodes.filter(n=>n.kind!=='claim')]){if(n.kind==='claim')lines.push('- '+clean(n.title));else{lines.push('','#'.repeat(Math.min(6,depth))+' '+clean(n.title));walk(n.children,depth+1);}}}
 walk(tree.children,2);return lines.join('\n').trim()+'\n';}
const api={build,markdown,heading};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.LabwiseOutline=api;
})(typeof window!=='undefined'?window:globalThis);

/* END DOCUMENT OUTLINE */
const $=id=>document.getElementById(id);
const state={bootstrap:null,report:null,map:'outline',dirty:false,busy:false,section:'home'};
const gradingNames={not_started:'未开始',in_progress:'批改中',completed:'已完成'};
const statusNames={parsed:'待自动分析',queued:'AI 排队中',waiting_key:'等待 AI 连接',analyzing:'AI 分析中',ready:'AI 结果就绪',failed:'AI 分析失败'};
function node(tag,cls,content){const n=document.createElement(tag);if(cls)n.className=cls;if(content!==undefined)n.textContent=content;return n;}
let messageTimer;
function message(msg,error=false){$('message').textContent=msg;$('message').classList.toggle('error',error);$('message').hidden=false;clearTimeout(messageTimer);messageTimer=setTimeout(()=>$('message').hidden=true,error?10000:5000);}
async function api(path,body){const res=await fetch('/api/pilot/'+path,{method:body===undefined?'GET':'POST',headers:body===undefined?{}:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)});const data=await res.json();if(!res.ok)throw Error(data.error||'请求失败');return data;}
function protectChange(){if(state.navigating||state.uploading||state.saving||assignmentEditor.loading||assignmentEditor.saving){message('正在保存或读取评分标准，请稍候。');return false;}return !(state.dirty||assignmentEditor.dirty)||window.confirm('还有未保存的修改，确定离开吗？');}
const teacherViews=[{name:'home',id:'dashboardHome'},{name:'assignments',id:'assignmentSettings'},{name:'standards',id:'standardsSettings'},{name:'analytics',id:'analyticsSettings'},{name:'settings',id:'settingsSettings'}];
function page(name){
  if(name==='reports')name='home';const review=name==='workspace';
  document.body.classList.toggle('review-active',review);
  $('entryPage').classList.toggle('hidden',review);$('liveReview').hidden=!review;
  for(const v of teacherViews)$(v.id).hidden=review||v.name!==name;
  state.section=review?'workspace':name;
  document.querySelectorAll('.nav-item').forEach((b,i)=>{const active=teacherViews[i].name===name;b.classList.toggle('active',active);if(active)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current');});
  $('homeNav').classList.toggle('hidden',!review);$('workspaceStatus').classList.toggle('hidden',!review);
  const hash=review?'#review='+encodeURIComponent(state.report.id):name==='home'?'#':'#'+name;
  if(location.hash!==hash)history.pushState(null,'',hash);
  closeTeacherNavigation();window.scrollTo(0,0);
}
function dirty(){state.dirty=true;$('draftState').textContent='有未保存修改';$('export').disabled=true;}
function safeAction(fn){return async()=>{try{await fn();}catch(e){message(e.message,true);}};}
function renderConnectionSettings(settings){
  const connected=Boolean(settings.has_key),managed=settings.key_source==='environment';
  $('connectionSummary').classList.toggle('connected',connected);
  $('connectionBadge').textContent=connected?'已连接':'未连接';
  $('keyState').textContent=connected?'辅助分析服务已连接':'尚未配置访问密钥';
  $('connectionDetail').textContent=connected
    ?(managed?'密钥由服务器部署环境提供，可测试连接或更换为本机保存的密钥。':'密钥已保存在本机且仅当前用户可读，刷新页面或重启服务后仍会保留。')
    :'输入密钥并连接后，系统会记住此配置。';
  $('apiKeyEditor').hidden=connected;$('connectActions').hidden=connected;$('connectedActions').hidden=!connected;
  $('cancelKeyChange').hidden=true;$('apiKey').required=!connected;$('apiKey').value='';
  $('clearKey').disabled=managed;$('clearKey').title=managed?'部署环境提供的密钥需由部署者移除。':'';
}
async function refresh(){
  state.bootstrap=await api('bootstrap');const data=state.bootstrap;
  const selected=$('assignmentSelect').value;$('assignmentSelect').replaceChildren();
  data.assignments.forEach(a=>{const o=node('option',null,a.title+' · 第 '+a.revision+' 版');o.value=a.id;$('assignmentSelect').append(o);});
  if(data.assignments.some(a=>a.id===selected))$('assignmentSelect').value=selected;
  assignmentInfo();$('upload').disabled=!data.assignments.length;
  $('model').value=data.settings.model;renderConnectionSettings(data.settings);
  renderAssignmentLibrary(data.assignments);drawReportList();renderMetrics();applyPreferences();renderReviewSequence();
}
// Keep branch expansion and keyboard focus stable during automatic status polling.
const reportGroupOpen=new Map();
let reportListSignature='';
function drawReportList(){
  const query=$('reportSearch').value.trim().toLowerCase(),filter=$('reportFilter').value;
  const reports=(state.bootstrap?.reports||[]).filter(r=>!r.sample);
  const assignments=state.bootstrap?.assignments||[];
  const signature=JSON.stringify([query,filter,reports,assignments.map(a=>[a.id,a.title,a.type])]);
  if(signature===reportListSignature)return;
  reportListSignature=signature;
  const groups=new Map(assignments.map(a=>[a.id,{id:a.id,title:a.title,reports:[]}]));
  for(const r of reports){
    const key=r.assignment_id||'legacy:'+r.assignment_title;
    if(!groups.has(key))groups.set(key,{id:key,title:r.assignment_title||'未命名作业题',reports:[]});
    groups.get(key).reports.push(r);
  }
  const list=$('reportList');list.replaceChildren();
  const overview=node('div','assignment-review-overview');
  overview.append(node('strong',null,groups.size+' 个作业题'),node('span',null,'共 '+reports.length+' 份作业 · 已确认评分计为已批改'));
  list.append(overview);
  let visible=0;
  for(const group of groups.values()){
    const titleMatch=group.title.toLowerCase().includes(query);
    const matches=group.reports.filter(r=>(!query||titleMatch||(r.filename+' '+(r.student_alias||'')).toLowerCase().includes(query))&&(filter==='all'||(filter==='confirmed'?r.confirmed:filter==='pending'?!r.confirmed:r.grading_state===filter)));
    if((query||filter!=='all')&&!matches.length&&!(filter==='all'&&titleMatch))continue;
    visible++;
    const done=group.reports.filter(r=>r.confirmed).length,total=group.reports.length;
    const drafts=group.reports.filter(r=>!r.confirmed&&r.grading_state==='in_progress');
    const checkpoint=[...drafts].sort((a,b)=>((b.review_progress||{}).last_opened||'').localeCompare((a.review_progress||{}).last_opened||''))[0];
    const task=node('div','assignment-review-task');
    const branch=node('details','assignment-review-group');branch.dataset.assignmentId=group.id;
    branch.open=reportGroupOpen.get(group.id)??false;
    branch.ontoggle=()=>{reportGroupOpen.set(group.id,branch.open);branch.querySelector('.assignment-review-toggle').textContent=branch.open?'收起作业':'查看作业';};
    const summary=node('summary','assignment-review-summary');
    const heading=node('div','assignment-review-heading');heading.append(node('span','assignment-review-label','作业题'),node('h3',null,group.title));
    const counts=node('div','assignment-review-counts');
    counts.append(node('span',null,'共 '+total+' 份'),node('span','graded-count','已批改 '+done),node('span','pending-count','未批改 '+(total-done)));
    if(drafts.length)counts.append(node('span','in-progress-count','批改中 '+drafts.length));
    heading.append(counts);
    if(checkpoint)heading.append(node('p','assignment-resume-hint','上次停在：'+checkpoint.filename));
    const progress=node('div','assignment-review-progress');
    progress.setAttribute('role','progressbar');progress.setAttribute('aria-label',group.title+'批改进度');progress.setAttribute('aria-valuemin','0');progress.setAttribute('aria-valuemax',String(total||1));progress.setAttribute('aria-valuenow',String(done));progress.setAttribute('aria-valuetext',done+' / '+total+' 份已批改');
    const fill=node('span');fill.style.width=(total?done/total*100:0)+'%';progress.append(fill);heading.append(progress);
    summary.append(node('span','assignment-review-chevron','›'),heading,node('span','assignment-review-toggle',branch.open?'收起作业':'查看作业'));branch.append(summary);
    const children=node('div','assignment-review-files');
    if(!matches.length)children.append(node('p','muted','此作业题尚未导入学生作业，可在“导入新报告”中选择该作业题后上传。'));
    else if(matches.length!==total)children.append(node('p','assignment-review-filter-note','当前筛选显示 '+matches.length+' / '+total+' 份作业'));
    matches.sort((a,b)=>(a.import_order||0)-(b.import_order||0)||a.id.localeCompare(b.id)).forEach(r=>{
      const row=node('div','report-record'),button=node('button','report-open',r.filename);
      button.append(node('small',null,(r.student_alias?r.student_alias+' · ':'')+(gradingNames[r.grading_state]||(r.confirmed?'已完成':'未开始'))));
      button.onclick=safeAction(async()=>{if(!state.busy&&protectChange())await openReport(r.id);});
      const phase=node('span','ai-state state-'+r.status,r.has_ai_result?'AI 结果可查看':statusNames[r.status]||'待自动分析');row.append(button,phase);
      if(r.status==='failed'&&!r.has_ai_result){
        const retry=node('button','archive-action','重试分析');retry.onclick=safeAction(async()=>{retry.disabled=true;try{const current=await api('reports/'+r.id);await api('reports/'+r.id+'/auto-analysis',{revision:current.revision,retry:true});await refresh();message('已重新排队分析。');}finally{retry.disabled=false;}});row.append(retry);
      }
      if(r.status==='waiting_key'){const connect=node('button','archive-action','配置连接');connect.onclick=()=>openTeacherSection('settings');row.append(connect);}
      const archive=node('button','archive-action','归档');archive.onclick=safeAction(async()=>{if(!window.confirm('将此报告移出任务列表？已保存的内容仍会保留。'))return;const current=await api('reports/'+r.id);await api('reports/'+r.id+'/archive',{revision:current.revision});await refresh();});row.append(archive);children.append(row);
    });
    branch.append(children);task.append(branch);
    const action=total===0?'等待导入':done===total?'全部已完成':drafts.length||done?'继续批改':'开始批改';
    const resume=node('button','assignment-resume-button',action);
    resume.disabled=total===0||done===total;resume.setAttribute('aria-label',action+'：'+group.title);
    resume.onclick=safeAction(()=>continueAssignment(group.id));task.append(resume);
    if(total&&done===total){const exportAll=node('button','assignment-export-button','导出批改包');exportAll.onclick=safeAction(async()=>{exportAll.disabled=true;try{const pack=await api('assignments/'+encodeURIComponent(group.id)+'/export-review');downloadBase64Package(pack);message('Word 原稿、批注稿及评分数据已导出。');}finally{exportAll.disabled=false;}});task.append(exportAll);}
    list.append(task);
  }
  if(!visible)list.append(node('p','muted',groups.size?'暂无匹配作业，请调整搜索或批改状态。':'尚无作业题。先创建作业题，再导入学生作业。'));
}

function renderMetrics(){const reports=state.bootstrap.reports.filter(r=>!r.sample);$('pendingCount').textContent=reports.filter(r=>!r.confirmed).length;$('failedCount').textContent=reports.filter(r=>['failed','waiting_key'].includes(r.status)).length;$('completionRate').textContent=(reports.length?Math.round(reports.filter(r=>r.confirmed).length/reports.length*100):0)+'%';}
function assignmentInfo(){const a=state.bootstrap?.assignments.find(a=>a.id===$('assignmentSelect').value);$('rubricInfo').textContent=a?a.rubric.name+' · '+a.rubric.criteria.length+' 个评分项':'';}
async function createReport(){
  if(state.uploading||!protectChange())return;
  const assignment=state.bootstrap.assignments.find(a=>a.id===$('assignmentSelect').value);
  if(!assignment)throw Error('请先创建并保存作业题和评分标准。');
  const file=$('reportFile').files[0];
  if(!file||!(/\.docx$/i.test(file.name)))throw Error('请选择 Word（.docx）文件。');
  if(file.size>10*1024*1024)throw Error('文件不能超过 10 MB。');
  state.uploading=true;$('upload').disabled=true;
  try{
    const bytes=new Uint8Array(await file.arrayBuffer());let binary='';
    for(let i=0;i<bytes.length;i+=8192)binary+=String.fromCharCode(...bytes.subarray(i,i+8192));
    const report=await api('reports',{sample:false,assignment_id:assignment.id,assignment_revision:assignment.revision,filename:file.name,file:btoa(binary)});
    state.dirty=false;await openReport(report.id);$('reportFile').value='';
    try{await refresh();}catch{message('报告已保存，但任务列表刷新失败。',true);}
  }finally{state.uploading=false;$('upload').disabled=false;}
}
function rememberReview(r){
  const item=state.bootstrap?.reports.find(item=>item.id===r.id);
  if(item)Object.assign(item,{grading_state:r.confirmed?'completed':'in_progress',review_progress:r.review_progress||item.review_progress});
}
async function openReport(id){
  if(state.navigating)return;
  state.navigating=true;
  try{
    let r=await api('reports/'+id+'/start-review',{});rememberReview(r);
    if(!r.confirmed&&(r.analysis||{}).mode!=='deepseek'&&['parsed','ready'].includes(r.status))r=await api('reports/'+id+'/auto-analysis',{revision:r.revision});
    renderReport(r);page('workspace');drawReportList();
  }finally{state.navigating=false;}
}
async function continueAssignment(id,afterConfirm=false){
  if(state.navigating)return;
  if(!afterConfirm&&(state.busy||state.saving||!protectChange()))return;
  state.navigating=true;
  try{
    const result=await api('assignments/'+encodeURIComponent(id)+'/continue-review',{});
    if(!result.report){renderReviewSequence();message('本作业题的全部作业均已批改完成。');return;}
    rememberReview(result.report);renderReport(result.report);page('workspace');drawReportList();
    message(afterConfirm?'上一份已确认，已打开下一份未完成作业。':result.resumed?'已打开本题上次未完成的作业。':'已开始批改本题的第一份未完成作业。');
  }finally{state.navigating=false;}
}
function renderReviewSequence(){
  const r=state.report;if(!r)return;
  const reports=(state.bootstrap?.reports||[]).filter(item=>item.assignment_id===r.assignment.id&&!item.sample);
  const done=reports.filter(item=>item.id===r.id?r.confirmed:item.confirmed).length;
  const next=reports.some(item=>item.id!==r.id&&!item.confirmed);
  $('reviewQueueState').textContent=r.assignment.title+' · 已完成 '+done+' / '+reports.length+' 份 · 当前'+(r.confirmed?'已完成':'批改中');
  $('confirm').textContent=next?'确认并批改下一份':'确认评分与反馈';
  $('save').title='保存草稿，下次从本题继续批改';
}

function reviewPayload(){const scores={};for(const input of $('scores').querySelectorAll('input'))if(input.value!=='')scores[input.dataset.id]=Number(input.value);return {revision:state.report.revision,notes:$('notes').value,feedback:$('feedback').value,scores,suggestion_edits:state.report.suggestion_edits||{},reviews:state.report.reviews,teacher_summary:$('summary').value,map_edits:state.report.map_edits||{},teacher_maps:state.report.teacher_maps||{},annotations:state.report.annotations||[],visual_decisions:Object.fromEntries((state.report.visual_reviews||[]).map(v=>[v.id,v.decision||'pending']))};}
function total(){let score=0,maximum=0,complete=0;for(const input of $('scores').querySelectorAll('input')){maximum+=Number(input.max);if(input.value!==''){score+=Number(input.value);complete++;}}$('total').textContent=`教师评分：${score.toFixed(1)} / ${maximum} · 已填写 ${complete} 项`;}
function renderReport(r){const changedReport=state.report?.id!==r.id;state.report=r;state.baseReport=structuredClone(r);state.dirty=false;if(changedReport)clearOriginalPreview();$('headerReportState').textContent=r.student_alias||r.filename;$('filename').textContent=r.filename;$('status').textContent=(r.confirmed?'已完成':'批改中')+' · '+(statusNames[r.status]||r.status);$('snapshot').textContent=r.assignment.rubric.name+' · v'+r.assignment.rubric.version;$('workNotice').textContent=analysisNotice(r);$('autoAnalysisHint').textContent=analysisNotice(r);$('notes').value=r.notes;$('feedback').value=r.feedback;$('summary').value=r.teacher_summary??'';$('aiSummary').textContent=r.analysis?.mode==='deepseek'?r.analysis.summary:analysisNotice(r);$('aiAnalysisInfo').textContent=r.analysis?(r.analysis.mode==='deepseek'?'AI · '+r.analysis.model:'结构提取 · 未调用 AI')+' · '+(r.analysis.findings?.length||0)+' 条建议 · '+new Date(r.analysis.generated).toLocaleString()+(r.error?' · 显示上次成功结果，本次分析失败':''):'';$('scores').replaceChildren();r.assignment.rubric.criteria.forEach(c=>{const label=node('label','score-row',c.name+' / '+c.maximum_points);const input=node('input');input.setAttribute('aria-label',c.name+'评分');input.type='number';input.min=0;input.max=c.maximum_points;input.step='0.1';input.dataset.id=c.id;input.value=r.scores[c.id]??'';input.oninput=()=>{dirty();total();};label.append(input);$('scores').append(label);});total();renderMap();renderFindings();applyPreferences();renderReviewSequence();$('export').disabled=!r.confirmed;$('draftState').textContent=r.confirmed?'教师已确认，可导出反馈':'草稿 · 最近保存 '+new Date(r.updated).toLocaleString();renderAnnotations();renderWordCoverage();if(changedReport)void showOriginal();}
const outlineUI={collapsed:new Set(),query:'',active:null,editing:false,reportID:null};
function renderMap(){
 const r=state.report;if(!r)return;
 if(outlineUI.reportID!==r.id){outlineUI.collapsed.clear();outlineUI.active=null;outlineUI.reportID=r.id;outlineUI.query='';$('outlineSearch').value='';}
 const tree=LabwiseOutline.build(r),host=$('map');host.replaceChildren();
 const title=node('button','outline-document-title',tree.title);title.onclick=()=>{if(tree.paragraph_ids.length)void reveal(tree.paragraph_ids[0]);};host.append(title);
 host.append(node('p','outline-meta',tree.children.filter(n=>n.kind==='heading').length+' 个主章节 · '+tree.sections+' 个标题 · '+tree.claims+' 个分论点'));
 const query=outlineUI.query.trim().toLowerCase(),claimsOnly=state.map==='claims';
 const hasPoint=n=>n.kind==='claim'||n.children?.some(hasPoint);
 const matches=n=>n.title.toLowerCase().includes(query)||n.children?.some(matches);
 const list=node('ul','outline-tree');list.setAttribute('aria-label','文章章节与分论点');
 function draw(nodes,parent,depth){for(const n of [...nodes.filter(n=>n.kind==='claim'),...nodes.filter(n=>n.kind!=='claim')]){if(query&&!matches(n))continue;if(claimsOnly&&!hasPoint(n))continue;
  const item=node('li','outline-item '+n.kind),row=node('div','outline-row');row.style.setProperty('--outline-depth',depth);
  const children=n.children||[],expandable=children.length>0,collapsed=outlineUI.collapsed.has(n.key)&&!query;
  const toggle=node('button','outline-toggle',expandable?(collapsed?'▸':'▾'):'');toggle.disabled=!expandable;toggle.setAttribute('aria-label',(collapsed?'展开':'收起')+n.title);if(expandable){toggle.setAttribute('aria-expanded',String(!collapsed));toggle.onclick=()=>{if(collapsed)outlineUI.collapsed.delete(n.key);else outlineUI.collapsed.add(n.key);renderMap();};}
  const label=node('button','outline-link',n.title);label.dataset.outlineKey=n.key;label.title=n.title;label.setAttribute('aria-label',(n.kind==='claim'?'分论点：':'章节：')+n.title);if(outlineUI.active===n.key)label.setAttribute('aria-current','location');
  label.onclick=()=>{outlineUI.active=n.key;host.querySelectorAll('[aria-current]').forEach(el=>el.removeAttribute('aria-current'));label.setAttribute('aria-current','location');void reveal(n.paragraph_ids[0],n.quote,n.page);};
  row.append(toggle,node('span','outline-symbol',n.kind==='claim'?'•':'≡'),label);
  if(outlineUI.editing){const edit=node('button','outline-edit','✎');edit.setAttribute('aria-label','重命名'+n.title);edit.onclick=()=>{const value=window.prompt('编辑'+(n.kind==='claim'?'分论点':'章节')+'标题',n.title);if(!value?.trim())return;r.map_edits??={};r.map_edits[n.key]=value.trim().slice(0,500);dirty();renderMap();};row.append(edit);}
  item.append(row);if(expandable&&!collapsed){const nested=node('ul','outline-children');draw(children,nested,depth+1);item.append(nested);}parent.append(item);
 }}
 draw(tree.children,list,0);host.append(list);
 if(!list.children.length)host.append(node('p','outline-empty',query?'没有匹配的章节或分论点。':claimsOnly?'尚无分论点分析，生成 AI 分析后会按章节显示。':'尚未识别出文章结构。'));
 host.append(node('p','outline-caption','章节来自原文标题；分论点来自 AI 提炼。点击条目，在原页核对。'));
 $('editOutline').setAttribute('aria-pressed',String(outlineUI.editing));
}
$('outlineSearch').oninput=()=>{outlineUI.query=$('outlineSearch').value;renderMap();};
$('editOutline').onclick=()=>{outlineUI.editing=!outlineUI.editing;renderMap();};
$('collapseOutline').onclick=()=>{outlineUI.collapsed.clear();const tree=LabwiseOutline.build(state.report);function collapse(nodes){nodes.forEach(n=>{if(n.children?.length){outlineUI.collapsed.add(n.key);collapse(n.children);}});}collapse(tree.children);renderMap();};
$('expandOutline').onclick=()=>{outlineUI.collapsed.clear();renderMap();};
$('copyOutline').onclick=()=>{if(!state.report)return;$('outlineMarkdown').value=LabwiseOutline.markdown(LabwiseOutline.build(state.report));$('outlineExportDialog').showModal();};
$('closeOutlineExport').onclick=()=>$('outlineExportDialog').close();
$('downloadOutline').onclick=()=>{download($('outlineMarkdown').value,state.report.filename.replace(/\.[^.]+$/,'')+'-outline.md','text/markdown;charset=utf-8');message('Markdown 文件已生成，可导入 Notion。');};
$('copyOutlineText').onclick=safeAction(async()=>{try{if(!navigator.clipboard?.writeText)throw Error('Clipboard unavailable');await navigator.clipboard.writeText($('outlineMarkdown').value);message('Markdown 已复制，可粘贴到 Notion。');}catch{$('outlineMarkdown').focus();$('outlineMarkdown').select();message('请复制已选中的 Markdown，或下载文件。');}});
async function decideFinding(fid,action,decision,feedback){
 if(state.busy||state.saving)throw Error('请等待当前保存完成。');
 if(state.dirty)await save('save');
 state.saving=true;
 try{
  const r=await api('reports/'+state.report.id+'/'+action,{revision:state.report.revision,finding_id:fid,decision,feedback});
  renderReport(r);await refresh();message(action==='reopen-finding'?'已进入修改模式，修改后请重新确认。':'建议已确认并保存。');
 }finally{state.saving=false;}
}
function renderFindings(){
 const r=state.report;const host=$('findings');host.replaceChildren();
 if(!r.analysis?.findings.length)host.append(node('p','muted','暂无候选建议。上传 Word 后会自动分析正文、表格及可读取的图表。'));
 r.analysis?.findings.forEach(f=>{
  const decision=r.reviews[f.id]||'pending',locked=['accepted','rejected'].includes(decision);
  const card=node('article','finding '+f.kind+(locked?' finding-confirmed':''));card.id='finding-'+f.id;card.tabIndex=0;
  const heading=node('div','row');heading.append(node('span','num',f.id),node('b',null,f.title));
  if(locked)heading.append(node('span','finding-confirmed-badge',decision==='rejected'?'✓ 已确认 · 不采纳':'✓ 已确认'));
  card.append(heading,node('small','muted','评分项目：'+(r.assignment.rubric.criteria.find(c=>c.id===f.criterion_id)?.name||f.criterion_id)),node('p',null,f.rationale));
  const evidence=node('button','evidence-link',f.quote?'↗ '+f.quote:'↗ 定位 Word 图表 '+(f.object_id||'').replace(/^v/,''));evidence.onclick=()=>void reveal(f.paragraph_ids.find(pid=>!f.quote||r.paragraphs.find(p=>p.id===pid)?.text.includes(f.quote))||f.paragraph_ids[0],f.quote);card.append(evidence);
  const value=r.suggestion_edits?.[f.id]??f.feedback;
  if(locked){
   card.append(node('p','confirmed-feedback',value));const edit=node('button','finding-edit','修改');edit.onclick=safeAction(()=>decideFinding(f.id,'reopen-finding',null,value));card.append(edit);
  }else{
   const draft=node('textarea');draft.rows=3;draft.setAttribute('aria-label',f.title+'反馈草稿');draft.value=value;
   draft.oninput=()=>{r.suggestion_edits??={};r.suggestion_edits[f.id]=draft.value;r.reviews[f.id]='pending';dirty();};card.append(draft);
   const actions=node('div','row');for(const [key,label] of [['accepted','确认建议'],['rejected','不采纳']]){const button=node('button',key==='accepted'?'primary':'',label);button.onclick=safeAction(()=>decideFinding(f.id,'decide-finding',key,draft.value));actions.append(button);}card.append(actions);
  }
  card.onmouseenter=()=>link(f,'card');card.onmouseleave=clearLinks;card.onfocusin=()=>link(f,'card');card.onfocusout=clearLinks;host.append(card);
 });
 $('originalFrame')?.contentWindow?.postMessage({type:'labwise:review-marks',findings:r.analysis?.findings||[],reviews:r.reviews},location.origin);
}

async function reveal(id,quote,page){const paragraph=state.report?.paragraphs.find(p=>p.id===id);const query=quote||paragraph?.text;if(!query)return;pendingAnchor={type:'labwise:locate',quote:quote||(!paragraph?.object_only?query:''),paragraph_id:id,word_index:paragraph?.anchor?.paragraph_index,object_only:paragraph?.object_only,page:page||paragraph?.page||null};await showOriginal();sendAnchor();}
function clearLinks(){document.querySelectorAll('.linked').forEach(n=>n.classList.remove('linked'));document.querySelectorAll('.source-p.strength,.source-p.issue').forEach(n=>n.classList.remove('strength','issue'));}
function link(f,origin){clearLinks();$('finding-'+f.id)?.classList.add('linked');document.querySelectorAll('#map [data-finding]').forEach(n=>{if(n.dataset.finding===f.id)n.classList.add('linked');});void reveal(f.paragraph_ids.find(id=>!f.quote||state.report.paragraphs.find(p=>p.id===id)?.text.includes(f.quote))||f.paragraph_ids[0],f.quote);const target=origin==='map'?$('finding-'+f.id):document.querySelector('#map .linked');const container=origin==='map'?$('findings').closest('.scroll'):$('map');if(target&&container){const c=container.getBoundingClientRect(),t=target.getBoundingClientRect();if(t.top<c.top||t.bottom>c.bottom)container.scrollTo({top:container.scrollTop+t.top-c.top-25,behavior:'smooth'});}}
async function save(action){
 if(state.busy||state.saving||state.navigating)throw Error('请等待当前操作完成。');
 for(const input of $('scores').querySelectorAll('input'))if(!input.checkValidity())throw Error('请检查各项评分范围，最多一位小数。');
 state.saving=true;document.querySelectorAll('.workspace .column').forEach(n=>n.inert=true);$('save').disabled=true;$('confirm').disabled=true;
 try{
  const payload=reviewPayload(),latest=await api('reports/'+state.report.id);
  if(latest.status==='analyzing')throw Error('AI 正在生成结果，请稍后保存；当前输入会保留。');
  if(latest.revision!==payload.revision){if(!sameTeacherFields(state.baseReport,latest))throw Error('报告已有其他修改，请先保留当前输入并重新打开，避免覆盖。');payload.revision=latest.revision;}
  const r=await api('reports/'+state.report.id+'/'+action,payload);renderReport(r);
  try{await refresh();renderReviewSequence();}catch{message('评阅已保存，但任务列表刷新失败。可返回工作台后继续。',true);return;}
  if(action==='confirm'){
   try{await continueAssignment(r.assignment.id,true);}catch{message('本份评分已确认，但下一份打开失败。请返回工作台点击“继续批改”。',true);}
  }else message('草稿已保存，下次点击本作业题的“继续批改”即可接着处理。');
 }finally{state.saving=false;document.querySelectorAll('.workspace .column').forEach(n=>n.inert=false);$('save').disabled=false;$('confirm').disabled=false;}
}

function analysisNotice(r){
 if(r.analysis?.mode==='deepseek')return (r.analysis.coverage?.state==='partial'?'AI 辅助分析已返回，部分内容需教师核对':'AI 辅助分析已完成')+' · '+r.analysis.findings.length+' 条候选建议。确认建议后会保存并锁定，评分由教师确认。';
 if(r.status==='queued')return '已自动加入 AI 分析队列，完成后结果会自动显示，无需手动启动。';
 if(r.status==='analyzing')return 'AI 正在后台分析报告，完成后自动显示概览、分论点和候选建议。你可以先阅读原文或返回文件列表。';
 if(r.status==='waiting_key')return '等待 AI 服务连接：请在设置页保存访问密钥，文件会自动继续分析。';
 if(r.status==='failed')return '自动分析暂未完成：'+(r.error||'请检查服务连接')+'。可在工作台文件列表重试。';
 return '文件将自动进行 AI 辅助分析，结果就绪后会显示在这里。';
}
const teacherFields=['filename','student_alias','notes','feedback','scores','reviews','suggestion_edits','teacher_summary','map_edits','teacher_maps','annotations','visual_reviews','assignment','confirmed'];
function sameTeacherFields(a,b){return teacherFields.every(key=>JSON.stringify(a?.[key]??null)===JSON.stringify(b?.[key]??null));}
let polling=false;
async function pollAutomaticResults(){
 if(polling||document.hidden||state.navigating||state.saving||state.uploading||submissionImport.running||!state.bootstrap)return;
 polling=true;try{
  const data=await api('bootstrap');state.bootstrap=data;drawReportList();renderMetrics();renderReviewSequence();
  if(assignmentEditor.id)drawSavedSubmissions(assignmentEditor.id);
  if(state.section==='workspace'&&state.report&&!state.busy){
   const id=state.report.id,latest=await api('reports/'+id);
   if(state.section!=='workspace'||state.report?.id!==id)return;
   if(latest.revision!==state.report.revision||latest.status!==state.report.status){
    if(!state.dirty)renderReport(latest);
    else{$('status').textContent=(latest.confirmed?'已完成':'批改中')+' · '+(statusNames[latest.status]||latest.status);$('workNotice').textContent=analysisNotice(latest)+(latest.analysis?.mode==='deepseek'?' 先保存当前修改，即可展示新结果。':'');}
   }
  }
 }catch{}finally{polling=false;}
}
setInterval(pollAutomaticResults,2500);

function openTeacherSection(name){if(state.busy||state.saving||submissionImport.running){message('当前处理尚未完成，请稍候。');return false;}if(!protectChange())return false;state.dirty=false;page(name);if(name==='settings')loadPreferencesForm();if(name==='standards')renderStandards();if(name==='analytics')renderAnalytics();return true;}
function applyPreferences(){const prefs=state.bootstrap?.settings?.preferences||{};const course=prefs.course_name||'我的课程',term=prefs.term||'个人教师工作区';$('teacherGreeting').textContent='你好，'+(prefs.name||'老师');$('courseName').textContent=course;$('courseTerm').textContent=term;$('dashboardTerm').textContent=term;const avatar=document.querySelector('.avatar');avatar.textContent=(prefs.name||'师').slice(0,1);avatar.setAttribute('aria-label','用户：'+(prefs.name||'老师'));}
function loadPreferencesForm(){const p=state.bootstrap?.settings?.preferences||{};$('teacherName').value=p.name||'老师';$('courseLabel').value=p.course_name||'我的课程';$('termLabel').value=p.term||'';$('readingSize').value=p.font_size||'14';$('readingSpace').value=p.line_height||'1.95';loadArchived().catch(e=>message(e.message,true));renderTeacherActivity();}
function renderTeacherActivity(){const list=$('activityList');if(!list)return;list.replaceChildren();const events=readLocal(storageKeys.activity,[]);if(!events.length)list.append(node('p','muted','暂无操作记录。'));for(const event of events.slice(0,20)){const row=node('div','activity-row');row.append(node('span',null,event.action),node('small',null,new Date(event.time).toLocaleString()));list.append(row);}}
async function loadArchived(){
  let box=$('archivedRecords');if(!box){box=node('article','panel settings-note');box.id='archivedRecords';$('settingsSettings').append(box);}box.replaceChildren(node('h2',null,'已归档记录'));
  const records=await api('archived');if(!records.assignments.length&&!records.reports.length)box.append(node('p','muted','暂无归档记录。'));
  for(const [kind,list] of [['assignments',records.assignments],['reports',records.reports]])for(const item of list){const row=node('div','row');row.append(node('span',null,item.title||item.filename));const restore=node('button',null,'恢复');restore.onclick=safeAction(async()=>{await api(kind+'/'+item.id+'/unarchive',{revision:item.revision});await refresh();await loadArchived();message('已恢复。');});row.append(restore);box.append(row);}
}
document.querySelectorAll('.nav-item').forEach((b,i)=>b.onclick=()=>openTeacherSection(teacherViews[i].name));
$('newAssignmentEntry').onclick=()=>{if(openTeacherSection('assignments')){resetAssignment();$('assignmentTitle').focus();}};
$('assignmentSelect').onchange=assignmentInfo;$('reportSearch').oninput=drawReportList;$('reportFilter').onchange=drawReportList;
$('refresh').onclick=safeAction(async()=>{if(state.busy||submissionImport.running)throw Error('请等待当前处理完成。');await refresh();if(state.report&&state.section==='workspace'&&!state.dirty)renderReport(await api('reports/'+state.report.id));message('记录已刷新。');});
$('upload').onclick=safeAction(()=>createReport(false));
$('back').onclick=safeAction(async()=>{if(openTeacherSection('home'))await refresh();});
$('outlineTab').onclick=()=>{state.map='outline';$('outlineTab').classList.add('active');$('claimsTab').classList.remove('active');renderMap();};
$('claimsTab').onclick=()=>{state.map='claims';$('claimsTab').classList.add('active');$('outlineTab').classList.remove('active');renderMap();};
for(const id of ['notes','feedback','summary'])$(id).oninput=dirty;
$('save').onclick=safeAction(()=>save('save'));$('confirm').onclick=safeAction(()=>save('confirm'));
$('renameReport').onclick=safeAction(async()=>{if(state.busy)throw Error('请等待分析完成。');if(state.dirty)await save('save');const alias=window.prompt('学生姓名或匿名编号（可留空）',state.report.student_alias||'');if(alias===null)return;const name=window.prompt('报告显示名称',state.report.filename);if(name===null)return;renderReport(await api('reports/'+state.report.id+'/metadata',{revision:state.report.revision,filename:name,student_alias:alias}));await refresh();message('报告信息已保存。');});
$('preferencesForm').onsubmit=async e=>{e.preventDefault();try{await api('preferences',{name:$('teacherName').value,course_name:$('courseLabel').value,term:$('termLabel').value,font_size:$('readingSize').value,line_height:$('readingSpace').value});await refresh();recordTeacherAction('更新课程与阅读设置');message('个人偏好已保存。');}catch(error){message(error.message,true);}};
$('settingsForm').onsubmit=async e=>{e.preventDefault();try{const editing=!$('apiKeyEditor').hidden,key=$('apiKey').value;if(editing&&!key)throw Error('请输入访问密钥。');const result=await api('settings',{model:$('model').value,api_key:editing?key:''});await refresh();message(result.has_key?(editing?'连接已保存，刷新或重启服务后仍会保留。':'模型设置已保存。'):'尚未连接，请输入访问密钥。',!result.has_key);}catch(error){message(error.message,true);}};
$('replaceKey').onclick=()=>{$('apiKeyEditor').hidden=false;$('connectActions').hidden=false;$('connectedActions').hidden=true;$('cancelKeyChange').hidden=false;$('apiKey').required=true;$('apiKey').focus();};
$('cancelKeyChange').onclick=()=>renderConnectionSettings(state.bootstrap.settings);
$('clearKey').onclick=safeAction(async()=>{if(!window.confirm('确定删除本机保存的访问密钥吗？删除后 AI 分析将不可用，直到添加新密钥。'))return;await api('settings',{model:$('model').value,clear_key:true});await refresh();$('apiTestResult').textContent='访问密钥已删除。';message('访问密钥已删除。');});
$('testConnection').onclick=safeAction(async()=>{const button=$('testConnection');button.disabled=true;try{await api('connection',{});$('apiTestResult').textContent='连接成功：模型列表接口返回正常。分析接口尚需单独测试。';message('连接正常。');}catch(e){$('apiTestResult').textContent='连接失败：'+e.message;throw e;}finally{button.disabled=false;}});
$('export').onclick=()=>{if(state.busy||state.saving)return message('请等待当前操作完成。');if(state.dirty)return message('存在未保存修改，请先重新确认。',true);$('exportDialog').showModal();};
function download(content,filename,type){const url=URL.createObjectURL(new Blob([content],{type}));const a=node('a');a.href=url;a.download=filename;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
$('printExport').onclick=safeAction(async()=>{const popup=window.open('','_blank');if(!popup)throw Error('浏览器阻止了打印窗口，请允许弹出窗口后重试。');try{const exported=await api('reports/'+state.report.id+'/export-html');popup.document.open();popup.document.write(exported.content);popup.document.close();setTimeout(()=>popup.print(),400);$('exportDialog').close();}catch(e){popup.close();throw e;}});
$('wordExport').onclick=safeAction(async()=>{const exported=await api('reports/'+state.report.id+'/export-docx');const binary=atob(exported.content);const bytes=new Uint8Array(binary.length);for(let i=0;i<binary.length;i++)bytes[i]=binary.charCodeAt(i);download(bytes,exported.filename,exported.content_type);message('Word 反馈文档已生成。');});
$('turnitinExport').onclick=safeAction(async()=>{const exported=await api('reports/'+state.report.id+'/export-turnitin');if(navigator.clipboard?.writeText)await navigator.clipboard.writeText(exported.content);else{const area=node('textarea');area.value=exported.content;area.style.position='fixed';area.style.opacity='0';document.body.append(area);area.select();document.execCommand('copy');area.remove();}$('exportDialog').close();message('Turnitin 人工录入摘要已复制。');});
$('closeExport').onclick=()=>$('exportDialog').close();
$('history').onclick=safeAction(async()=>{if(state.busy||state.saving)throw Error('请等待当前操作完成。');const data=await api('reports/'+state.report.id+'/revisions');$('versions').replaceChildren();if(!data.revisions.length)$('versions').append(node('p','muted','尚无历史版本，保存草稿后自动生成。'));data.revisions.forEach(v=>{const b=node('button',null,'恢复 '+new Date(v.created).toLocaleString());b.onclick=safeAction(async()=>{if(!protectChange())return;const restored=await api('reports/'+state.report.id+'/restore',{revision:state.report.revision,version_id:v.id});renderReport(restored);$('historyDialog').close();message('已恢复为新的草稿版本。');});$('versions').append(b);});$('historyDialog').showModal();});$('closeHistory').onclick=()=>$('historyDialog').close();
$('textExport').onclick=safeAction(async()=>{const result=await api('reports/'+state.report.id+'/export');download(result.content,result.filename,'text/plain;charset=utf-8');message('反馈已导出。');});
window.addEventListener('beforeunload',e=>{if(state.dirty||assignmentEditor.dirty||state.uploading||state.saving||state.busy||submissionImport.running||assignmentEditor.loading){e.preventDefault();e.returnValue='';}});
let navigating=false;
async function route(){
  if(navigating)return;navigating=true;
  try{
    if(state.busy||state.saving||submissionImport.running||!protectChange()){history.replaceState(null,'',state.section==='workspace'&&state.report?'#review='+encodeURIComponent(state.report.id):'#'+state.section);return;}
    const hash=location.hash.slice(1);state.dirty=false;
    if(hash.startsWith('review=')){await openReport(decodeURIComponent(hash.slice(7)));return;}
    const name=teacherViews.some(v=>v.name===hash)?hash:'home';page(name);if(name==='settings')loadPreferencesForm();if(name==='standards')renderStandards();if(name==='analytics')renderAnalytics();
  }catch(e){message(e.message,true);page('reports');}finally{navigating=false;}
}
window.addEventListener('popstate',route);
(async()=>{initTeacherNavigation();initAssignmentEditor();try{await refresh();await route();}catch(e){message('暂时无法连接应用。请确认服务已启动，再点击刷新记录。'+e.message,true);}})();

$('openStandards').onclick=()=>openTeacherSection('standards');
document.querySelector('.assignment-entry').onclick=()=>openTeacherSection('assignments');$('homeNav').onclick=()=>openTeacherSection('home');
$('usageHelp').onclick=()=>$('helpDialog').showModal();$('closeHelp').onclick=()=>$('helpDialog').close();
$('testAnalysis').onclick=safeAction(async()=>{const button=$('testAnalysis');button.disabled=true;$('apiTestResult').textContent='正在发送不含学生资料的接口测试请求…';try{const result=await api('test-analysis',{});$('apiTestResult').textContent='测试成功：'+result.model+' 已返回可解析、证据引用有效的分析结果。';}catch(e){$('apiTestResult').textContent='测试失败：'+e.message;throw e;}finally{button.disabled=false;}});
function closeTeacherNavigation(){document.querySelector('.dashboard-nav').classList.remove('mobile-open');document.body.classList.remove('nav-open');$('teacherNavBackdrop').hidden=true;$('teacherNavToggle').setAttribute('aria-expanded','false');}
function initTeacherNavigation(){const nav=document.querySelector('.dashboard-nav');const toggle=node('button','sidebar-toggle','☰ 导航');toggle.id='teacherNavToggle';toggle.setAttribute('aria-expanded','false');document.querySelector('.top-actions').prepend(toggle);const backdrop=node('button','nav-backdrop');backdrop.id='teacherNavBackdrop';backdrop.hidden=true;backdrop.setAttribute('aria-label','关闭侧边导航');document.body.append(backdrop);backdrop.onclick=closeTeacherNavigation;toggle.onclick=()=>{if(toggle.getAttribute('aria-expanded')==='true'){closeTeacherNavigation();return;}nav.classList.add('mobile-open');document.body.classList.add('nav-open');backdrop.hidden=false;toggle.setAttribute('aria-expanded','true');};document.addEventListener('keydown',e=>{if(e.key==='Escape')closeTeacherNavigation();});}
let originalURL=null,originalGeneration=0,readerReady=false,pendingAnchor=null,currentOriginalSelection=null;
function clearOriginalPreview(){originalGeneration++;readerReady=false;pendingAnchor=null;currentOriginalSelection=null;if(originalURL)URL.revokeObjectURL(originalURL);originalURL=null;$('originalFrame')?.remove();$('originalNotice')?.remove();$('sourceScroll').classList.add('showing-original');}
function sendAnchor(){const frame=$('originalFrame');if(readerReady&&frame&&pendingAnchor){frame.contentWindow.postMessage(pendingAnchor,location.origin);pendingAnchor=null;$('sourceScroll').scrollIntoView?.({block:'center',behavior:'smooth'});}}
async function showOriginal(){
 const reportID=state.report?.id;if(!reportID)return;
 $('sourceScroll').classList.add('showing-original');if($('originalFrame'))return;
 const generation=++originalGeneration;
 let notice=$('originalNotice');if(!notice){notice=node('div','original-preview-notice');notice.id='originalNotice';notice.setAttribute('role','status');$('sourceScroll').prepend(notice);}
 notice.hidden=false;notice.replaceChildren(node('span',null,'正在载入原文件，请稍候…'));
 try{
  const data=await api('reports/'+reportID+'/source');if(generation!==originalGeneration)return;
  let encoded=data.file,conversion=null;const isWord=data.filename.toLowerCase().endsWith('.docx');
  if(isWord){const frame=node('iframe');frame.id='originalFrame';frame.title='Word 原文与批注';frame.dataset.readerMode='word';frame.src='/word-reader.html?report='+encodeURIComponent(reportID);notice.textContent='Word 原文定位视图：点击建议可定位对应段落，原稿保持不变。';$('sourceScroll').append(frame);return;}
  if(isWord){notice.textContent='正在准备 Word 预览…';conversion=await api('reports/'+reportID+'/visual-preview').catch(()=>api('document-preview',{filename:data.filename,file:data.file}));encoded=conversion.file;}
  if(generation!==originalGeneration)return;
  if(conversion?.content_type==='text/html'){
    const frame=node('iframe');frame.id='originalFrame';frame.title='Word 兼容阅读预览';frame.dataset.readerMode='readable';frame.setAttribute('sandbox','');frame.srcdoc=conversion.html;
    notice.replaceChildren(node('span',null,'Word 兼容阅读视图。'+(conversion.warnings||[]).join(' ')+' 此视图暂不提供原页定位和原页批注。'));
    $('sourceScroll').append(frame);return;
  }
  if(generation!==originalGeneration)return;
  const bytes=Uint8Array.from(atob(encoded),c=>c.charCodeAt(0));originalURL=URL.createObjectURL(new Blob([bytes],{type:'application/pdf'}));
  const frame=node('iframe');frame.id='originalFrame';frame.title='原文件分页预览';frame.src='/original-reader.html?v=visual-1&file='+encodeURIComponent(originalURL);
  notice.replaceChildren(node('span',null,isWord?'Word 分页预览；字体或复杂排版可能与 Word 有差异。'+(conversion?.warnings?.length?' '+conversion.warnings.join(' '):''):'正在显示上传的原始 PDF，保留原文件分页和排版。'));
  const open=node('a',null,'独立窗口打开');open.href=originalURL;open.target='_blank';open.rel='noopener';notice.append(open);
  $('sourceScroll').append(frame);
 }catch(e){if(generation!==originalGeneration)return;notice.replaceChildren(node('span',null,'原文件预览暂不可用：'+e.message+' 请重新加载或重新导入原文件。'));const retry=node('button',null,'重新加载原文件');retry.type='button';retry.onclick=()=>void showOriginal();notice.append(retry);}
}
$('showOriginal').onclick=()=>{clearOriginalPreview();void showOriginal();};
window.addEventListener('pagehide',()=>{if(originalURL)URL.revokeObjectURL(originalURL);});

function renderAnnotations(){
 const host=$('originalAnnotations');host.replaceChildren();
 if(!state.report.annotations?.length){host.append(node('p','muted','在原文件中选中文字，点击“添加批注”开始评阅。'));return;}
 state.report.annotations.forEach((a,index)=>{const card=node('article','original-annotation');card.append(node('b',null,a.paragraph_id?'Word 段落 '+a.paragraph_id+' · 原文批注':'第 '+a.page+' 页 · 原文批注'),node('blockquote',null,a.quote));const note=node('textarea');note.rows=3;note.value=a.note;note.setAttribute('aria-label','第 '+a.page+' 页批注');note.oninput=()=>{a.note=note.value;dirty();};const locate=node('button',null,'定位原页');locate.onclick=()=>void reveal(a.paragraph_id,a.quote,a.page);const remove=node('button',null,'移除批注');remove.onclick=()=>{state.report.annotations.splice(index,1);dirty();renderAnnotations();};const accept=node('button',null,'加入学生反馈');accept.onclick=()=>{const text=note.value.trim();if(text&&!$('feedback').value.includes(text)){$('feedback').value+=($('feedback').value?'\n\n':'')+'第 '+a.page+' 页：'+text;dirty();message('批注已加入学生反馈草稿。');}};card.append(note,locate,accept,remove);host.append(card);});
}
window.addEventListener('message',event=>{
 const frame=$('originalFrame');if(event.origin!==location.origin||!frame||event.source!==frame.contentWindow)return;
 const data=event.data;if(!data||typeof data!=='object')return;
 if(data.type==='labwise:selection'&&typeof data.quote==='string'&&Number.isInteger(data.page))currentOriginalSelection={quote:data.quote,page:data.page};
 if(data.type==='labwise:select-finding'){const finding=state.report.analysis?.findings.find(f=>f.id===data.finding_id);if(finding){$('finding-'+finding.id)?.scrollIntoView({block:'center',behavior:'smooth'});link(finding,'map');}return;}
 if(data.type==='labwise:reader-ready'){readerReady=true;sendAnchor();$('originalFrame').contentWindow.postMessage({type:'labwise:review-marks',findings:state.report.analysis?.findings||[],reviews:state.report.reviews},location.origin);}
 if(data.type==='labwise:locate-result'&&typeof data.message==='string')message(data.message,data.found===false);
 if(data.type==='labwise:add-annotation'&&typeof data.quote==='string'&&data.quote.trim()&&data.quote.length<=4000&&Number.isInteger(data.page)&&data.page>0&&data.page<=200){
  if(state.busy||state.saving)return message('请等待当前操作完成后添加批注。',true);
  const note=window.prompt(data.paragraph_id?'为选中的 Word 原段落添加批注：':'为第 '+data.page+' 页选中的原文添加批注：');if(!note?.trim())return;
  state.report.annotations??=[];state.report.annotations.push({id:crypto.randomUUID(),page:data.page,quote:data.quote,note:note.trim().slice(0,4000),...(data.paragraph_id?{paragraph_id:data.paragraph_id}:{})});dirty();renderAnnotations();void reveal(null,data.quote,data.page);message('原文批注已添加，请保存草稿。');
 }
});

function renderWordCoverage(){
 const host=$('wordCoverage');host.replaceChildren();const a=state.report?.analysis;
 if(!a?.coverage){host.append(node('p','muted',state.report?.source_filename?.toLowerCase().endsWith('.docx')?'此历史结果来自旧版正文分析；新提交的 Word 会自动分析正文与图表。':'历史 PDF 记录保留供查阅；新作业仅接收 Word。'));return;}
 const c=a.coverage;host.append(node('b',null,'Word 图表自动检查 · '+c.objects.length+' 个对象'));
 for(const warning of c.warnings||[])host.append(node('p','word-coverage-warning',warning));
 for(const check of a.visual_checks||[]){const object=c.objects.find(o=>o.id===check.object_id);const entry=node('p','muted',check.object_id.replace(/^v/,'图表 ')+' · '+(check.status==='checked'?'已读取':'需核对')+' · '+check.summary);entry.onclick=()=>object&&void reveal(object.paragraph_id);host.append(entry);}
}

function downloadBase64Package(pack){const bytes=Uint8Array.from(atob(pack.content),c=>c.charCodeAt(0));download(bytes,pack.filename,pack.content_type);}
$('reviewPackageExport').onclick=safeAction(async()=>{const pack=await api('reports/'+state.report.id+'/export-reviewed');downloadBase64Package(pack);message('原 Word、批注稿及评分数据已导出。');});
