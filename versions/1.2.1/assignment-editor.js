'use strict';
const assignmentEditor={id:null,revision:null,dirty:false,ready:false,sequence:0,timer:null,filename:'',loading:false};
function assignmentEdited(){assignmentEditor.dirty=true;$('assignmentSaveState').textContent='有未保存修改';}
function protectAssignment(){if(assignmentEditor.loading||assignmentEditor.saving){message('正在读取或保存评分标准，请稍候。');return false;}if(submissionImport.running){message('正在导入，请等待本批文件处理完成。');return false;}return !assignmentEditor.dirty||window.confirm('这份作业还有未保存的修改，确定切换吗？');}
function rubricAsText(rubric){return rubric.source_text||rubric.criteria.map(c=>`${c.name}（${c.maximum_points??c.weight}分）\n${c.descriptor||''}`).join('\n\n');}
function renderAssignmentLibrary(assignments){
  const list=$('assignmentList');list.replaceChildren();
  if(!assignments.length)list.append(node('p','muted','还没有保存作业。从左侧添加第一份吧。'));
  assignments.forEach(a=>{const button=node('button','assignment-item'+(assignmentEditor.id===a.id?' selected':''));button.type='button';const icon=node('span','assignment-icon','▤');const detail=node('span','assignment-detail');detail.append(node('b',null,a.title),node('small',null,`${a.assignment_type||'实验报告'} · ${a.rubric.criteria.length} 个评分项目 · 总分 ${a.rubric.criteria.reduce((n,c)=>n+(c.maximum_points??c.weight),0)}`));button.append(icon,detail,node('span','assignment-arrow','查看 / 修改 →'));button.onclick=()=>{if(protectAssignment())loadAssignment(a);};list.append(button);});
}
function resetAssignment(){clearTimeout(assignmentEditor.timer);assignmentEditor.sequence++;Object.assign(assignmentEditor,{id:null,revision:null,dirty:false,ready:false,filename:'',originalSource:''});$('assignmentForm').reset();$('submissionPanel').hidden=true;clearSubmissionQueue();$('editorTitle').textContent='新建作业';$('assignmentSaveState').textContent='尚未保存';$('saveAssignment').textContent='保存作业';$('rubricPreviewPanel').hidden=true;$('importStatus').textContent='保留每个评分项目的名称、分值和说明，便于准确整理。';$('importStatus').classList.remove('needs-check');$('importFilename').textContent='也可直接粘贴文字';renderAssignmentLibrary(state.bootstrap?.assignments||[]);inspectRubric().catch(e=>message(e.message,true));}
function loadAssignment(a){clearTimeout(assignmentEditor.timer);assignmentEditor.sequence++;Object.assign(assignmentEditor,{id:a.id,revision:a.revision||1,dirty:false,filename:'',originalSource:a.rubric.original_source_text||a.rubric.source_text||''});$('assignmentTitle').value=a.title;$('instructions').value=a.instructions;$('assignmentType').value=a.assignment_type||'实验报告';$('externalTask').value=a.external_task||'';$('rubricSource').value=rubricAsText(a.rubric);$('editorTitle').textContent='编辑作业';$('assignmentSaveState').textContent='已保存';$('saveAssignment').textContent='保存修改';$('importFilename').textContent='已保存的评分细则';renderAssignmentLibrary(state.bootstrap.assignments);renderSubmissionPanel(a);inspectRubric().catch(e=>message(e.message,true));}
function showRubricPreview(parsed){
  $('rubricPreviewPanel').hidden=false;$('previewTotal').textContent=parsed.criteria.length?`合计 ${parsed.total} 分`:'';$('rubricPreview').replaceChildren();
  parsed.criteria.forEach((criterion,index)=>{
    const item=node('section','criterion-preview');const nameLabel=node('label',null,'评分项目 '+(index+1));const name=node('input');name.value=criterion.name;name.maxLength=200;nameLabel.append(name);
    const scoreLabel=node('label',null,'满分');const score=node('input');score.type='number';score.min='.01';score.max='10000';score.step='any';score.value=criterion.maximum_points;scoreLabel.append(score);
    const descLabel=node('label',null,'要求与等级说明');const description=node('textarea');description.rows=3;description.maxLength=4000;description.value=criterion.descriptor||'';descLabel.append(description);
    const update=()=>{if(!name.value.trim()||!score.value||!score.checkValidity()){message('评分项目需要名称和有效满分。',true);return;}criterion.name=name.value.trim();criterion.maximum_points=Number(score.value);criterion.descriptor=description.value;writeCriteria(parsed.criteria);};
    name.onchange=update;score.onchange=update;description.onchange=update;
    const remove=node('button',null,'移除此项');remove.type='button';remove.onclick=()=>{parsed.criteria.splice(index,1);writeCriteria(parsed.criteria);};
    item.append(nameLabel,scoreLabel,descLabel,remove);$('rubricPreview').append(item);
  });
  const original=node('details','original-rubric');original.append(node('summary',null,'查看保留的导入原文'));original.append(node('pre',null,assignmentEditor.originalSource||parsed.source_text));$('rubricPreview').append(original);
  const add=node('button',null,'＋ 添加评分项目');add.type='button';add.onclick=()=>{const name=window.prompt('新评分项目名称');if(!name?.trim())return;const raw=window.prompt('这一项的满分（请按你的评分标准填写）');if(raw===null)return;const points=Number(raw);if(!Number.isFinite(points)||points<=0||points>10000){message('请输入大于 0 且不超过 10000 的分值。',true);return;}writeCriteria([...parsed.criteria,{name:name.trim(),maximum_points:points,descriptor:''}]);};$('rubricPreview').append(add);
  if(!parsed.criteria.length)$('rubricPreview').prepend(node('p','muted','请在左侧补充项目名称和分值，也可添加评分项目。'));
  $('importStatus').textContent=parsed.ready?`已整理出 ${parsed.criteria.length} 个评分项目，请核对后保存。`:parsed.messages.join(' ');$('importStatus').classList.toggle('needs-check',!parsed.ready&&!!parsed.source_text);assignmentEditor.ready=parsed.ready;
}
function writeCriteria(criteria){
  const previous=$('rubricSource').value;
  if(!assignmentEditor.originalSource)assignmentEditor.originalSource=previous;
  $('rubricSource').value=criteria.map(c=>`${c.name}（${c.maximum_points}分）\n${c.descriptor||''}`).join('\n\n');
  if(previous!==$('rubricSource').value)assignmentEdited();inspectRubric().catch(e=>message(e.message,true));
}
async function inspectRubric(){const sequence=++assignmentEditor.sequence;const source=$('rubricSource').value;try{const result=await api('rubric-import',{source_text:source});if(sequence!==assignmentEditor.sequence)return null;showRubricPreview(result);return result;}catch(e){if(sequence===assignmentEditor.sequence){assignmentEditor.ready=false;$('importStatus').textContent=e.message;$('importStatus').classList.add('needs-check');}throw e;}}
async function importRubricDocument(file){if(!file)return;if(assignmentEditor.loading)return;if(!/\.docx$/i.test(file.name))throw Error('请选择 Word（.docx）文件。旧版 Word 请先另存为 .docx。');if(file.size>10*1024*1024)throw Error('文件不能超过 10 MB。');clearTimeout(assignmentEditor.timer);assignmentEditor.sequence++;assignmentEditor.loading=true;$('rubricSource').disabled=true;$('saveAssignment').disabled=true;$('importStatus').textContent='正在读取文件…';try{const bytes=new Uint8Array(await file.arrayBuffer());let binary='';for(let i=0;i<bytes.length;i+=8192)binary+=String.fromCharCode(...bytes.subarray(i,i+8192));const result=await api('rubric-import',{file:btoa(binary),filename:file.name});$('rubricSource').value=result.source_text;assignmentEditor.filename=file.name;assignmentEditor.originalSource=result.source_text;$('importFilename').textContent=file.name;assignmentEdited();showRubricPreview(result);}catch(e){$('importStatus').textContent=e.message;$('importStatus').classList.add('needs-check');throw e;}finally{assignmentEditor.loading=false;$('rubricSource').disabled=false;$('saveAssignment').disabled=false;$('rubricDocument').value='';}}
function initAssignmentEditor(){
  inspectRubric().catch(e=>message(e.message,true));
  $('reuseAssignment').onclick=()=>{if(!protectAssignment())return;const title=$('assignmentTitle').value,type=$('assignmentType').value,instructions=$('instructions').value,rubric=$('rubricSource').value;resetAssignment();$('assignmentTitle').value=title?title+'（副本）':'';$('assignmentType').value=type;$('instructions').value=instructions;$('rubricSource').value=rubric;assignmentEdited();inspectRubric().catch(e=>message(e.message,true));};
  $('archiveAssignment').onclick=safeAction(async()=>{if(!assignmentEditor.id)throw Error('请先选择已保存的作业题。');if(!protectAssignment()||!window.confirm('归档此作业题？已导入报告与原评分依据会保留，可在设置中恢复题目。'))return;await api('assignments/'+assignmentEditor.id+'/archive',{revision:assignmentEditor.revision});assignmentEditor.dirty=false;resetAssignment();await refresh();message('作业题已归档，可在设置中恢复。');});
  $('assignmentType').oninput=assignmentEdited;$('externalTask').oninput=assignmentEdited;
  $('submissionFiles').onchange=()=>{$('importSubmissions').textContent='导入所选文件';submissionImport.queue=Array.from($('submissionFiles').files).map(file=>({file,token:crypto.randomUUID().replaceAll('-',''),status:'等待导入'}));drawSubmissionQueue();};
  $('importSubmissions').onclick=safeAction(importSubmissionBatch);
  $('assignmentHandoff').onclick=safeAction(exportAssignmentHandoff);
  $('assignmentTitle').oninput=assignmentEdited;$('instructions').oninput=assignmentEdited;
  $('rubricSource').oninput=()=>{assignmentEdited();assignmentEditor.ready=false;clearTimeout(assignmentEditor.timer);assignmentEditor.timer=setTimeout(()=>inspectRubric().catch(e=>message(e.message,true)),450);};
  $('chooseRubric').onclick=()=>$('rubricDocument').click();$('rubricDocument').onchange=safeAction(()=>importRubricDocument($('rubricDocument').files[0]));
  const drop=$('rubricDrop');drop.ondragover=e=>{e.preventDefault();drop.classList.add('drag-over');};drop.ondragleave=e=>{if(!drop.contains(e.relatedTarget))drop.classList.remove('drag-over');};drop.ondrop=e=>{e.preventDefault();drop.classList.remove('drag-over');if(e.dataTransfer.files.length>1){message('请每次导入一份评分文件。',true);return;}importRubricDocument(e.dataTransfer.files[0]).catch(err=>message(err.message,true));};
  $('newAssignment').onclick=()=>{if(protectAssignment()){resetAssignment();$('assignmentTitle').focus();}};
  $('assignmentForm').onsubmit=async e=>{e.preventDefault();if(assignmentEditor.loading||submissionImport.running)return;const button=$('saveAssignment');assignmentEditor.saving=true;button.disabled=true;try{clearTimeout(assignmentEditor.timer);const result=await inspectRubric();if(!result?.ready)throw Error('请先核对评分细则：'+(result?.messages.join(' ')||'读取尚未完成。'));const path='assignments'+(assignmentEditor.id?'/'+assignmentEditor.id:'');const saved=await api(path,{title:$('assignmentTitle').value,instructions:$('instructions').value,assignment_type:$('assignmentType').value,external_task:$('externalTask').value,source_text:$('rubricSource').value,original_source_text:assignmentEditor.originalSource||$('rubricSource').value,revision:assignmentEditor.revision});assignmentEditor.dirty=false;await refresh();loadAssignment(state.bootstrap.assignments.find(a=>a.id===saved.id));if($('assignmentSelect')){$('assignmentSelect').value=saved.id;assignmentInfo();}window.dispatchEvent(new Event('labwise:assignment-saved'));message('作业已保存，可在批改时选择使用。');}catch(err){message(err.message,true);}finally{assignmentEditor.saving=false;button.disabled=false;}};
}

// Each saved assignment owns multiple independent student submissions.
const submissionImport={running:false,queue:[]};
function clearSubmissionQueue(){$('importSubmissions').textContent='导入所选文件';submissionImport.queue=[];$('submissionFiles').value='';$('submissionQueue').replaceChildren();$('submissionStatus').textContent='';}
function renderSubmissionPanel(a){
  clearSubmissionQueue();$('submissionPanel').hidden=false;$('submissionHeading').textContent='学生提交 · '+a.title;
  $('submissionContext').textContent=`${a.assignment_type||'实验报告'} · 评分标准第 ${a.revision||1} 版 · 导入前请先保存题目修改`;
  drawSavedSubmissions(a.id);
}
function drawSavedSubmissions(id){
  const list=$('savedSubmissions');list.replaceChildren();
  const reports=(state.bootstrap?.reports||[]).filter(r=>r.assignment_id===id&&!r.sample);
  if(!reports.length){list.append(node('p','muted','还没有学生提交。可在上方一次选择多份文件。'));return;}
  for(const report of reports){const row=node('div','submission-row');row.append(node('b',null,report.filename),node('span',null,({parsed:'待自动分析',queued:'AI 排队中',waiting_key:'等待 AI 连接',analyzing:'AI 分析中',ready:'AI 结果可查看',failed:'AI 分析失败'})[report.status]||report.status));const open=node('button',null,report.confirmed?'查看反馈':report.status==='ready'?'查看 AI 结果':'查看分析进度');open.type='button';open.onclick=safeAction(async()=>{if(!submissionImport.running&&protectChange())await openReport(report.id);});row.append(open);list.append(row);}
}
function drawSubmissionQueue(){
  const list=$('submissionQueue');list.replaceChildren();
  for(const entry of submissionImport.queue){const row=node('div','submission-row');row.append(node('span',null,entry.file.name),node('span',entry.error?'submission-error':null,entry.status));list.append(row);}
}
async function importSubmissionBatch(){
  if(submissionImport.running)return;
  if(!assignmentEditor.id)throw Error('请先保存作业题与评分标准。');
  if(assignmentEditor.dirty)throw Error('请先保存题目修改，再导入学生作业。');
  const queue=submissionImport.queue.filter(entry=>!entry.saved);
  if(!queue.length)throw Error('请先选择需要导入的 Word 文件。');
  if(submissionImport.queue.length>30)throw Error('每批最多 30 份，请分批选择。');
  const id=assignmentEditor.id,revision=assignmentEditor.revision;
  submissionImport.running=true;$('importSubmissions').disabled=true;$('saveAssignment').disabled=true;$('submissionFiles').disabled=true;
  let imported=0;
  try{
    for(let i=0;i<queue.length;i++){
      const entry=queue[i];entry.error=false;entry.status='正在读取…';drawSubmissionQueue();
      $('submissionStatus').textContent=`正在导入 ${i+1} / ${queue.length}，请保持此页面打开。`;
      try{
        if(!/\.docx$/i.test(entry.file.name))throw Error('请选择 .docx 文件');
        if(entry.file.size>10*1024*1024)throw Error('文件超过 10 MB');
        const bytes=new Uint8Array(await entry.file.arrayBuffer());let binary='';
        for(let offset=0;offset<bytes.length;offset+=8192)binary+=String.fromCharCode(...bytes.subarray(offset,offset+8192));
        const report=await api('reports',{assignment_id:id,assignment_revision:revision,import_token:entry.token,filename:entry.file.name,file:btoa(binary)});
        entry.saved=true;entry.status=report.status==='waiting_key'?'已保存 · 等待 AI 连接':'已保存 · 已加入 AI 分析队列';imported++;
        // Keep the visible saved list useful even if the subsequent refresh fails.
        state.bootstrap.reports.push({id:report.id,filename:report.filename,status:report.status,assignment_id:id,sample:false,confirmed:report.confirmed,updated:report.updated,auto_analysis:report.auto_analysis,has_ai_result:report.analysis?.mode==='deepseek'});
      }catch(e){entry.error=true;entry.status=e.message;}
      drawSubmissionQueue();drawSavedSubmissions(id);
    }
    const failures=queue.filter(entry=>!entry.saved).length;
    $('submissionStatus').textContent=`本次已保存 ${imported} 份${failures?'，'+failures+' 份未完成。核对已保存列表后，可重试未完成文件。':'，可在下方查看。'}`;
    if(imported)recordTeacherAction('批量导入学生作业：'+imported+' 份');
    try{await refresh();drawSavedSubmissions(id);}catch{message('文件处理已结束，列表刷新失败，请稍后重新打开本题核对。');}
  }finally{submissionImport.running=false;$('importSubmissions').disabled=false;$('saveAssignment').disabled=false;$('submissionFiles').disabled=false;$('importSubmissions').textContent=submissionImport.queue.some(e=>!e.saved)?'重试未完成文件':'导入所选文件';}
}
async function exportAssignmentHandoff(){
  if(!assignmentEditor.id||assignmentEditor.dirty)throw Error('请先保存作业题，再导出摘要。');
  const result=await api('assignments/'+assignmentEditor.id+'/handoff');
  const url=URL.createObjectURL(new Blob([result.content],{type:'text/plain;charset=utf-8'}));
  const link=document.createElement('a');link.href=url;link.download=result.filename;document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
  message('摘要已导出。请在对应平台人工录入并核对评分表；尚未同步 Turnitin。');
}
