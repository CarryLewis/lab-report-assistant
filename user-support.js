/* Localize application copy only; imported content is passed through unchanged. */
var uiT=globalThis.LabwiseI18n?.t||((text,...values)=>typeof text==='string'?text:text.reduce((s,part,i)=>s+part+(i<values.length?values[i]:''),''));
/* Offline help, recoverable operations and explicit local issue reports. */
(function(){
'use strict';
const feedbackKey='labwise.support.draft.v1';
const topics=[
 [uiT('安装与启动'),uiT('安装版的启动、资料和退出'),[
  uiT('macOS Apple Silicon 试用版：打开 DMG，把 Labwise.app 拖入应用程序，再从应用程序目录启动。也可使用 ZIP 解压后的应用。'),
  uiT('启动窗口检查依赖并显示实际本机地址。重复启动会复用同一资料工作区，常用端口被占用时自动选择备用端口。'),
  uiT('安装版资料独立于程序，默认位于用户的 Library/Application Support/Labwise/data。源码版保留原资料目录，安装时不静默迁移或合并。'),
  uiT('关闭网页不会退出应用。请先保存草稿，再通过启动窗口退出；替换应用前先退出并下载备份。'),
  uiT('试用包未进行 Developer ID 签名与 Apple 公证。如系统阻止打开，请向维护者取得正式签名版本。Word 分页 PDF 另需 LibreOffice。')
 ]],
 [uiT('快速开始'),uiT('完成第一份报告'),[
  uiT('在“设置”保存访问密钥，先检查连接，再点击“测试分析接口”。密钥已保存不代表分析可用；测试使用虚构内容，可能产生服务用量。'),
  uiT('点击“创建作业题”，填写题目和要求，导入或粘贴评分细则。核对评分项目、各项满分与合计后保存。'),
  uiT('回到工作台选择作业，快速导入一份 DOCX；多份文件点击“批量导入”，进入所选作业的学生提交区。'),
  uiT('等待分析结果，核对建议中的引文，逐条确认或不采纳，再填写分项评分、学生反馈及适用的图表复核。'),
  uiT('中途离开先保存草稿；完成后点击确认按钮，按缺项提示补齐，再确认。确认后可能自动打开下一份。'),
  uiT('从工作台打开已确认报告，选择所需格式导出；在浏览器下载记录中查找文件。')
 ]],
 [uiT('文体与写作批改'),uiT('实验报告以外的写作任务'),[
  uiT('支持实验报告、学术议论文／课程论文、文献综述、研究计划、研究报告、案例分析、反思写作和通用写作批改。文本文件仍使用 DOCX。'),
  uiT('在“课程与作业”选择文体模板，先查看评分建议和反馈示例，再点击“应用文体模板”。应用会填入要求和评分细则；已有输入时需要确认替换。'),
  uiT('模板是原创试用起点，权重不是学校官方标准。可以改写要求、修改分值，或导入自己的评分细则；也能在“评分标准”中查看和复用模板。'),
  uiT('只选择模板作预览不会改变作业。已导入文本会保留当时的文体与评分快照；修改作业后仅后续导入使用新版本。'),
  uiT('反馈示例仅供措辞参考。AI 按当前文本语言生成候选反馈、用中文解释；教师仍须核对原文、评分并确认。')
 ]],
 [uiT('服务配置'),uiT('配置、测试与外部 AI'),[
  uiT('“密钥已保存”仅说明本机已保存配置；“检查连接”只测试模型列表；“测试分析接口”才验证一次分析结果。'),
  uiT('更换模型或密钥后需要重新测试。一次测试成功不保证今后请求一直可用。'),
  uiT('报告和评阅记录在本机保存；使用外部 AI 时会联网发送本次分析所需的内容，请使用获准的服务。没有密钥时报告会等待连接，仍可填写并保存草稿。')
 ]],
 [uiT('作业与导入'),uiT('准备评分标准和批量文件'),[
  uiT('评分细则可自由输入、粘贴或导入 DOCX。点击“让 AI 理解”后核对项目、权重、等级和附加规则，保存后用于评分；信息不完整可先保存原文草稿。'),
  uiT('首页快速入口每次导入一份；作业的学生提交区支持多选，每批最多 30 份，每份不超过 10 MB，仅接收 .docx。'),
  uiT('同一作业、同一版评分标准下重新导入相同原文件，会打开已有报告并保留批改。不同原文件名或标准版本分别保存。'),
  uiT('导入前保存作业修改。部分文件失败时，已保存的文件保留，只需点击“重试未完成文件”。分析失败请重试分析，不必重新导入。'),
  uiT('已导入报告保留当时的标准快照。后续修改作业标准不会静默改变已有报告的评分依据。')
 ]],
 [uiT('评阅与保存'),uiT('核对证据、保存和继续'),[
  uiT('AI 按当前报告的评分快照给出逐项建议分数、理由和原文依据。可采纳或修改；“填入空白评分”会保留已经填写的分数，最终由教师确认。'),
  uiT('处理建议、填写评分和学生反馈。私人评阅笔记仅供自己使用，不进入学生反馈导出。'),
  uiT('自由编辑内容需要点击“保存草稿”，请看到保存成功后再关闭。当前后台自动分析期间也可保存草稿；分析不会替换教师的评分、笔记和反馈。历史报告如提示旧版分析，请待其完成后保存。'),
  uiT('保存失败时当前输入保留，可从错误面板“导出当前输入”。版本冲突时先保留输入再重新打开核对，避免覆盖。'),
  uiT('下次在工作台点击该作业的“继续批改”。历史版本恢复会生成新草稿，核对后需要重新确认。')
 ]],
 [uiT('确认与导出'),uiT('检查完整性并选择文件格式'),[
  uiT('确认检查会列出缺少的评分、尚未处理的建议和适用的图表复核。未完成时仍可保存草稿。'),
  uiT('分析进行中请先保存草稿，等待结果并核对建议后再确认。确认后可继续下一份；也可从列表重开已确认报告导出。'),
  uiT('PDF 适合预览整体呈现；Word 批改包包含原稿、批注稿和评分数据；Word 摘要与文字版适合单独整理评语。'),
  uiT('修改评分或反馈后需要重新确认。下载由浏览器处理，请检查下载记录；导出不会自动向学生发送。')
 ]],
 [uiT('故障恢复'),uiT('遇到问题时如何继续'),[
  uiT('导入失败：检查 .docx 格式和 10 MB 大小限制；批量只重试未完成文件。'),
  uiT('分析失败：在工作台该报告旁重试分析。未配置服务时进入设置。已保存的原稿无需重复导入。'),
  uiT('预览失败：重新加载原文件；仍不可用时下载原稿核对，不要把无法定位的建议当成证据已核实。'),
  uiT('保存失败：不要刷新，先导出当前输入，再检查本机应用是否在运行并重试。'),
  uiT('确认成功但下一份打开失败：上一份已确认，返回工作台继续批改。导出失败也不必重新评分。'),
  uiT('仍无法处理时，打开“向开发者报告问题”，填写操作与实际结果；未配置接收渠道时导出反馈包交给维护者。')
 ]],
 [uiT('数据与备份'),uiT('本机保存、恢复和升级'),[
  uiT('“设置 → 本机资料与备份”显示实际数据目录。历史版本只恢复单份报告，不能代替完整备份。'),
  uiT('先保存评阅内容，再下载备份 ZIP。备份包括已保存的作业、原稿、评分、笔记、历史版本及进度，不包含 API 密钥或浏览器内的未提交问题草稿。'),
  uiT('恢复备份会建立独立副本，不替换当前工作区。macOS 可关闭当前应用后双击恢复目录内的“启动恢复副本.command”，按提示打开副本并重新配置密钥。'),
  uiT('当前提供 macOS Apple Silicon 本机试用安装包，其他系统与自动升级仍待交付。更新前备份并保留资料目录，不要把程序替换与资料清理一起操作。超过工具限额时关闭应用后复制整个数据目录。')
 ]],
 [uiT('软件问题反馈'),uiT('把问题交给开发者'),[
  uiT('“学生反馈”是给学生的评语；“向开发者报告问题”用于报告软件故障或改进建议。'),
  uiT('描述操作步骤、预期与实际结果，可留下联系邮箱。草稿仅存在当前浏览器的本机存储中，换浏览器、换端口或清理浏览器数据后不能保证保留。'),
  uiT('默认诊断仅包含应用版本、当前模块、分析状态与配置测试状态，不附原稿、引文、评分、私人笔记、文件名、完整路径或密钥。请自行检查自由描述中的身份信息。'),
  uiT('当前没有配置开发者接收端；预览后可导出反馈包，由你交给维护者。导出不代表已发送。')
 ]]
];
function button(text,fn){const b=node('button',null,text);b.type='button';b.onclick=fn;return b;}
function dialog(id,title){const d=node('dialog','support-dialog');d.id=id;const head=node('div','support-heading');head.append(node('h2',null,title),button(uiT('关闭'),()=>d.close()));d.append(head);document.body.append(d);d.addEventListener('close',()=>{if(errors.parentElement===d)document.querySelector('.topbar').after(errors);d._opener?.focus();});return d;}
function show(d){if(d.open)return;if(d.id==='supportHelp')helpExport.disabled=!state.report;d._opener=document.activeElement;d.showModal();}
const help=dialog('supportHelp',uiT('帮助与反馈'));
const helpExport=button(uiT('导出当前评阅输入'),()=>exportInputs());
const helpActions=node('div','support-actions');helpActions.append(button(uiT('向开发者报告问题'),()=>openFeedback()),helpExport);help.append(helpActions);
const search=node('input');search.type='search';search.placeholder=uiT('搜索操作或问题…');search.setAttribute('aria-label',uiT('搜索使用指南'));help.append(search);
const helpBody=node('div');help.append(helpBody);
function renderHelp(){helpBody.replaceChildren();const q=search.value.trim().toLowerCase();for(const [name,title,steps] of topics){if(q&&![name,title,...steps].join(' ').toLowerCase().includes(q))continue;const details=node('details','support-topic');details.open=!!q||name===uiT('快速开始');details.append(node('summary',null,name+' · '+title));const list=node('ol');for(const text of steps)list.append(node('li',null,text));details.append(list);helpBody.append(details);}if(!helpBody.children.length)helpBody.append(node('p',null,uiT('没有匹配的指引，试试搜索“保存”“导入”或“恢复”。')));}
search.oninput=renderHelp;renderHelp();
$('usageHelp').onclick=()=>show(help);

const start=node('section','support-start');start.id='gettingStarted';start.setAttribute('aria-label',uiT('首次使用准备清单'));document.querySelector('.dashboard-shortcuts').after(start);
function renderStart(){
 const data=state.bootstrap;if(!data)return;start.replaceChildren(node('h2',null,uiT('开始与继续使用')));
 const tested=data.settings.connection_test?.state==='passed';
 const unfinished=data.reports.find(r=>!r.confirmed&&r.grading_state==='in_progress')||data.reports.find(r=>!r.confirmed);
 const actions=node('div','support-actions');
 actions.append(button(tested?uiT('分析测试已通过 · 查看设置'):uiT('1. 配置并测试服务'),()=>openTeacherSection('settings')),
  button(data.assignments.length?uiT('2. 查看作业与评分标准'):uiT('2. 创建第一份作业'),()=>{if(openTeacherSection('assignments')&&!data.assignments.length)resetAssignment();}),
  button(unfinished?uiT('3. 继续批改'):uiT('3. 导入报告'),safeAction(async()=>{if(unfinished){await continueAssignment(unfinished.assignment_id);return;}if(!data.assignments.length){if(openTeacherSection('assignments')){$('assignmentTitle').focus();message(uiT('请先创建并保存作业，再导入报告。'));}}else $('assignmentSelect').focus();})),button(uiT('查看完整入门步骤'),()=>show(help)));
 start.append(actions,node('p','muted',uiT('分析结果需由教师核对。关闭前保存草稿；已确认报告才可导出正式反馈。')));
}
$('batchImportEntry').onclick=()=>{const selected=state.bootstrap?.assignments.find(a=>a.id===$('assignmentSelect').value);if(!openTeacherSection('assignments'))return;if(selected){loadAssignment(selected);$('submissionPanel').scrollIntoView({block:'start'});$('submissionFiles').focus();}else{$('assignmentTitle').focus();message(uiT('请先创建并保存作业题，再批量导入。'));}};

const errors=node('section','support-error');errors.hidden=true;errors.setAttribute('role','alert');errors.setAttribute('aria-label',uiT('需要处理的问题'));document.querySelector('.topbar').after(errors);
let errorContext='operation';
function showError(text,retry,context='operation'){
 errorContext=context;
 const openDialog=Array.from(document.querySelectorAll('dialog[open]')).at(-1);if(openDialog)openDialog.prepend(errors);else document.querySelector('.topbar').after(errors);
 errors.replaceChildren(node('strong',null,uiT('本次操作未完成或需要核对')),node('p',null,text));errors.hidden=false;
 const actions=node('div','support-actions');
 if(retry)actions.append(button(uiT('重试本次操作'),safeAction(async()=>{errors.hidden=true;await retry();},context)));
 if(state.report)actions.append(button(uiT('导出当前输入'),exportInputs));
 actions.append(button(uiT('查看恢复办法'),()=>{search.value=uiT('故障恢复');renderHelp();show(help);}),button(uiT('向开发者报告问题'),()=>openFeedback(errorContext)),button(uiT('关闭提示'),()=>errors.hidden=true));errors.append(actions);
}
function renderNotice(report){
 const notice=$('workNotice');if(report.confirmed)return;
 if(report.status==='waiting_key')notice.append(button(uiT('去配置服务'),()=>openTeacherSection('settings')));
 if(report.status==='failed')notice.append(button(uiT('重试分析'),safeAction(async()=>{if(state.dirty)await save('save');const latest=await api('reports/'+report.id);await api('reports/'+report.id+'/auto-analysis',{revision:latest.revision,retry:true});await refresh();message(uiT('已重新排队分析。'));})));
 if(['waiting_key','failed'].includes(report.status))notice.append(button(uiT('查看恢复办法'),()=>{search.value=uiT('故障恢复');renderHelp();show(help);}));
}
function exportInputs(){
 if(!state.report)return message(uiT('请先打开一份报告。'));
 const p=reviewPayload();const raw={format:'labwise-review-recovery.v1',saved_at:new Date().toISOString(),report_id:state.report.id,...p};
 download(JSON.stringify(raw,null,2),'Labwise-current-review-inputs.json','application/json');
 message(uiT('已开始下载当前输入，仅供你恢复与核对；包含评阅内容和私人笔记，请勿作为软件问题诊断包发送。'));
}

const confirmDialog=dialog('reviewCheckDialog',uiT('确认前检查'));const checkBody=node('div');confirmDialog.append(checkBody);
function confirmationIssues(){
 const issues=[];if(!state.report)return issues;
 if(state.report.status==='analyzing')issues.push({text:uiT('分析仍在进行，请先保存草稿，待分析完成后核对结果。'),target:'workNotice'});
 for(const input of $('scores').querySelectorAll('input'))if(input.value===''||!input.checkValidity())issues.push({text:uiT('填写有效评分：')+input.getAttribute('aria-label'),element:input});
 for(const finding of state.report.analysis?.findings||[])if(!['accepted','edited','rejected'].includes(state.report.reviews[finding.id]))issues.push({text:uiT('处理评阅建议：')+finding.title,target:'finding-'+finding.id});
 for(const review of state.report.visual_reviews||[])if((review.decision||'pending')==='pending')issues.push({text:uiT('完成图表复核：')+review.id,target:'visual-check-'+review.id});
 return issues;
}
function openConfirmation(){
 if(state.saving||state.busy)return message(uiT('请等待当前操作完成。'));
 checkBody.replaceChildren();const issues=confirmationIssues();
 if(issues.length){checkBody.append(node('p',null,uiT('还有 ')+issues.length+uiT(' 项需要处理；可以先保存草稿。')));const list=node('ul');for(const item of issues){const li=node('li');li.append(button(item.text,()=>{const el=item.element||$(item.target);confirmDialog._opener=el;confirmDialog.close();el?.scrollIntoView({block:'center'});if(el){el.tabIndex=el.tabIndex<0?0:el.tabIndex;el.focus();}}));list.append(li);}checkBody.append(list,button(uiT('保存草稿'),safeAction(async()=>{await save('save');confirmDialog.close();})));}
 else{checkBody.append(node('p',null,uiT('评分、候选建议及适用的图表复核已完成。请核对学生反馈；私人笔记不会导出。确认后将保存本份评分，并按队列继续。')));if(!state.report.analysis)checkBody.append(node('p',null,uiT('本次没有 AI 分析结果，确认的是你的手动评分与反馈。')));const commit=button(uiT('确认评分与反馈'),safeAction(async()=>{commit.disabled=true;try{await save('confirm');confirmDialog.close();}finally{commit.disabled=false;}}));commit.className='primary';checkBody.append(commit);}
 show(confirmDialog);
}
function renderVisualChecks(){
 $('legacyVisualChecks')?.remove();const reviews=state.report?.visual_reviews||[];if(!reviews.length)return;
 const section=node('section');section.id='legacyVisualChecks';section.append(node('h3',null,uiT('图表复核')));
 for(const review of reviews){const label=node('label',null,uiT('图表 ')+review.id);label.id='visual-check-'+review.id;const select=node('select');select.setAttribute('aria-label',uiT('图表 ')+review.id+uiT('复核'));for(const [value,text] of [['pending',uiT('待复核')],['accepted',uiT('确认')],['rejected',uiT('不采纳')]]){const option=node('option',null,text);option.value=value;select.append(option);}select.value=review.decision||'pending';select.onchange=()=>{review.decision=select.value;dirty();};label.append(select);section.append(label);}$('wordCoverage').after(section);
}

const feedback=dialog('developerFeedback',uiT('向开发者报告问题'));
feedback.append(node('p',null,uiT('反馈先保存在当前浏览器的本机草稿中。当前未配置接收渠道，请预览后导出反馈包交给维护者；导出不会发送。')));
const form=node('form');form.id='developerFeedbackForm';
function field(title,id,type,required=false){const label=node('label',null,title);let el=node(type==='textarea'?'textarea':'input');el.id=id;if(type!=='textarea')el.type=type;else el.rows=4;el.required=required;el.maxLength=type==='textarea'?6000:200;label.append(el);form.append(label);return el;}
const kindLabel=node('label',null,uiT('问题类型'));const kind=node('select');kind.id='issueKind';for(const name of ['启动与设置','文件导入','分析','原文定位','评分与保存','导出','界面操作','改进建议','其他']){const option=node('option',null,uiT(name));option.value=name;kind.append(option);}kindLabel.append(kind);form.append(kindLabel);
const title=field(uiT('简短标题（必填）'),'issueTitle','text',true);
const description=field(uiT('操作步骤、预期结果与实际结果（必填）'),'issueDescription','textarea',true);
const email=field(uiT('联系邮箱（可选）'),'issueEmail','email');
form.append(node('p','muted',uiT('请检查自由描述中的姓名、学号和密钥。诊断信息不包含报告、引文、评分、私人笔记、文件名或本机路径。')));
const status=node('p');status.id='issueDraftState';status.setAttribute('role','status');form.append(status);
const preview=node('pre','support-preview');preview.id='issuePreview';preview.hidden=true;form.append(preview);
const previewButton=node('button',null,uiT('预览反馈包'));previewButton.type='submit';const exportButton=button(uiT('导出反馈包（不发送）'),()=>{if(!form.reportValidity())return;const packet=previewPacket;if(!packet)return;download(JSON.stringify(packet,null,2),'Labwise-issue-'+packet.id+'.json','application/json');status.textContent=uiT('已开始下载，请查看浏览器下载记录；尚未发送给开发者。');});exportButton.disabled=true;
const actions=node('div','support-actions');actions.append(previewButton,exportButton,button(uiT('清空草稿'),()=>{try{localStorage.removeItem(feedbackKey);}catch{status.textContent=uiT('无法清空浏览器中的草稿，请检查存储权限。');return;}form.reset();issueId=crypto.randomUUID();issueCreated=new Date().toISOString();previewPacket=null;preview.hidden=true;exportButton.disabled=true;status.textContent=uiT('已清空当前草稿。');}));form.append(actions);feedback.append(form);
let issueId=crypto.randomUUID(),issueCreated=new Date().toISOString(),issueContext='operation',previewPacket=null;
function draft(){return {id:issueId,created_at:issueCreated,kind:kind.value,title:title.value,description:description.value,email:email.value,context:issueContext};}
function makePacket(){const test=state.bootstrap?.settings.connection_test;return {format:'labwise-issue.v1',...draft(),diagnostic:{app_version:document.querySelector('.pilot-badge')?.textContent.match(/v[\d.]+/)?.[0]||'unknown',module:['home','assignments','standards','analytics','settings','workspace'].includes(state.section)?state.section:'home',analysis_state:['parsed','queued','waiting_key','analyzing','ready','failed'].includes(state.report?.status)?state.report.status:'none',connection_test:['passed','failed'].includes(test?.state)?test.state:'not-tested',time_zone:Intl.DateTimeFormat().resolvedOptions().timeZone}};}
function persistDraft(){previewPacket=null;preview.hidden=true;exportButton.disabled=true;try{localStorage.setItem(feedbackKey,JSON.stringify(draft()));status.textContent=uiT('草稿已保存在当前浏览器。');}catch{status.textContent=uiT('浏览器无法保存草稿，请预览后导出，关闭前保留副本。');}}
form.oninput=persistDraft;form.onchange=persistDraft;
form.onsubmit=e=>{e.preventDefault();previewPacket=makePacket();const p=previewPacket;preview.textContent=uiT`问题编号：${p.id}\n创建时间：${new Date(p.created_at).toLocaleString(globalThis.LabwiseI18n?.locale==='en'?'en-GB':'zh-CN')}\n问题类型：${uiT(p.kind)}\n标题：${p.title}\n描述：${p.description}\n联系邮箱：${p.email||uiT('未填写')}\n应用版本：${p.diagnostic.app_version}\n所在模块：${({home:uiT('工作台'),assignments:uiT('课程与作业'),standards:uiT('评分标准'),analytics:uiT('数据分析'),settings:uiT('设置'),workspace:uiT('报告评阅')})[p.diagnostic.module]}\n分析状态：${({none:uiT('未打开报告'),parsed:uiT('待处理'),queued:uiT('排队中'),waiting_key:uiT('等待配置'),analyzing:uiT('分析中'),ready:uiT('分析完成'),failed:uiT('分析失败')})[p.diagnostic.analysis_state]}\n连接测试：${({passed:uiT('当次测试通过'),failed:uiT('当次测试失败'),'not-tested':uiT('未测试')})[p.diagnostic.connection_test]}\n时区：${p.diagnostic.time_zone}`;preview.hidden=false;exportButton.disabled=false;status.textContent=uiT('请检查以下内容；只会导出这里展示的信息。');};
function openFeedback(context='operation'){
 let hasDraft=false;try{const saved=JSON.parse(localStorage.getItem(feedbackKey)||'null');if(saved&&typeof saved.title==='string'&&typeof saved.description==='string'&&typeof saved.id==='string'&&typeof saved.created_at==='string'){hasDraft=true;issueId=saved.id;issueCreated=saved.created_at;kind.value=saved.kind;title.value=saved.title;description.value=saved.description;email.value=typeof saved.email==='string'?saved.email:'';issueContext=saved.context;}}catch{}
 if(!hasDraft||context!=='operation')issueContext=['operation','import','settings','analysis','export','save','preview'].includes(context)?context:'operation';if(!hasDraft)kind.value=({import:'文件导入',settings:'启动与设置',analysis:'分析',export:'导出',save:'评分与保存',preview:'原文定位',operation:'其他'})[issueContext];persistDraft();show(feedback);
}

const dataPanel=node('article','panel settings-note');dataPanel.id='localDataPanel';dataPanel.append(node('h2',null,uiT('本机资料与备份')),node('p',null,uiT('先保存评阅内容再备份。ZIP 包包含已保存的原稿、评分、私人笔记和历史记录，请妥善保管；不含访问密钥。')));
const dataPath=node('p','support-path');dataPath.id='localDataPath';dataPanel.append(dataPath);
const dataStatus=node('div');dataStatus.id='backupStatus';dataStatus.setAttribute('role','status');
const restoreInput=node('input');restoreInput.type='file';restoreInput.accept='.zip';restoreInput.id='restoreBackupFile';restoreInput.setAttribute('aria-label',uiT('选择 Labwise 备份 ZIP'));
const backup=button(uiT('下载完整备份'),safeAction(async()=>{if(state.dirty||assignmentEditor.dirty)throw Error(uiT('请先保存当前修改，再生成备份。'));backup.disabled=true;dataStatus.textContent=uiT('正在生成已保存资料的备份…');try{const pack=await api('backup',{});downloadBase64Package(pack);dataStatus.textContent=uiT('已开始下载备份（')+pack.reports+uiT(' 份报告），请查看下载记录；不包含密钥和未保存输入。');}finally{backup.disabled=false;}}));
const restore=button(uiT('恢复为独立副本'),safeAction(async()=>{
 const file=restoreInput.files[0];if(!file)throw Error(uiT('请先选择 Labwise 备份 ZIP。'));if(file.size>64*1024*1024)throw Error(uiT('备份 ZIP 不能超过 64 MB。'));
 if(!window.confirm(uiT('将在新的资料目录建立恢复副本，不替换当前工作区。备份不包含密钥，副本需重新配置。继续？')))return;
 restore.disabled=true;dataStatus.textContent=uiT('正在校验并恢复为独立副本…');
 try{const bytes=new Uint8Array(await file.arrayBuffer());let binary='';for(let i=0;i<bytes.length;i+=8192)binary+=String.fromCharCode(...bytes.subarray(i,i+8192));const result=await api('restore-backup',{file:btoa(binary)});dataStatus.replaceChildren(node('p',null,uiT('已建立独立副本，当前工作区未改变。')),node('p','support-path',result.directory),node('p',null,uiT('macOS：关闭当前应用后，在上面的目录双击“启动恢复副本.command”，打开 ')+result.url+uiT(' 并重新配置密钥。其他系统请按恢复目录内说明指定资料目录启动。')));}finally{restore.disabled=false;}
}));
dataPanel.append(backup,node('p',null,uiT('恢复仅建立独立副本，原工作区保留。工具支持 ZIP 最大 64 MB、展开资料最大 256 MB；超过限额请关闭应用后复制整个数据目录。')),restoreInput,restore,dataStatus,node('p','muted',uiT('更新程序前下载备份，并保留实际资料目录。当前未提供自动升级安装器；不要覆盖或删除资料目录。')));
$('settingsSettings').append(dataPanel);
async function loadDataInfo(){try{const info=await api('data-info');dataPath.textContent=uiT('当前数据目录：')+info.directory;}catch{dataPath.textContent=uiT('暂时无法读取资料位置，请检查本机应用是否在运行。');}}
window.LabwiseSupport={showError,renderNotice,renderStart,renderVisualChecks,openConfirmation,openFeedback,exportInputs};
renderStart();loadDataInfo();
})();
