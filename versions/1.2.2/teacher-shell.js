// One product shell for the six teacher-facing modules.
const $=id=>document.getElementById(id);
const state={bootstrap:null};
function node(tag,cls,content){const el=document.createElement(tag);if(cls)el.className=cls;if(content!==undefined)el.textContent=content;return el;}
function message(msg){showToast(msg);}
function safeAction(fn){return async()=>{try{await fn();}catch(e){showToast(e.message);}};}
async function api(path,body){const response=await fetch('/api/pilot/'+path,{method:body===undefined?'GET':'POST',headers:body===undefined?{}:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)});const data=await response.json();if(!response.ok)throw Error(data.error||'暂时无法保存，请稍后重试。');return data;}
async function refresh(){state.bootstrap=await api('bootstrap');renderAssignmentLibrary(state.bootstrap.assignments);}
function assignmentInfo(){}
const teacherViews=[
  {name:'home',id:'dashboardHome',label:'工作台'},
  {name:'assignments',id:'assignmentSettings',label:'课程与作业'},
  {name:'standards',id:'standardsSettings',label:'评分标准'},
  {name:'calibration',id:'calibrationSettings',label:'团队与校准'},
  {name:'analytics',id:'analyticsSettings',label:'数据分析'},
  {name:'settings',id:'settingsSettings',label:'设置与审计'}
];
let dashboardSection='home';
function openTeacherSection(name,{fromHistory=false}={}){
  if(!teacherViews.some(v=>v.name===name))name='home';
  if(dashboardSection==='assignments'&&name!=='assignments'&&!protectAssignment())return false;
  if(dashboardSection==='calibration'&&name!=='calibration'&&teacherModules.calibrationDirty&&!window.confirm('校准笔记尚未保存，确定离开吗？'))return false;
  if(dashboardSection==='calibration'&&name!=='calibration')teacherModules.calibrationDirty=false;
  if(dashboardSection==='calibration'&&name==='calibration'&&teacherModules.calibrationDirty){closeTeacherNavigation();return true;}
  $('entryPage').classList.remove('hidden');$('workspacePage').classList.add('hidden');$('homeNav').classList.add('hidden');$('workspaceStatus').classList.add('hidden');
  dashboardSection=name;teacherViews.forEach(v=>$(v.id).hidden=v.name!==name);
  document.querySelectorAll('.nav-item').forEach((b,i)=>{const active=teacherViews[i].name===name;b.classList.toggle('active',active);if(active)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current');});
  if(name==='assignments')refresh().catch(()=>{$('assignmentList').textContent='暂时无法读取已保存作业，请稍后重试。';});
  if(name==='standards')renderStandards();if(name==='calibration')renderCalibration();if(name==='analytics')renderAnalytics();if(name==='settings')renderTeacherPreferences();
  document.querySelector('.assignment-entry').textContent=name==='home'?'作业与评分细则':'返回工作台';
  const target=name==='home'?'#':'#'+name;if(location.hash!==target){history[fromHistory?'replaceState':'pushState'](null,'',target);}
  closeTeacherNavigation();window.scrollTo(0,0);return true;
}
function closeTeacherNavigation(){document.querySelector('.dashboard-nav').classList.remove('mobile-open');document.body.classList.remove('nav-open');$('teacherNavBackdrop').hidden=true;$('teacherNavToggle').setAttribute('aria-expanded','false');}
function initTeacherNavigation(){
  const nav=document.querySelector('.dashboard-nav');nav.id='teacherNavigation';
  const toggle=node('button','sidebar-toggle','☰ 导航');toggle.id='teacherNavToggle';toggle.setAttribute('aria-label','打开侧边导航');toggle.setAttribute('aria-controls',nav.id);toggle.setAttribute('aria-expanded','false');document.querySelector('.top-actions').prepend(toggle);
  const backdrop=node('button','nav-backdrop');backdrop.id='teacherNavBackdrop';backdrop.hidden=true;backdrop.setAttribute('aria-label','关闭侧边导航');document.body.append(backdrop);backdrop.onclick=closeTeacherNavigation;
  toggle.onclick=()=>{const opened=toggle.getAttribute('aria-expanded')==='true';if(opened){closeTeacherNavigation();return;}nav.classList.add('mobile-open');document.body.classList.add('nav-open');backdrop.hidden=false;toggle.setAttribute('aria-expanded','true');nav.querySelector('.nav-item.active')?.focus();};
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&toggle.getAttribute('aria-expanded')==='true'){closeTeacherNavigation();toggle.focus();}});
  document.querySelectorAll('.nav-item').forEach((b,i)=>{b.setAttribute('aria-label',String(i+1).padStart(2,'0')+' '+teacherViews[i].label);b.title=teacherViews[i].label;b.onclick=()=>openTeacherSection(teacherViews[i].name);});
}
setupTeacherModules();initAssignmentEditor();initTeacherNavigation();
document.querySelector('.assignment-entry').onclick=()=>openTeacherSection(dashboardSection==='home'?'assignments':'home');
$('homeNav').onclick=()=>openTeacherSection('home');
window.addEventListener('beforeunload',e=>{if(assignmentEditor.dirty||teacherModules.calibrationDirty){e.preventDefault();e.returnValue='';}});
window.addEventListener('popstate',()=>{if(location.hash==='#workspace'){showPage('workspace');return;}openTeacherSection(location.hash.slice(1)||'home',{fromHistory:true});});
if(location.hash!=='#workspace')openTeacherSection(location.hash.slice(1)||'home',{fromHistory:true});
