// The teacher dashboard is the single application shell.
const $=id=>document.getElementById(id);
const state={bootstrap:null};
function node(tag,cls,content){const el=document.createElement(tag);if(cls)el.className=cls;if(content!==undefined)el.textContent=content;return el;}
function message(msg){showToast(msg);}
function safeAction(fn){return async()=>{try{await fn();}catch(e){showToast(e.message);}};}
async function api(path,body){const response=await fetch('/api/pilot/'+path,{method:body===undefined?'GET':'POST',headers:body===undefined?{}:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)});const data=await response.json();if(!response.ok)throw Error(data.error||'暂时无法保存，请稍后重试。');return data;}
async function refresh(){state.bootstrap=await api('bootstrap');renderAssignmentLibrary(state.bootstrap.assignments);}
function assignmentInfo(){}
let dashboardSection='home';
function openTeacherSection(name){
  if(dashboardSection==='assignments'&&name!=='assignments'&&!protectAssignment())return;
  showPage('entry');dashboardSection=name;
  $('dashboardHome').hidden=name!=='home';$('assignmentSettings').hidden=name!=='assignments';
  document.querySelectorAll('.nav-item').forEach((b,i)=>b.classList.toggle('active',name==='home'?i===0:i===1));
  if(name==='assignments')refresh().catch(()=>{$('assignmentList').textContent='暂时无法读取已保存作业，请稍后重试。';});
  document.querySelector('.assignment-entry').textContent=name==='assignments'?'返回工作台':'作业与评分细则';
  history.replaceState(null,'',name==='assignments'?'#assignments':'#');
}
initAssignmentEditor();
document.querySelectorAll('.nav-item').forEach((b,i)=>{if(i===0)b.onclick=()=>openTeacherSection('home');else if(i===1||i===2)b.onclick=()=>openTeacherSection('assignments');else b.onclick=()=>showToast('此功能尚未开放。');});
document.querySelector('.assignment-entry').onclick=()=>openTeacherSection(dashboardSection==='assignments'?'home':'assignments');
$('homeNav').onclick=()=>openTeacherSection('home');
window.addEventListener('beforeunload',e=>{if(assignmentEditor.dirty){e.preventDefault();e.returnValue='';}});
if(location.hash==='#assignments')openTeacherSection('assignments');
