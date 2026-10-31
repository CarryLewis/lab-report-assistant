'use strict';
/* Localize application copy only; imported content is passed through unchanged. */
var uiT=globalThis.LabwiseI18n?.t||((text,...values)=>typeof text==='string'?text:text.reduce((s,part,i)=>s+part+(i<values.length?values[i]:''),''));
const assignmentEditor={id:null,revision:null,dirty:false,ready:false,sequence:0,timer:null,filename:'',loading:false};
function assignmentEdited(){assignmentEditor.dirty=true;$('assignmentSaveState').textContent=uiT('有未保存修改');}
function protectAssignment(){if(assignmentEditor.loading||assignmentEditor.saving){message(uiT('正在读取或保存评分标准，请稍候。'));return false;}if(submissionImport.running){message(uiT('正在导入，请等待本批文件处理完成。'));return false;}return !assignmentEditor.dirty||window.confirm(uiT('这份作业还有未保存的修改，确定切换吗？'));}
function rubricMethodLabel(rubric){return (rubric.processing_mode||(rubric.schema_version==='rubric-understanding.v1'?'ai':'code'))==='ai'?uiT('AI 分析版本'):uiT('代码版本');}
function rubricAsText(rubric){return rubric.source_text||rubric.criteria.map(c=>uiT`${c.name}（${c.maximum_points??c.weight}分）\n${c.descriptor||''}`).join('\n\n');}
function renderAssignmentLibrary(assignments){
  const list=$('assignmentList');list.replaceChildren();
  if(!assignments.length)list.append(node('p','muted',uiT('还没有保存作业。从左侧添加第一份吧。')));
  assignments.forEach(a=>{const button=node('button','assignment-item'+(assignmentEditor.id===a.id?' selected':''));button.type='button';const icon=node('span','assignment-icon','▤');const detail=node('span','assignment-detail');detail.append(node('b',null,a.title),node('small',null,uiT`${a.assignment_type||uiT('实验报告')} · ${rubricMethodLabel(a.rubric)} · ${a.rubric.criteria.length} 个评分项目 · 总分 ${a.rubric.criteria.reduce((n,c)=>n+(c.maximum_points??c.weight),0)}`));button.append(icon,detail,node('span','assignment-arrow',uiT('查看 / 修改 →')));button.onclick=()=>{if(protectAssignment())loadAssignment(a);};list.append(button);});
}
function resetAssignment(){clearTimeout(assignmentEditor.timer);assignmentEditor.sequence++;Object.assign(assignmentEditor,{id:null,revision:null,dirty:false,ready:false,filename:'',originalSource:'',understanding:null,context:null,modeResults:{}});$('assignmentForm').reset();syncRubricMode();syncWritingTemplate();$('submissionPanel').hidden=true;clearSubmissionQueue();$('editorTitle').textContent=uiT('新建作业');$('assignmentSaveState').textContent=uiT('尚未保存');$('saveAssignment').textContent=uiT('保存作业');$('rubricPreviewPanel').hidden=true;$('importStatus').textContent=uiT('保留每个评分项目的名称、分值和说明，便于准确整理。');$('importStatus').classList.remove('needs-check');$('importFilename').textContent=uiT('也可直接粘贴文字');renderAssignmentLibrary(state.bootstrap?.assignments||[]);inspectRubric().catch(e=>message(e.message,true));}
function loadAssignment(a){clearTimeout(assignmentEditor.timer);assignmentEditor.sequence++;Object.assign(assignmentEditor,{id:a.id,revision:a.revision||1,dirty:false,filename:'',originalSource:a.rubric.original_source_text||a.rubric.source_text||''});$('assignmentTitle').value=a.title;$('instructions').value=a.instructions;$('assignmentType').value=a.assignment_type||uiT('实验报告');syncWritingTemplate();$('externalTask').value=a.external_task||'';$('rubricSource').value=rubricAsText(a.rubric);$('rubricProcessingMode').value=a.rubric.processing_mode||(a.rubric.schema_version==='rubric-understanding.v1'?'ai':'code');syncRubricMode();$('editorTitle').textContent=uiT('编辑作业');$('assignmentSaveState').textContent=uiT('已保存');$('saveAssignment').textContent=uiT('保存修改');$('importFilename').textContent=uiT('已保存的评分细则');renderAssignmentLibrary(state.bootstrap.assignments);renderSubmissionPanel(a);assignmentEditor.understanding=a.rubric.schema_version==='rubric-understanding.v1'?structuredClone(a.rubric):{...structuredClone(a.rubric),source_text:rubricAsText(a.rubric),total:a.rubric.criteria.reduce((n,c)=>n+c.maximum_points,0),ready:true,messages:[],legacy:true};assignmentEditor.context=rubricContext();inspectRubric().catch(e=>message(e.message,true));}
const rubricTypes={points:uiT('分值制'),weights:uiT('权重制'),levels:uiT('等级标准'),holistic:uiT('整体评分'),qualitative:uiT('定性要求'),mixed:uiT('混合评分')};
function rubricMode(){return $('rubricProcessingMode').value||'ai';}
function syncRubricMode(){const code=rubricMode()==='code';$('understandRubric').textContent=code?uiT('按代码规则解析'):uiT('更新预览');$('rubricModeHelp').textContent=code?uiT('沿用原有规则：例如每行“实验方法（30分）”。细则解析在本机完成；报告仍可生成 AI 反馈，分数由教师填写。'):uiT('接受自然语言、权重、等级和扣分规则；AI 理解后按该标准给出建议评分。');assignmentEditor.lastMode=rubricMode();}
function switchRubricMode(){if(assignmentEditor.loading||assignmentEditor.saving){$('rubricProcessingMode').value=assignmentEditor.lastMode;return;}const previous=assignmentEditor.lastMode;assignmentEditor.modeResults??={};if(assignmentEditor.understanding)assignmentEditor.modeResults[previous]={result:assignmentEditor.understanding,context:assignmentEditor.context};const cached=assignmentEditor.modeResults[rubricMode()];invalidateRubric();syncRubricMode();if(cached?.context===rubricContext()){assignmentEditor.understanding=cached.result;assignmentEditor.context=cached.context;showRubricPreview(cached.result);}else void inspectRubric().catch(e=>message(e.message,true));assignmentEdited();}
function rubricContext(){return JSON.stringify([rubricMode(),$('rubricSource').value.trim(),$('assignmentType').value.trim(),$('instructions').value.trim()]);}
function rubricPreviewState(stage,description,source=$('rubricSource').value){
  const panel=$('rubricPreviewPanel');panel.hidden=false;panel.dataset.state=stage;panel.setAttribute('aria-busy',String(stage==='reading'||stage==='analyzing'));
  $('previewTotal').textContent='';$('rubricPreviewStatus').textContent=description;$('rubricPreviewHelp').hidden=true;
  const host=$('rubricPreview');host.replaceChildren();
  if(source.trim()){host.append(node('p','muted',uiT('导入原文')),node('pre','rubric-source-preview',source));}
}
function invalidateRubric(){assignmentEditor.sequence++;assignmentEditor.understanding=null;assignmentEditor.context=null;assignmentEditor.ready=false;const hasSource=!!$('rubricSource').value.trim();const description=hasSource?(rubricMode()==='code'?uiT('文字已更新，将按原有代码规则解析。'):uiT('原文已更新，点击“更新预览”重新理解。')):uiT('导入 Word 或粘贴细则后，这里会自动显示可编辑的评分项目。');rubricPreviewState(hasSource?'pending':'empty',description);$('importStatus').textContent=description;$('importStatus').classList.remove('needs-check');}
function scheduleRubricPreview(){clearTimeout(assignmentEditor.timer);assignmentEditor.timer=setTimeout(()=>{if(assignmentEditor.loading){assignmentEditor.pendingAutoPreview=true;return;}if(!assignmentEditor.saving&&$('rubricSource').value.trim())inspectRubric(rubricMode()==='ai').catch(e=>message(e.message,true));},450);}
function showRubricPreview(parsed){
  $('rubricPreviewPanel').hidden=false;$('rubricPreviewPanel').dataset.state='ready';$('rubricPreviewPanel').setAttribute('aria-busy','false');$('rubricPreviewStatus').textContent=uiT('请核对并编辑项目名称、分值和评分要求，确认后保存作业。');$('rubricPreviewHelp').hidden=false;$('previewTotal').textContent=parsed.criteria.length?uiT`合计 ${parsed.total} ${parsed.percentage?'%':uiT('分')}`:'';const host=$('rubricPreview');host.replaceChildren();
  if(parsed.summary)host.append(node('p','rubric-understanding-summary',parsed.summary));
  host.append(node('p','muted',rubricTypes[parsed.input_type]||uiT('已保存的评分标准')));
  parsed.criteria.forEach((criterion,index)=>{
    const item=node('section','criterion-preview');const nameLabel=node('label',null,uiT('评分项目 ')+(index+1));const name=node('input');name.value=criterion.name;name.maxLength=200;nameLabel.append(name);
    const scoreLabel=node('label',null,parsed.percentage?uiT('权重（%）'):uiT('满分'));const score=node('input');score.type='number';score.min='.01';score.max='10000';score.step='any';score.value=criterion.maximum_points??'';score.placeholder=uiT('尚未明确');scoreLabel.append(score);
    const descLabel=node('label',null,uiT('评分要求'));const description=node('textarea');description.rows=3;description.maxLength=4000;description.value=criterion.descriptor||'';descLabel.append(description);
    const update=()=>{if(!name.value.trim()||(score.value&&!score.checkValidity())){message(uiT('请核对项目名称和分值。'),true);return;}criterion.name=name.value.trim();criterion.maximum_points=score.value?Number(score.value):null;criterion.descriptor=description.value;parsed.edited_by_teacher=true;if(parsed.legacy){if(!assignmentEditor.originalSource)assignmentEditor.originalSource=parsed.source_text;$('rubricSource').value=parsed.criteria.map(c=>uiT`${c.name}（${c.maximum_points}分）\n${c.descriptor||''}`).join('\n\n');parsed.source_text=$('rubricSource').value;assignmentEditor.context=rubricContext();}parsed.total=parsed.criteria.reduce((n,c)=>n+(c.maximum_points||0),0);assignmentEdited();$('previewTotal').textContent=uiT`合计 ${parsed.total} ${parsed.percentage?'%':uiT('分')}`;};
    name.onchange=update;score.onchange=update;description.onchange=update;item.append(nameLabel,scoreLabel,descLabel);
    if(criterion.weight_percent!=null&&!parsed.percentage)item.append(node('small','muted',uiT('原文权重：')+criterion.weight_percent+'%'));
    if(criterion.levels?.length){const levels=node('div','rubric-levels');levels.append(node('b',null,uiT('等级标准')));for(const level of criterion.levels)levels.append(node('p',null,level.label+(level.minimum!=null||level.maximum!=null?`（${level.minimum??'…'}–${level.maximum??'…'}）`:'')+'：'+level.descriptor));item.append(levels);}
    if(criterion.source_quote){const evidence=node('details','rubric-source-evidence');evidence.append(node('summary',null,uiT('对应细则原文')),node('blockquote',null,criterion.source_quote));item.append(evidence);}
    host.append(item);
  });
  if(parsed.special_rules?.length){const rules=node('section','rubric-special-rules');rules.append(node('h3',null,uiT('附加评分规则')));for(const rule of parsed.special_rules){const detail=node('details');detail.append(node('summary',null,rule.description),node('blockquote',null,rule.source_quote));rules.append(detail);}host.append(rules);}
  if(parsed.messages?.length){const issues=node('section','rubric-questions');issues.append(node('b',null,uiT('需要补充或确认')));for(const question of parsed.messages)issues.append(node('p',null,question));issues.append(node('p','muted',uiT('在左侧原文补充说明后，再次点击“让 AI 理解”；也可先保存草稿。')));host.append(issues);}
  const original=node('details','original-rubric');original.append(node('summary',null,uiT('查看评分细则原文')),node('pre',null,parsed.source_text));host.append(original);
  $('importStatus').textContent=parsed.legacy?(parsed.ready?uiT`代码规则已整理 ${parsed.criteria.length} 个项目，分数由教师填写。`:parsed.messages.join(' ')):parsed.ready?uiT`已理解 ${parsed.criteria.length} 个评分项目。可修改理解结果，保存后用于分析与评分。`:uiT('理解结果已保留，请补充待确认内容，或先保存草稿。');$('importStatus').classList.toggle('needs-check',!parsed.ready);assignmentEditor.ready=parsed.ready;
}
async function inspectRubric(understand=false){
  if(assignmentEditor.understanding&&assignmentEditor.context===rubricContext()&&!understand){showRubricPreview(assignmentEditor.understanding);return assignmentEditor.understanding;}
  if(rubricMode()==='code'){
    const sequence=++assignmentEditor.sequence,context=rubricContext();
    rubricPreviewState('analyzing',uiT('正在整理评分项目…'));
    let result;try{result=await api('rubric-import',{source_text:$('rubricSource').value});}catch(e){if(sequence===assignmentEditor.sequence)rubricPreviewState('error',e.message);throw e;}
    if(sequence!==assignmentEditor.sequence||context!==rubricContext())return null;
    result.legacy=true;assignmentEditor.understanding=result;assignmentEditor.context=context;showRubricPreview(result);return result;
  }
  if(!understand){invalidateRubric();return null;}
  if(assignmentEditor.loading||assignmentEditor.saving)return null;
  const source=$('rubricSource').value.trim();if(!source)throw Error(uiT('请先输入或导入评分细则。'));
  const sequence=++assignmentEditor.sequence,context=rubricContext();assignmentEditor.loading=true;assignmentEditor.ready=false;assignmentEditor.understanding=null;rubricPreviewState('analyzing',uiT('AI 正在整理评分项目，完成后可直接编辑。'));$('understandRubric').disabled=true;$('saveAssignment').disabled=true;$('importStatus').textContent=uiT('AI 正在阅读评分细则，理解维度、分值、等级与附加规则…');
  try{const result=await api('rubric-understand',{source_text:source,assignment_type:$('assignmentType').value,instructions:$('instructions').value});if(sequence!==assignmentEditor.sequence||context!==rubricContext())return null;assignmentEditor.understanding=result;assignmentEditor.context=context;assignmentEdited();showRubricPreview(result);return result;}
  catch(e){if(sequence===assignmentEditor.sequence){$('importStatus').textContent=e.message;$('importStatus').classList.add('needs-check');rubricPreviewState('error',e.message);}throw e;}
  finally{assignmentEditor.loading=false;$('understandRubric').disabled=false;$('saveAssignment').disabled=false;if(assignmentEditor.pendingAutoPreview){assignmentEditor.pendingAutoPreview=false;scheduleRubricPreview();}}
}
async function importRubricDocument(file){
  if(!file||assignmentEditor.loading||assignmentEditor.saving)return;
  if(!/\.docx$/i.test(file.name))throw Error(uiT('请选择 Word（.docx）文件。旧版 Word 请先另存为 .docx。'));
  if(file.size>10*1024*1024)throw Error(uiT('文件不能超过 10 MB。'));
  clearTimeout(assignmentEditor.timer);invalidateRubric();assignmentEditor.loading=true;
  $('rubricSource').disabled=true;$('understandRubric').disabled=true;$('saveAssignment').disabled=true;
  $('importStatus').textContent=uiT('正在读取文件…');rubricPreviewState('reading',uiT('正在读取文件…'),'');
  let imported=false;
  try{
    const bytes=new Uint8Array(await file.arrayBuffer());let binary='';for(let i=0;i<bytes.length;i+=8192)binary+=String.fromCharCode(...bytes.subarray(i,i+8192));
    const result=await api('rubric-import',{file:btoa(binary),filename:file.name,extract_only:true});
    $('rubricSource').value=result.source_text;assignmentEditor.filename=file.name;assignmentEditor.originalSource=result.source_text;
    $('importFilename').textContent=file.name;assignmentEdited();invalidateRubric();imported=true;
  }catch(e){$('importStatus').textContent=e.message;$('importStatus').classList.add('needs-check');rubricPreviewState('error',e.message);throw e;}
  finally{assignmentEditor.loading=false;$('rubricSource').disabled=false;$('understandRubric').disabled=false;$('saveAssignment').disabled=false;$('rubricDocument').value='';}
  if(imported)await inspectRubric(rubricMode()==='ai');
}
function rubricDraftPayload(){return {processing_mode:rubricMode(),title:$('assignmentTitle').value,assignment_type:$('assignmentType').value,instructions:$('instructions').value,source_text:$('rubricSource').value,external_task:$('externalTask').value,...(assignmentEditor.understanding&&!assignmentEditor.understanding.legacy&&assignmentEditor.context===rubricContext()?{rubric_understanding:assignmentEditor.understanding}:{}),assignment_id:assignmentEditor.id,revision:assignmentEditor.revision};}
async function saveRubricDraft(){if(assignmentEditor.saving)throw Error(uiT('正在保存，请稍候。'));const payload=rubricDraftPayload();await api('rubric-draft',payload);if(JSON.stringify(payload)===JSON.stringify(rubricDraftPayload())){assignmentEditor.dirty=false;$('assignmentSaveState').textContent=uiT('草稿已保存');}message(uiT('评分原文草稿已保存在本机，可用“恢复草稿”继续。'));}
async function restoreRubricDraft(){if(!protectAssignment())return;const saved=await api('rubric-draft');const draft=saved.drafts?.find(d=>d.processing_mode===rubricMode())||(!saved.drafts?.length?saved.draft:null);if(!draft){message(uiT('还没有保存的评分草稿。'));return;}resetAssignment();$('rubricProcessingMode').value=draft.processing_mode||'ai';syncRubricMode();assignmentEditor.id=draft.assignment_id||null;assignmentEditor.revision=draft.revision;$('assignmentTitle').value=draft.title;$('assignmentType').value=draft.assignment_type;$('instructions').value=draft.instructions;$('rubricSource').value=draft.source_text;$('externalTask').value=draft.external_task;syncWritingTemplate();invalidateRubric();if(draft.rubric_understanding){assignmentEditor.understanding=draft.rubric_understanding;assignmentEditor.context=rubricContext();showRubricPreview(draft.rubric_understanding);}$('editorTitle').textContent=uiT('继续评分草稿');$('assignmentSaveState').textContent=uiT('已恢复草稿');}
function initAssignmentEditor(){
  initWritingProfiles();syncRubricMode();$('rubricProcessingMode').onchange=switchRubricMode;
  $('understandRubric').onclick=safeAction(()=>inspectRubric(true));$('saveRubricDraft').onclick=safeAction(saveRubricDraft);$('restoreRubricDraft').onclick=safeAction(restoreRubricDraft);
  inspectRubric().catch(e=>message(e.message,true));
  $('reuseAssignment').onclick=()=>{if(!protectAssignment())return;const title=$('assignmentTitle').value,type=$('assignmentType').value,instructions=$('instructions').value,rubric=$('rubricSource').value,mode=rubricMode(),understanding=assignmentEditor.understanding?structuredClone(assignmentEditor.understanding):null;resetAssignment();$('rubricProcessingMode').value=mode;syncRubricMode();$('assignmentTitle').value=title?title+uiT('（副本）'):'';$('assignmentType').value=type;syncWritingTemplate();$('instructions').value=instructions;$('rubricSource').value=rubric;if(understanding){assignmentEditor.understanding=understanding;assignmentEditor.context=rubricContext();}assignmentEdited();inspectRubric().catch(e=>message(e.message,true));};
  $('archiveAssignment').onclick=safeAction(async()=>{if(!assignmentEditor.id)throw Error(uiT('请先选择已保存的作业题。'));if(!protectAssignment()||!window.confirm(uiT('归档此作业题？已导入报告与原评分依据会保留，可在设置中恢复题目。')))return;await api('assignments/'+assignmentEditor.id+'/archive',{revision:assignmentEditor.revision});assignmentEditor.dirty=false;resetAssignment();await refresh();message(uiT('作业题已归档，可在设置中恢复。'));});
  $('assignmentType').oninput=()=>{assignmentEdited();syncWritingTemplate();invalidateRubric();};$('externalTask').oninput=assignmentEdited;
  $('submissionFiles').onchange=()=>{$('importSubmissions').textContent=uiT('导入所选文件');submissionImport.queue=Array.from($('submissionFiles').files).map(file=>({file,token:crypto.randomUUID().replaceAll('-',''),status:uiT('等待导入')}));drawSubmissionQueue();};
  $('importSubmissions').onclick=safeAction(importSubmissionBatch);
  $('assignmentHandoff').onclick=safeAction(exportAssignmentHandoff);
  $('assignmentTitle').oninput=assignmentEdited;$('instructions').oninput=()=>{assignmentEdited();invalidateRubric();};
  $('rubricSource').onpaste=()=>{assignmentEditor.pasting=true;};
  $('rubricSource').oninput=()=>{assignmentEdited();invalidateRubric();clearTimeout(assignmentEditor.timer);if(rubricMode()==='code'||assignmentEditor.pasting)scheduleRubricPreview();assignmentEditor.pasting=false;};
  $('chooseRubric').onclick=()=>$('rubricDocument').click();$('rubricDocument').onchange=safeAction(()=>importRubricDocument($('rubricDocument').files[0]));
  const drop=$('rubricDrop');drop.ondragover=e=>{e.preventDefault();drop.classList.add('drag-over');};drop.ondragleave=e=>{if(!drop.contains(e.relatedTarget))drop.classList.remove('drag-over');};drop.ondrop=e=>{e.preventDefault();drop.classList.remove('drag-over');if(e.dataTransfer.files.length>1){message(uiT('请每次导入一份评分文件。'),true);return;}importRubricDocument(e.dataTransfer.files[0]).catch(err=>message(err.message,true));};
  $('newAssignment').onclick=()=>{if(protectAssignment()){resetAssignment();$('assignmentTitle').focus();}};
  $('assignmentForm').onsubmit=async e=>{e.preventDefault();if(assignmentEditor.loading||assignmentEditor.saving||submissionImport.running)return;const button=$('saveAssignment');assignmentEditor.saving=true;button.disabled=true;try{clearTimeout(assignmentEditor.timer);const result=await inspectRubric();if(!result?.ready)throw Error(result?.messages?.join(' ')||(rubricMode()==='code'?uiT('请核对代码解析结果，或先保存草稿。'):uiT('请先点击“让 AI 理解”，也可先保存草稿。')));const path='assignments'+(assignmentEditor.id?'/'+assignmentEditor.id:'');const saved=await api(path,{title:$('assignmentTitle').value,instructions:$('instructions').value,assignment_type:$('assignmentType').value,external_task:$('externalTask').value,processing_mode:rubricMode(),source_text:$('rubricSource').value,original_source_text:assignmentEditor.originalSource||$('rubricSource').value,...(result.legacy?{}:{rubric_understanding:result}),revision:assignmentEditor.revision});assignmentEditor.dirty=false;await refresh();loadAssignment(state.bootstrap.assignments.find(a=>a.id===saved.id));if($('assignmentSelect')){$('assignmentSelect').value=saved.id;assignmentInfo();}window.dispatchEvent(new Event('labwise:assignment-saved'));message(uiT('作业已保存，可在批改时选择使用。'));}catch(err){message(err.message,true);}finally{assignmentEditor.saving=false;button.disabled=false;}};
}

// Each saved assignment owns multiple independent student submissions.
const submissionImport={running:false,queue:[]};
function clearSubmissionQueue(){$('importSubmissions').textContent=uiT('导入所选文件');submissionImport.queue=[];$('submissionFiles').value='';$('submissionQueue').replaceChildren();$('submissionStatus').textContent='';}
function renderSubmissionPanel(a){
  clearSubmissionQueue();$('submissionPanel').hidden=false;$('submissionHeading').textContent=uiT('学生提交 · ')+a.title;
  $('submissionContext').textContent=uiT`${a.assignment_type||uiT('实验报告')} · 评分标准第 ${a.revision||1} 版 · 导入前请先保存题目修改`;
  drawSavedSubmissions(a.id);
}
function drawSavedSubmissions(id){
  const list=$('savedSubmissions');list.replaceChildren();
  const reports=(state.bootstrap?.reports||[]).filter(r=>r.assignment_id===id&&!r.sample);
  if(!reports.length){list.append(node('p','muted',uiT('还没有学生提交。可在上方一次选择多份文件。')));return;}
  for(const report of reports){const row=node('div','submission-row');row.append(node('b',null,report.filename),node('span',null,report.confirmed?uiT('教师已确认'):({parsed:uiT('待处理'),queued:uiT('排队中'),waiting_key:uiT('等待连接'),analyzing:uiT('处理中'),ready:uiT('可评阅'),failed:uiT('处理失败')})[report.status]||report.status));const open=node('button',null,report.confirmed?uiT('查看反馈'):report.status==='ready'?uiT('打开报告'):uiT('查看分析进度'));open.type='button';open.onclick=safeAction(async()=>{if(!submissionImport.running&&protectChange())await openReport(report.id);});row.append(open);list.append(row);}
}
function drawSubmissionQueue(){
  const list=$('submissionQueue');list.replaceChildren();
  for(const entry of submissionImport.queue){const row=node('div','submission-row');row.append(node('span',null,entry.file.name),node('span',entry.error?'submission-error':null,entry.status));list.append(row);}
}
async function importSubmissionBatch(){
  if(submissionImport.running)return;
  if(!assignmentEditor.id)throw Error(uiT('请先保存作业题与评分标准。'));
  if(assignmentEditor.dirty)throw Error(uiT('请先保存题目修改，再导入学生作业。'));
  const queue=submissionImport.queue.filter(entry=>!entry.saved);
  if(!queue.length)throw Error(uiT('请先选择需要导入的 Word 文件。'));
  if(submissionImport.queue.length>30)throw Error(uiT('每批最多 30 份，请分批选择。'));
  const id=assignmentEditor.id,revision=assignmentEditor.revision;
  submissionImport.running=true;$('importSubmissions').disabled=true;$('saveAssignment').disabled=true;$('submissionFiles').disabled=true;
  let imported=0,reused=0;
  try{
    for(let i=0;i<queue.length;i++){
      const entry=queue[i];entry.error=false;entry.status=uiT('正在读取…');drawSubmissionQueue();
      $('submissionStatus').textContent=uiT`正在导入 ${i+1} / ${queue.length}，请保持此页面打开。`;
      try{
        if(!/\.docx$/i.test(entry.file.name))throw Error(uiT('请选择 .docx 文件'));
        if(entry.file.size>10*1024*1024)throw Error(uiT('文件超过 10 MB'));
        const bytes=new Uint8Array(await entry.file.arrayBuffer());let binary='';
        for(let offset=0;offset<bytes.length;offset+=8192)binary+=String.fromCharCode(...bytes.subarray(offset,offset+8192));
        const report=await api('reports',{assignment_id:id,assignment_revision:revision,import_token:entry.token,filename:entry.file.name,file:btoa(binary)});
        entry.saved=true;entry.status=report.import_reused?uiT('已存在 · 保留原批改记录'):report.status==='waiting_key'?uiT('已保存 · 等待连接'):uiT('已保存 · 排队中');if(report.import_reused)reused++;else imported++;
        // Keep the visible saved list useful even if the subsequent refresh fails.
        const summary={id:report.id,filename:report.filename,status:report.status,assignment_id:id,sample:false,confirmed:report.confirmed,updated:report.updated,auto_analysis:report.auto_analysis,has_ai_result:report.analysis?.mode==='deepseek'};const existing=state.bootstrap.reports.find(r=>r.id===report.id);if(existing)Object.assign(existing,summary);else state.bootstrap.reports.push(summary);
      }catch(e){entry.error=true;entry.status=e.message;}
      drawSubmissionQueue();drawSavedSubmissions(id);
    }
    const failures=queue.filter(entry=>!entry.saved).length;
    $('submissionStatus').textContent=uiT`本次新增 ${imported} 份${reused?uiT('，已存在 ')+reused+uiT(' 份（原批改记录保留）'):''}${failures?'，'+failures+uiT(' 份未完成。核对已保存列表后，可重试未完成文件。'):uiT('，可在下方查看。')}`;
    if(imported)recordTeacherAction(uiT('批量导入学生作业：')+imported+uiT(' 份'));
    try{await refresh();drawSavedSubmissions(id);}catch{message(uiT('文件处理已结束，列表刷新失败，请稍后重新打开本题核对。'));}
  }finally{submissionImport.running=false;$('importSubmissions').disabled=false;$('saveAssignment').disabled=false;$('submissionFiles').disabled=false;$('importSubmissions').textContent=submissionImport.queue.some(e=>!e.saved)?uiT('重试未完成文件'):uiT('导入所选文件');}
}
async function exportAssignmentHandoff(){
  if(!assignmentEditor.id||assignmentEditor.dirty)throw Error(uiT('请先保存作业题，再导出摘要。'));
  const result=await api('assignments/'+assignmentEditor.id+'/handoff');
  const url=URL.createObjectURL(new Blob([result.content],{type:'text/plain;charset=utf-8'}));
  const link=document.createElement('a');link.href=url;link.download=result.filename;document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
  message(uiT('摘要已导出。请在对应平台人工录入并核对评分表；尚未同步 Turnitin。'));
}

// Catalog selection is a preview. Only an explicit Apply action changes teacher fields.
let writingProfiles=[];
function syncWritingTemplate(){
 const type=$('assignmentType').value.trim().toLowerCase();
 const profile=writingProfiles.find(p=>[p.name,...p.aliases].some(label=>label.toLowerCase()===type))||writingProfiles.find(p=>p.id==='general_writing');
 if(profile){$('writingTemplate').value=profile.id;renderWritingTemplate();}
}
function renderWritingTemplate(){
 const profile=writingProfiles.find(p=>p.id===$('writingTemplate').value);if(!profile)return;
 $('writingTemplateDescription').textContent=uiT(profile.description)+' '+profile.cautions.map(text=>uiT(text)).join(' ');
 const preview=$('writingTemplatePreview');preview.replaceChildren();
 for(const c of profile.criteria)preview.append(node('p',null,uiT`${c.name}（${c.maximum_points}分）：${c.descriptor}`));
 preview.append(node('p','muted',uiT('以下为原创待审核措辞示例。使用时必须依据当前文本，不能直接当作批改结论。')));
 for(const e of profile.feedback_examples)preview.append(node('p',null,`${e.criterion_name} · ${e.purpose==='strength'?uiT('优点'):uiT('改进')}：${e.text}`));
}
async function initWritingProfiles(){
 try{
  const result=await api('writing-profiles');writingProfiles=result.profiles;
  $('writingTemplate').replaceChildren();
  for(const p of writingProfiles){const option=node('option',null,uiT(p.name));option.value=p.id;$('writingTemplate').append(option);}
  $('writingTemplate').disabled=false;$('applyWritingTemplate').disabled=false;
  $('writingTemplate').onchange=renderWritingTemplate;syncWritingTemplate();renderWritingTemplate();
  $('applyWritingTemplate').onclick=safeAction(async()=>{
   if(assignmentEditor.loading||assignmentEditor.saving||submissionImport.running)throw Error(uiT('请等待当前读取、保存或导入完成。'));
   const profile=writingProfiles.find(p=>p.id===$('writingTemplate').value);if(!profile)return;
   if(($('rubricSource').value.trim()||$('instructions').value.trim())&&!window.confirm(uiT('应用模板将替换当前作业要求和评分细则。已导入文本的标准快照会保留。是否继续？')))return;
   clearTimeout(assignmentEditor.timer);assignmentEditor.sequence++;
   $('assignmentType').value=profile.name;$('instructions').value=profile.instructions;
   $('rubricSource').value=profile.criteria.map(c=>uiT`${c.name}（${c.maximum_points}分）\n${c.descriptor}`).join('\n\n');
   assignmentEditor.originalSource=$('rubricSource').value;assignmentEditor.filename='';
   $('importFilename').textContent=profile.name+uiT(' · 原创试用模板 v')+profile.version;
   assignmentEdited();await inspectRubric();message(uiT('模板已填入。请核对要求与分值，再保存作业。'));
  });
 }catch(e){$('writingTemplateDescription').textContent=uiT('文体模板暂时无法读取。仍可填写类型并导入自己的评分标准。');}
}
