'use strict';
// Screens are built around teacher actions. Entity details belong in docs, not the UI.
const teacherModules={standards:[],selectedStandard:null,defaultStandard:null};
const storageKeys={preferences:'labwise.teacher.preferences',activity:'labwise.teacher.activity'};
function readLocal(key,fallback){try{return JSON.parse(localStorage.getItem(key))??fallback;}catch{return fallback;}}
function writeLocal(key,value){try{localStorage.setItem(key,JSON.stringify(value));return true;}catch{message('此浏览器无法保存设置，请检查存储权限。');return false;}}
function recordTeacherAction(action){const events=readLocal(storageKeys.activity,[]);events.unshift({action,time:new Date().toISOString()});writeLocal(storageKeys.activity,events.slice(0,100));if($('activityList'))renderTeacherActivity();}
function moduleHeading(kicker,title,description,badge){const header=node('div','module-heading');const copy=node('div');copy.append(node('small','module-kicker',kicker),node('h1',null,title),node('p',null,description));header.append(copy);if(badge)header.append(node('span','module-badge',badge));return header;}
function moduleButton(label,fn,primary=false){const b=node('button',primary?'module-button primary':'module-button',label);b.type='button';b.onclick=fn;return b;}
function moduleMetric(value,label,description){const metric=node('div','module-metric');metric.append(node('strong',null,value),node('span',null,label));if(description)metric.append(node('small',null,description));return metric;}
function moduleNotice(text){return node('p','module-notice',text);}
async function renderStandards(){
  const page=$('standardsSettings');page.replaceChildren(moduleHeading('03 · GRADING STANDARDS','评分标准','查看每份作业的评分项目，复用已有标准，保持评阅口径一致。'));
  const toolbar=node('div','module-toolbar');toolbar.append(node('span','module-help','已保存作业的标准与参考模板分开展示。'),moduleButton('新建评分标准',()=>{if(!openTeacherSection('assignments'))return;if(protectAssignment()){resetAssignment();$('rubricSource').focus();}},true));page.append(toolbar);
  const layout=node('div','module-two-column');const library=node('section','module-panel');library.append(node('h2',null,'可用评分标准'));const list=node('div','standards-list');list.id='standardsList';library.append(list);const detail=node('article','module-panel');detail.id='standardDetail';layout.append(library,detail);page.append(layout);
  try{await refresh();
    teacherModules.standards=state.bootstrap.assignments.map(a=>({key:a.id,name:a.rubric.name,assignment:a.title,criteria:a.rubric.criteria,version:a.rubric.version,record:a,reference:false}));
    for(const s of teacherModules.standards){const b=node('button','standard-item');b.dataset.standard=s.key;b.append(node('b',null,s.name),node('small',null,s.assignment),node('span',null,`${s.criteria.length} 个项目 · 合计 ${s.criteria.reduce((n,c)=>n+(c.maximum_points??c.weight),0)} 分`));b.onclick=()=>showStandard(s.key);list.append(b);}
    const selected=teacherModules.standards.find(s=>s.key===teacherModules.selectedStandard)||teacherModules.standards[0];if(selected)showStandard(selected.key);else{list.append(node('p','module-help','尚未保存评分标准，请先创建作业题。'));detail.append(node('p','module-help','保存后可在此查看、修改和复用。'));}
  }catch(e){list.replaceChildren(node('p','module-help','暂时无法读取评分标准。'));detail.append(moduleButton('重新加载',renderStandards));message(e.message);}
}
function showStandard(key){
  const s=teacherModules.standards.find(s=>s.key===key);if(!s)return;teacherModules.selectedStandard=key;
  document.querySelectorAll('.standard-item').forEach(b=>b.classList.toggle('selected',b.dataset.standard===key));
  const detail=$('standardDetail');detail.replaceChildren();detail.append(node('span','module-badge',s.reference?'参考模板':'作业评分标准'),node('h2',null,s.name),node('p','module-help',s.assignment));
  for(const [index,c] of s.criteria.entries()){const item=node('div','standard-criterion');const head=node('div');head.append(node('span','criterion-index',String(index+1).padStart(2,'0')),node('b',null,c.name),node('span','standard-points',(c.maximum_points??c.weight)+' 分'));item.append(head,node('p',null,c.descriptor||'请在使用前补充适合本课程的等级描述和判断依据。'));detail.append(item);}
  const actions=node('div','module-actions');if(!s.reference)actions.append(moduleButton('修改这份作业的标准',()=>{if(openTeacherSection('assignments'))loadAssignment(s.record);}));actions.append(moduleButton('复用到新作业',()=>{if(!openTeacherSection('assignments')||!protectAssignment())return;resetAssignment();$('rubricSource').value=s.criteria.map(c=>`${c.name}（${c.maximum_points??c.weight}分）\n${c.descriptor||''}`).join('\n\n');assignmentEdited();inspectRubric().catch(e=>message(e.message));$('assignmentTitle').focus();},true));detail.append(actions,moduleNotice('修改标准后，已经开始评阅的报告仍按当时的标准保留；复用会建立新作业。'));
}
async function renderAnalytics(){
  const page=$('analyticsSettings');page.replaceChildren(moduleHeading('04 · REVIEW INSIGHTS','数据分析','查看实际导入记录的处理进度，明确下一步需要处理的报告。','当前设备记录'));
  page.append(moduleNotice('统计来自本机保存的报告；分析完成与教师确认分别记录。'));
  const filters=node('div','module-toolbar');const label=node('label','module-filter','作业范围');const select=node('select');select.id='analyticsAssignment';select.setAttribute('aria-label','统计作业范围');label.append(select);filters.append(label,moduleButton('刷新统计',renderAnalytics));page.append(filters);const body=node('div');body.id='analyticsBody';page.append(body);
  try{await refresh();const all=node('option',null,'全部作业');all.value='';select.append(all);state.bootstrap.assignments.forEach(a=>{const option=node('option',null,a.title);option.value=a.id;select.append(option);});select.onchange=()=>drawAnalytics(select.value);drawAnalytics('');}catch(e){body.append(node('p','module-help','暂时无法读取报告记录。'),moduleButton('重试',renderAnalytics));message(e.message);}
}
function drawAnalytics(assignment){
  const reports=state.bootstrap.reports.filter(r=>!r.sample&&(!assignment||r.assignment_id===assignment));const body=$('analyticsBody');body.replaceChildren();const counts={ready:0,parsed:0,queued:0,waiting_key:0,analyzing:0,failed:0};reports.forEach(r=>counts[r.status]=(counts[r.status]||0)+1);const metrics=node('div','module-metrics');metrics.append(moduleMetric(String(reports.length),'已导入报告'),moduleMetric(String(counts.ready),'分析完成'),moduleMetric(String(counts.parsed+counts.queued+counts.waiting_key),'等待分析'),moduleMetric(String(counts.failed),'需要处理'));body.append(metrics);
  if(!reports.length){const empty=node('div','module-empty');empty.append(node('h2',null,'还没有可统计的报告'),node('p',null,'导入报告后，这里会显示处理进度。'),moduleButton('返回工作台',()=>openTeacherSection('home')));body.append(empty);return;}
  const panel=node('section','module-panel');panel.append(node('h2',null,'报告处理进度'));for(const [key,label] of [['queued','AI 排队中'],['waiting_key','等待 AI 连接'],['parsed','等待分析'],['analyzing','正在分析'],['ready','分析完成'],['failed','需重新处理']]){const row=node('div','insight-bar-row');const track=node('div','insight-track');const fill=node('span');fill.style.width=(counts[key]/reports.length*100)+'%';fill.className=key==='failed'?'attention':'';track.append(fill);row.append(node('span',null,label),track,node('b',null,String(counts[key])));panel.append(row);}panel.append(node('small','module-help','统计口径：按每份报告当前处理状态计数；分析完成不代表教师已确认分数。'));body.append(panel);
  const recent=node('section','module-panel');recent.append(node('h2',null,'最近保存的报告'));for(const r of reports.slice().sort((a,b)=>b.updated.localeCompare(a.updated)).slice(0,10)){const row=node('div','module-record');row.append(node('b',null,r.filename),node('span',null,({ready:'分析完成',parsed:'等待分析',analyzing:'正在分析',failed:'需要处理'})[r.status]||r.status),node('small',null,new Date(r.updated).toLocaleString()));recent.append(row);}body.append(recent);
}
