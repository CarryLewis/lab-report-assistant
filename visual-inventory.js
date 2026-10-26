/* Local discovery is separate from external visual review. */
let inventoryRunning=false,inventoryPause=false,inventoryEditId=null,inventoryThumbnailObserver=null;
const visualKindNames={unknown:'待分类',chart:'科学图表',table:'数据表',scientific_image:'实验图片',diagram:'示意图',other:'其他'};
const visualPageStates={pending:'待扫描',with_candidates:'发现候选',no_candidates:'本地未发现候选',needs_supplement:'待补扫',failed:'解析失败'};
async function inventoryMutation(action,body={}){
 const report=state.report;if(!report)throw Error('请先打开报告。');
 const result=await api('reports/'+report.id+'/'+action,{revision:report.revision,...body});
 if(state.report?.id!==report.id)throw Error('报告已切换，请重新打开图表目录。');
 renderReport(result);return result;
}
async function beginVisualScan(rescan=false,retry=false){
 if(inventoryRunning||state.busy||state.saving)return;
 if(state.dirty)await save('save');
 inventoryRunning=true;inventoryPause=false;state.busy=true;renderVisualInventory();
 try{
  await inventoryMutation('visual-scan',{rescan,retry});
  while(state.report.visual_scan?.status==='running'&&!inventoryPause){
   await inventoryMutation('visual-scan-next',{scan_id:state.report.visual_scan.id});
  }
  if(inventoryPause&&state.report.visual_scan?.status==='running')await inventoryMutation('visual-scan-cancel',{scan_id:state.report.visual_scan.id});
  message(inventoryPause?'扫描已暂停，已发现的图表保留，可继续扫描。':'本地发现完成。请检查目录和待补查页面；尚未执行 AI 科学审核。');
 }finally{inventoryRunning=false;state.busy=false;renderVisualInventory();}
}
$('discoverVisuals').onclick=safeAction(()=>beginVisualScan());
$('rescanVisuals').onclick=safeAction(()=>beginVisualScan(true));
$('retryVisualScan').onclick=safeAction(()=>beginVisualScan(false,true));
$('pauseVisualScan').onclick=()=>{inventoryPause=true;$('pauseVisualScan').disabled=true;$('visualScanProgress').textContent='正在完成当前页并暂停…';};
$('closeVisualCapture').addEventListener('click',()=>{inventoryEditId=null;});
$('visualCaptureDialog').addEventListener('cancel',()=>{inventoryEditId=null;});
$('visualCaptureDialog').addEventListener('close',()=>{inventoryEditId=null;});
$('startVisualReview').addEventListener('click',()=>{inventoryEditId=null;});
$('saveVisualCandidate').onclick=safeAction(async()=>{
 if(state.busy||state.saving)return;
 if(!visualCapture||visualCapture.report_id!==state.report?.id)throw Error('请重新框选原文件中的图表。');
 if(state.dirty)await save('save');
 state.busy=true;
 try{
  await inventoryMutation('visual-object',{id:inventoryEditId||undefined,source_sha256:visualCapture.source_sha256,page:visualCapture.page,bbox:visualCapture.bbox});
  inventoryEditId=null;visualCapture=null;$('visualCaptureDialog').close();message('原页选区已保存到本地图表目录，未发送给 AI。');
 }finally{state.busy=false;renderVisualInventory();}
});
async function inventoryLocate(obj,capture=false){
 if(state.busy||state.saving)throw Error('请等待扫描或保存完成。');
 if(obj.source_sha256!==state.report.source_sha256)throw Error('该图表属于旧版原文件，请重新扫描。');
 inventoryEditId=capture?obj.id:null;pendingAnchor={type:capture?'labwise:capture-visual':'labwise:visual-region',page:obj.page,bbox:obj.bbox};
 await showOriginal();sendAnchor();
}
function renderVisualInventory(){
 if(!$('visualInventory')||!state.report)return;
 document.querySelectorAll('#liveReview input,#liveReview textarea,#liveReview select').forEach(el=>{
  if(inventoryRunning){if(el.dataset.inventoryDisabled===undefined)el.dataset.inventoryDisabled=String(el.disabled);el.disabled=true;}
  else if(el.dataset.inventoryDisabled!==undefined){el.disabled=el.dataset.inventoryDisabled==='true';delete el.dataset.inventoryDisabled;}
 });
 const scan=state.report.visual_scan,objects=state.report.visual_objects||[];
 $('discoverVisuals').disabled=inventoryRunning;
 $('discoverVisuals').textContent=scan&&['running','cancelled'].includes(scan.status)?'继续扫描':'自动发现图表';
 $('pauseVisualScan').hidden=!inventoryRunning;$('pauseVisualScan').disabled=inventoryPause;
 $('rescanVisuals').hidden=!scan;$('rescanVisuals').disabled=inventoryRunning;
 $('retryVisualScan').hidden=!scan?.pages.some(p=>p.state==='failed');$('retryVisualScan').disabled=inventoryRunning;
 const active=objects.filter(o=>o.decision!=='excluded');
 const unresolved=scan?.pages.filter(p=>['failed','needs_supplement'].includes(p.state)).length||0;
 const names={running:'逐页扫描中（离开页面后可继续）',cancelled:'已暂停',completed:'本地扫描完成',partial_completed:'本地扫描部分完成，需人工补查'};
 $('visualScanProgress').textContent=scan?(names[scan.status]||scan.status)+' · '+scan.processed+'/'+scan.page_count+' 页 · '+active.length+' 个候选'+(unresolved?' · '+unresolved+' 页待补查':'')+'。未执行 AI 科学审核。':active.length?'已手动保存 '+active.length+' 个候选，可继续自动发现。':'尚未扫描；可自动发现，也可在原页手动框选并保存目录。';
 $('visualPageCoverage').hidden=!scan;const coverage=$('visualCoverageList');coverage.replaceChildren();
 scan?.pages.forEach(pg=>{const row=node('p',pg.state==='failed'||pg.state==='needs_supplement'?'inventory-warning':'', '第 '+pg.page+' 页 · '+visualPageStates[pg.state]+(pg.message?'：'+pg.message:''));coverage.append(row);});
 const host=$('visualObjectList');host.replaceChildren();inventoryThumbnailObserver?.disconnect();
 if(!objects.length){host.append(node('p','muted',scan?'暂无候选。请结合逐页覆盖结果判断是否需要手动补选。':'发现结果将在这里显示。'));return;}
 if(typeof IntersectionObserver==='function')inventoryThumbnailObserver=new IntersectionObserver(entries=>{for(const entry of entries)if(entry.isIntersecting){inventoryThumbnailObserver.unobserve(entry.target);void loadInventoryThumbnail(entry.target);}});
 objects.forEach((obj,index)=>{
  const card=node('article','visual-object-card'+(obj.decision==='excluded'?' excluded':''));
  card.append(node('b',null,(index+1)+'. 第 '+obj.page+' 页 · '+visualKindNames[obj.type]),node('small','muted',(obj.manual?'教师补选':'本地候选')+' · '+({pending:'待核实',confirmed:'教师已确认',excluded:'已排除'}[obj.decision])));
  const image=node('img');image.alt='第 '+obj.page+' 页图表候选缩略图';image.dataset.objectId=obj.id;image.dataset.reportId=state.report.id;card.append(image);
  if(inventoryThumbnailObserver)inventoryThumbnailObserver.observe(image);else image.alt+='（点击定位查看原页）';
  if(obj.caption_candidate)card.append(node('p','muted','候选图注（待核对）：'+obj.caption_candidate));
  card.append(node('p','muted',obj.evidence?.join('；')||'教师修订的选区'));
  const title=node('input');title.value=obj.title||'';title.disabled=inventoryRunning;title.maxLength=200;title.placeholder='为该图表添加名称';title.setAttribute('aria-label','第 '+(index+1)+' 个图表名称');
  const kind=node('select');kind.setAttribute('aria-label','第 '+(index+1)+' 个图表类型');for(const [value,label]of Object.entries(visualKindNames)){const option=node('option',null,label);option.value=value;kind.append(option);}kind.value=obj.type;kind.disabled=inventoryRunning;card.append(title,kind);
  const actions=node('div','row');
  const add=(label,handler)=>{const button=node('button',null,label);button.type='button';button.disabled=inventoryRunning;button.onclick=safeAction(handler);actions.append(button);};
  add('定位原页',()=>inventoryLocate(obj));
  add('审核此图',()=>inventoryLocate(obj,true));
  add('重新框选',async()=>{await inventoryLocate(obj);inventoryEditId=obj.id;pendingAnchor={type:'labwise:start-visual'};sendAnchor();message('重新框选后，点击“保存到图表目录”替换此选区。');});
  const edit=async decision=>{if(state.busy||state.saving)return;if(state.dirty)await save('save');await inventoryMutation('visual-object',{id:obj.id,type:kind.value,title:title.value,decision,source_sha256:state.report.source_sha256});};
  add('确认并保存',()=>edit('confirmed'));add(obj.decision==='excluded'?'恢复候选':'排除误识别',()=>edit(obj.decision==='excluded'?'pending':'excluded'));
  card.append(actions);host.append(card);
 });
}
async function loadInventoryThumbnail(img){
 try{const data=await api('reports/'+img.dataset.reportId+'/visual-thumbnail/'+img.dataset.objectId);if(img.isConnected)img.src='data:image/png;base64,'+data.image;}
 catch(e){if(img.isConnected){img.alt='缩略图暂不可用，请定位原页';img.title=e.message;}}
}
