'use strict';
const $=id=>document.getElementById(id);
const state={bootstrap:null,report:null,map:'outline',dirty:false,busy:false,section:'home'};
const statusNames={parsed:'已解析',analyzing:'分析中',ready:'分析完成',failed:'分析失败'};
function node(tag,cls,content){const n=document.createElement(tag);if(cls)n.className=cls;if(content!==undefined)n.textContent=content;return n;}
let messageTimer;
function message(msg,error=false){$('message').textContent=msg;$('message').classList.toggle('error',error);$('message').hidden=false;clearTimeout(messageTimer);messageTimer=setTimeout(()=>$('message').hidden=true,error?10000:5000);}
async function api(path,body){const res=await fetch('/api/pilot/'+path,{method:body===undefined?'GET':'POST',headers:body===undefined?{}:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)});const data=await res.json();if(!res.ok)throw Error(data.error||'请求失败');return data;}
function protectChange(){if(state.uploading||state.saving||assignmentEditor.loading||assignmentEditor.saving){message('正在保存或读取评分标准，请稍候。');return false;}return !(state.dirty||assignmentEditor.dirty)||window.confirm('还有未保存的修改，确定离开吗？');}
function page(name){
  const names={reports:'reportsPage',workspace:'workspacePage',assignments:'assignmentSettings',settings:'settingsPage'};
  for(const id of Object.values(names))$(id).hidden=id!==names[name];
  state.section=name==='reports'?'home':name;
  document.querySelectorAll('[data-section]').forEach(b=>{b.classList.toggle('active',b.dataset.section===state.section);b.setAttribute('aria-current',b.dataset.section===state.section?'page':'false');});
  const hash=name==='workspace'?'#review='+encodeURIComponent(state.report.id):'#'+state.section;
  if(location.hash!==hash)history.pushState(null,'',hash);
  window.scrollTo(0,0);
}
function dirty(){state.dirty=true;$('draftState').textContent='有未保存修改';$('export').disabled=true;}
function safeAction(fn){return async()=>{try{await fn();}catch(e){message(e.message,true);}};}
async function refresh(){
  state.bootstrap=await api('bootstrap');const data=state.bootstrap;
  const selected=$('assignmentSelect').value;$('assignmentSelect').replaceChildren();
  data.assignments.forEach(a=>{const o=node('option',null,a.title+' · 第 '+a.revision+' 版');o.value=a.id;$('assignmentSelect').append(o);});
  if(data.assignments.some(a=>a.id===selected))$('assignmentSelect').value=selected;
  assignmentInfo();$('upload').disabled=!data.assignments.length;
  $('model').value=data.settings.model;$('keyState').textContent=data.settings.has_key?'已配置访问密钥':'尚未配置访问密钥，可先进行人工评阅';
  renderAssignmentLibrary(data.assignments);drawReportList();renderMetrics();applyPreferences();
}
function drawReportList(){
  const query=$('reportSearch').value.trim().toLowerCase(),filter=$('reportFilter').value;
  const reports=(state.bootstrap?.reports||[]).filter(r=>!r.sample&&(!query||(r.filename+' '+r.assignment_title).toLowerCase().includes(query))&&(filter==='all'||(filter==='confirmed'?r.confirmed:!r.confirmed)));
  $('reportList').replaceChildren();
  if(!reports.length)$('reportList').append(node('p','muted','暂无匹配报告。先创建作业题并导入学生报告。'));
  reports.sort((a,b)=>(b.updated||'').localeCompare(a.updated||'')).forEach(r=>{const row=node('div','report-record');const b=node('button',null,r.filename);b.append(node('small',null,r.assignment_title+' · '+(r.confirmed?'已确认':statusNames[r.status]||r.status)));b.onclick=safeAction(async()=>{if(!state.busy&&protectChange())await openReport(r.id);});row.append(b);const archive=node('button','archive-action','归档');archive.onclick=safeAction(async()=>{if(!window.confirm('将此报告移出任务列表？已保存的内容仍会保留。'))return;const report=await api('reports/'+r.id);await api('reports/'+r.id+'/archive',{revision:report.revision});await refresh();message('报告已归档。');});row.append(archive);$('reportList').append(row);});
}
function renderMetrics(){const reports=state.bootstrap.reports.filter(r=>!r.sample);$('assignmentCount').textContent=state.bootstrap.assignments.length;$('pendingCount').textContent=reports.filter(r=>!r.confirmed).length;$('confirmedCount').textContent=reports.filter(r=>r.confirmed).length;}
function assignmentInfo(){const a=state.bootstrap?.assignments.find(a=>a.id===$('assignmentSelect').value);$('rubricInfo').textContent=a?a.rubric.name+' · '+a.rubric.criteria.length+' 个评分项':'';}
async function createReport(){
  if(state.uploading||!protectChange())return;
  const assignment=state.bootstrap.assignments.find(a=>a.id===$('assignmentSelect').value);
  if(!assignment)throw Error('请先创建并保存作业题和评分标准。');
  const file=$('reportFile').files[0];
  if(!file||!(/\.(docx|pdf)$/i.test(file.name)))throw Error('请选择 DOCX 或 PDF 文件。');
  if(file.size>10*1024*1024)throw Error('文件不能超过 10 MB。');
  state.uploading=true;$('upload').disabled=true;
  try{
    const bytes=new Uint8Array(await file.arrayBuffer());let binary='';
    for(let i=0;i<bytes.length;i+=8192)binary+=String.fromCharCode(...bytes.subarray(i,i+8192));
    const report=await api('reports',{sample:false,assignment_id:assignment.id,assignment_revision:assignment.revision,filename:file.name,file:btoa(binary)});
    state.dirty=false;renderReport(report);page('workspace');$('reportFile').value='';
    try{await refresh();}catch{message('报告已保存，但任务列表刷新失败。',true);}
  }finally{state.uploading=false;$('upload').disabled=false;}
}
async function openReport(id){const r=await api('reports/'+id);renderReport(r);page('workspace');}
function reviewPayload(){const scores={};for(const input of $('scores').querySelectorAll('input'))if(input.value!=='')scores[input.dataset.id]=Number(input.value);return {revision:state.report.revision,notes:$('notes').value,feedback:$('feedback').value,scores,suggestion_edits:state.report.suggestion_edits||{},reviews:state.report.reviews,teacher_summary:$('summary').value,map_edits:state.report.map_edits||{}};}
function total(){let score=0,maximum=0,complete=0;for(const input of $('scores').querySelectorAll('input')){maximum+=Number(input.max);if(input.value!==''){score+=Number(input.value);complete++;}}$('total').textContent=`教师评分：${score.toFixed(1)} / ${maximum} · 已填写 ${complete} 项`;}
function renderReport(r){state.report=r;state.dirty=false;$('filename').textContent=r.filename;$('status').textContent=statusNames[r.status]+(r.confirmed?' · 教师已确认':'');$('snapshot').textContent=r.assignment.rubric.name+' · v'+r.assignment.rubric.version;$('workNotice').textContent=r.error|| (r.sample?'当前为虚构示例报告，可使用示例分析演示完整审核流程。':'已载入保存的报告，可以直接填写评分与反馈。选择 AI 分析时，报告与评分标准将发送给 DeepSeek。');$('notes').value=r.notes;$('feedback').value=r.feedback;$('summary').value=r.teacher_summary??r.analysis?.summary??'';$('source').replaceChildren();r.paragraphs.forEach(p=>{const n=node('div','source-p'+(p.heading?' heading':''));n.id='source-'+p.id;n.append(node('small',null,'第 '+p.id.replace('p','')+' 段'),node('span',null,p.text));$('source').append(n);});$('scores').replaceChildren();r.assignment.rubric.criteria.forEach(c=>{const label=node('label','score-row',c.name+' / '+c.maximum_points);const input=node('input');input.setAttribute('aria-label',c.name+'评分');input.type='number';input.min=0;input.max=c.maximum_points;input.step='0.1';input.dataset.id=c.id;input.value=r.scores[c.id]??'';input.oninput=()=>{dirty();total();};label.append(input);$('scores').append(label);});total();renderMap();renderFindings();applyPreferences();$('export').disabled=!r.confirmed;$('draftState').textContent=r.confirmed?'教师已确认，可导出反馈':'草稿 · 最近保存 '+new Date(r.updated).toLocaleString();$('analyze').disabled=r.status==='analyzing';}
function renderMap(){const r=state.report,field=state.map;let entries=r.analysis?.[field];if(!entries?.length&&field==='outline'){entries=r.paragraphs.filter(p=>p.heading).map(p=>({title:p.text,paragraph_ids:[p.id]}));if(!entries.length)entries=[{title:'正文',paragraph_ids:[r.paragraphs[0].id]}];}$('map').replaceChildren();if(!entries?.length)$('map').append(node('p','muted',field==='claims'?'尚无论点分析结果。':'未识别到标题，可直接浏览原文。'));entries?.forEach(entry=>{const box=node('div','map-node');const key=field+':'+entry.paragraph_ids.join(',');const title=node('input','map-title');title.value=r.map_edits?.[key]??entry.title;title.maxLength=500;title.setAttribute('aria-label','编辑导航标题');title.oninput=()=>{r.map_edits??={};r.map_edits[key]=title.value;dirty();};const locate=node('button',null,'定位原文');locate.onclick=()=>reveal(entry.paragraph_ids[0]);box.append(title,locate);const start=r.paragraphs.findIndex(p=>p.id===entry.paragraph_ids[0]);const next=field==='outline'?r.paragraphs.findIndex((p,i)=>i>start&&p.heading):-1;const related=(r.analysis?.findings||[]).filter(f=>f.paragraph_ids.some(id=>{const i=r.paragraphs.findIndex(p=>p.id===id);return field==='outline'?i>=start&&(next<0||i<next):entry.paragraph_ids.includes(id);}));related.forEach(f=>{const b=node('button','bubble '+f.kind);b.dataset.finding=f.id;b.append(node('span','num',f.id),node('span',null,(f.kind==='strength'?'优点 · ':'问题 · ')+f.title));b.onmouseenter=()=>link(f,'map');b.onmouseleave=clearLinks;b.onfocus=()=>link(f,'map');b.onblur=clearLinks;b.onclick=()=>link(f,'map');box.append(b);});$('map').append(box);});}
function renderFindings(){const r=state.report;$('findings').replaceChildren();if(!r.analysis?.findings.length)$('findings').append(node('p','muted','暂无候选建议，可直接填写教师评分与反馈，或连接 AI 后生成建议。'));r.analysis?.findings.forEach(f=>{const card=node('article','finding '+f.kind);card.id='finding-'+f.id;card.tabIndex=0;const heading=node('div','row');heading.append(node('span','num',f.id),node('b',null,f.title));card.append(heading,node('small','muted','评分项目：'+(r.assignment.rubric.criteria.find(c=>c.id===f.criterion_id)?.name||f.criterion_id)),node('p',null,f.rationale),node('blockquote',null,f.quote));const draft=node('textarea');draft.rows=3;draft.setAttribute('aria-label',f.title+'反馈草稿');draft.value=r.suggestion_edits?.[f.id]??f.feedback;draft.oninput=()=>{state.report.suggestion_edits??={};state.report.suggestion_edits[f.id]=draft.value;state.report.reviews[f.id]='edited';status.textContent='审核状态：已编辑（请将内容加入最终反馈）';dirty();};card.append(draft);const status=node('p','muted','审核状态：'+({accepted:'已采纳',rejected:'已拒绝',edited:'已编辑',pending:'待复核'}[r.reviews[f.id]||'pending']));card.append(status);const buttons=node('div','row');for(const [key,label] of [['accepted','采纳并加入反馈'],['rejected','拒绝'],['pending','待复核']]){const b=node('button',null,label);b.onclick=()=>{r.reviews[f.id]=key;status.textContent='审核状态：'+label;if(key==='accepted'){const text=draft.value.trim();if(text&&!$('feedback').value.includes(text))$('feedback').value+=($('feedback').value?'\n\n':'')+text;}dirty();};buttons.append(b);}card.append(buttons);card.onmouseenter=()=>link(f,'card');card.onmouseleave=clearLinks;card.onfocusin=()=>link(f,'card');card.onfocusout=clearLinks;$('findings').append(card);});}
function reveal(id){const p=$('source-'+id);if(!p)return;const container=$('sourceScroll');container.scrollTo({top:Math.max(0,container.scrollTop+p.getBoundingClientRect().top-container.getBoundingClientRect().top-container.clientHeight/3),behavior:'smooth'});}
function clearLinks(){document.querySelectorAll('.linked').forEach(n=>n.classList.remove('linked'));document.querySelectorAll('.source-p.strength,.source-p.issue').forEach(n=>n.classList.remove('strength','issue'));}
function link(f,origin){clearLinks();for(const id of f.paragraph_ids)$('source-'+id)?.classList.add(f.kind);$('finding-'+f.id)?.classList.add('linked');document.querySelectorAll('#map [data-finding]').forEach(n=>{if(n.dataset.finding===f.id)n.classList.add('linked');});reveal(f.paragraph_ids[0]);const target=origin==='map'?$('finding-'+f.id):document.querySelector('#map .linked');const container=origin==='map'?$('findings').closest('.scroll'):$('map');if(target&&container){const c=container.getBoundingClientRect(),t=target.getBoundingClientRect();if(t.top<c.top||t.bottom>c.bottom)container.scrollTo({top:container.scrollTop+t.top-c.top-25,behavior:'smooth'});}}
async function save(action){
 if(state.busy||state.saving)throw Error('请等待当前操作完成。');
 for(const input of $('scores').querySelectorAll('input'))if(!input.checkValidity())throw Error('请检查各项评分范围，最多一位小数。');
 state.saving=true;document.querySelectorAll('.workspace .column').forEach(n=>n.inert=true);$('save').disabled=true;$('confirm').disabled=true;
 try{const r=await api('reports/'+state.report.id+'/'+action,reviewPayload());renderReport(r);try{await refresh();}catch{message('评阅已保存，但任务列表刷新失败。',true);return;}message(action==='confirm'?'教师确认已保存，现在可以导出反馈。':'草稿已保存，可随时继续批改。');}
 finally{state.saving=false;document.querySelectorAll('.workspace .column').forEach(n=>n.inert=false);$('save').disabled=false;$('confirm').disabled=false;}
}
async function analyzeReport(){if(state.busy||state.saving)return;if(state.report.analysis&&!window.confirm('重新分析会产生新的建议。当前教师评分和反馈将保留，旧建议的审核状态会进入历史版本。继续吗？'))return;if(state.dirty){await save('save');}const mode=$('mode').value;if(mode==='deepseek'&&!window.confirm('将向 DeepSeek 发送当前报告正文、作业要求和评分细则。请确认已获得使用授权，继续分析？'))return;state.busy=true;document.querySelectorAll('.workspace .column').forEach(n=>n.inert=true);$('analyze').disabled=true;$('save').disabled=true;$('confirm').disabled=true;$('workNotice').textContent='分析中，请等待。请不要关闭服务或重复提交。';try{const r=await api('reports/'+state.report.id+'/analyze',{revision:state.report.revision,mode});renderReport(r);if(r.error)throw Error(r.error);message('分析完成，请逐项审核。');}finally{state.busy=false;document.querySelectorAll('.workspace .column').forEach(n=>n.inert=false);$('analyze').disabled=false;$('save').disabled=false;$('confirm').disabled=false;}}

function recordTeacherAction(action){if(state.bootstrap){drawReportList();renderMetrics();}}
function openTeacherSection(name){if(state.busy||state.saving||submissionImport.running){message('当前处理尚未完成，请稍候。');return false;}if(!protectChange())return false;state.dirty=false;page(name==='home'?'reports':name);if(name==='settings')loadPreferencesForm();return true;}
function applyPreferences(){const prefs=state.bootstrap?.settings?.preferences||{};$('teacherGreeting').textContent=(prefs.name||'教师')+'的工作区';const source=$('source');source.style.fontSize=(prefs.font_size||'14')+'px';source.style.lineHeight=prefs.line_height||'1.95';}
function loadPreferencesForm(){const p=state.bootstrap?.settings?.preferences||{};$('teacherName').value=p.name||'老师';$('readingSize').value=p.font_size||'14';$('readingSpace').value=p.line_height||'1.95';loadArchived().catch(e=>message(e.message,true));}
async function loadArchived(){
  let box=$('archivedRecords');if(!box){box=node('article','panel settings-note');box.id='archivedRecords';$('settingsPage').append(box);}box.replaceChildren(node('h2',null,'已归档记录'));
  const records=await api('archived');if(!records.assignments.length&&!records.reports.length)box.append(node('p','muted','暂无归档记录。'));
  for(const [kind,list] of [['assignments',records.assignments],['reports',records.reports]])for(const item of list){const row=node('div','row');row.append(node('span',null,item.title||item.filename));const restore=node('button',null,'恢复');restore.onclick=safeAction(async()=>{await api(kind+'/'+item.id+'/unarchive',{revision:item.revision});await refresh();await loadArchived();message('已恢复。');});row.append(restore);box.append(row);}
}
document.querySelectorAll('[data-section]').forEach(b=>b.onclick=()=>openTeacherSection(b.dataset.section));
$('newAssignmentEntry').onclick=()=>{if(openTeacherSection('assignments')){resetAssignment();$('assignmentTitle').focus();}};
$('assignmentSelect').onchange=assignmentInfo;$('reportSearch').oninput=drawReportList;$('reportFilter').onchange=drawReportList;
$('refresh').onclick=safeAction(async()=>{if(state.busy||submissionImport.running)throw Error('请等待当前处理完成。');await refresh();if(state.report&&state.section==='workspace'&&!state.dirty)renderReport(await api('reports/'+state.report.id));message('记录已刷新。');});
$('upload').onclick=safeAction(()=>createReport(false));
$('back').onclick=safeAction(async()=>{if(openTeacherSection('home'))await refresh();});
$('outlineTab').onclick=()=>{state.map='outline';$('outlineTab').classList.add('active');$('claimsTab').classList.remove('active');renderMap();};
$('claimsTab').onclick=()=>{state.map='claims';$('claimsTab').classList.add('active');$('outlineTab').classList.remove('active');renderMap();};
for(const id of ['notes','feedback','summary'])$(id).oninput=dirty;
$('save').onclick=safeAction(()=>save('save'));$('confirm').onclick=safeAction(()=>save('confirm'));$('analyze').onclick=safeAction(analyzeReport);
$('renameReport').onclick=safeAction(async()=>{if(state.busy)throw Error('请等待分析完成。');if(state.dirty)await save('save');const alias=window.prompt('学生姓名或匿名编号（可留空）',state.report.student_alias||'');if(alias===null)return;const name=window.prompt('报告显示名称',state.report.filename);if(name===null)return;renderReport(await api('reports/'+state.report.id+'/metadata',{revision:state.report.revision,filename:name,student_alias:alias}));await refresh();message('报告信息已保存。');});
$('preferencesForm').onsubmit=async e=>{e.preventDefault();try{await api('preferences',{name:$('teacherName').value,font_size:$('readingSize').value,line_height:$('readingSpace').value});await refresh();message('个人偏好已保存。');}catch(error){message(error.message,true);}};
$('settingsForm').onsubmit=async e=>{e.preventDefault();try{await api('settings',{model:$('model').value,api_key:$('apiKey').value});$('apiKey').value='';await refresh();message('连接设置已保存。');}catch(error){message(error.message,true);}};
$('clearKey').onclick=safeAction(async()=>{await api('settings',{model:$('model').value,clear_key:true});await refresh();message('访问密钥已清除。');});
$('testConnection').onclick=safeAction(async()=>{const button=$('testConnection');button.disabled=true;try{await api('connection',{});message('连接正常，可以进行 AI 辅助分析。');}finally{button.disabled=false;}});
function download(content,filename,type){const url=URL.createObjectURL(new Blob([content],{type}));const a=node('a');a.href=url;a.download=filename;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);}
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
    page(hash==='assignments'?'assignments':hash==='settings'?'settings':'reports');if(hash==='settings')loadPreferencesForm();
  }catch(e){message(e.message,true);page('reports');}finally{navigating=false;}
}
window.addEventListener('popstate',route);
(async()=>{initAssignmentEditor();try{await refresh();await route();}catch(e){message('暂时无法连接应用。请确认服务已启动，再点击刷新记录。'+e.message,true);}})();
