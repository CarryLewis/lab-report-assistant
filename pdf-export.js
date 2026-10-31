'use strict';
/* Localize application copy only; imported content is passed through unchanged. */
var uiT=globalThis.LabwiseI18n?.t||((text,...values)=>typeof text==='string'?text:text.reduce((s,part,i)=>s+part+(i<values.length?values[i]:''),''));
/* One generated PDF is shared by preview and download. No grading data is changed. */
(() => {
 const dialog=document.createElement('dialog');dialog.id='pdfExportDialog';
 dialog.setAttribute('aria-labelledby','pdfExportTitle');
 dialog.innerHTML=uiT`<header class="pdf-export-header"><div><small>LABWISE / EXPORT</small><h2 id="pdfExportTitle">导出评阅 PDF</h2><p id="pdfExportSubtitle"></p></div><button id="pdfExportClose" aria-label="关闭 PDF 导出">✕</button></header>
 <div class="pdf-export-layout"><aside class="pdf-export-settings"><div class="pdf-settings-body"><span class="pdf-export-eyebrow">导出内容</span><h3>一份完整的评阅记录</h3><ol class="pdf-export-outline"><li><b>评分与总评</b><span>总分、分项得分、教师反馈</span></li><li><b>原文与旁批</b><span>保留原文，右侧显示对应评语</span></li><li><b>逐条评语</b><span>原文引句与对应修改建议</span></li><li><b>评分细则</b><span>本次作业使用的评分标准</span></li></ol>
 <fieldset><legend>PDF 设置</legend><label><input id="pdfHighlights" type="checkbox" checked> 在原文显示高亮、编号与旁批</label><label><input id="pdfAnnotations" type="checkbox" checked> 包含教师原文批注</label><label><input id="pdfRubric" type="checkbox" checked> 附上评分细则</label></fieldset><p class="pdf-export-note">仅导出已确认的评分与采纳建议。原文批注会按上方设置导出；私人评阅笔记始终不导出。</p></div><div class="pdf-settings-footer"><button id="pdfGenerate">重新生成预览</button><button id="pdfDownload" class="primary" disabled>下载 PDF</button><p id="pdfExportStatus" role="status" aria-live="polite"></p></div></aside>
 <section class="pdf-export-preview" aria-label="PDF 预览"><div class="pdf-preview-toolbar"><span>PDF 预览</span><span id="pdfPreviewMeta">与下载文件一致</span></div><div id="pdfPreviewEmpty"><span class="pdf-file-icon">PDF</span><h3>正在准备评阅报告</h3><p>生成后可在此检查原文、评分与评语。</p></div><iframe id="pdfPreviewFrame" title="已批改作业 PDF 预览" hidden></iframe></section></div>`;
 document.body.append(dialog);
 const el=id=>document.getElementById(id);
 let target=null,result=null,url=null,generation=0,busy=false,controller=null;
 function clearPreview(){result=null;el('pdfDownload').disabled=true;el('pdfPreviewFrame').hidden=true;el('pdfPreviewFrame').src='about:blank';if(url)URL.revokeObjectURL(url);url=null;el('pdfPreviewMeta').textContent=uiT('与下载文件一致');}
 function cleanup(){generation++;controller?.abort();controller=null;busy=false;clearPreview();el('pdfGenerate').disabled=false;dialog.querySelector('fieldset').disabled=false;}
 dialog.addEventListener('close',cleanup);
 el('pdfExportClose').onclick=()=>dialog.close();
 async function generate(){
  if(busy||!target)return;
  const token=++generation;busy=true;clearPreview();
  el('pdfGenerate').disabled=true;dialog.querySelector('fieldset').disabled=true;
  el('pdfPreviewEmpty').hidden=false;el('pdfPreviewEmpty').querySelector('h3').textContent=uiT('正在生成评阅 PDF');
  el('pdfExportStatus').textContent=uiT('正在排版原文、匹配引文与生成评语，请稍候…');
  el('pdfExportStatus').classList.remove('error');controller=new AbortController();
  try{
   const body={options:{highlights:el('pdfHighlights').checked,annotations:el('pdfAnnotations').checked,rubric:el('pdfRubric').checked}};
   if(target.revision!==undefined)body.revision=target.revision;
   const response=await fetch('/api/pilot/'+target.path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal:controller.signal});
   const pack=await response.json();if(!response.ok)throw Error(pack.error||uiT('PDF 生成失败'));
   if(token!==generation||!dialog.open)return;
   const bytes=Uint8Array.from(atob(pack.content),char=>char.charCodeAt(0));
   url=URL.createObjectURL(new Blob([bytes],{type:'application/pdf'}));result=pack;
   const meta=pack.summary;el('pdfPreviewMeta').textContent=meta.reports+uiT(' 份作业 · ')+meta.pages+uiT(' 页 · ')+meta.comments+uiT(' 条评语');
   el('pdfPreviewFrame').src='/original-reader.html?mode=export&name='+encodeURIComponent(pack.filename)+'&file='+encodeURIComponent(url);
   el('pdfPreviewFrame').hidden=false;el('pdfPreviewEmpty').hidden=true;el('pdfDownload').disabled=false;
   el('pdfExportStatus').textContent=meta.unlocated?meta.unlocated+uiT(' 条评语需核对位置，已列在评语页。请检查后下载。'):uiT('已生成。请检查原文分页与批注后下载。');
  }catch(error){
   if(token!==generation||error.name==='AbortError')return;
   el('pdfPreviewEmpty').querySelector('h3').textContent=uiT('暂时无法生成 PDF');
   el('pdfExportStatus').textContent=error.message;el('pdfExportStatus').classList.add('error');
  }finally{if(token===generation){busy=false;controller=null;el('pdfGenerate').disabled=false;dialog.querySelector('fieldset').disabled=false;}}
 }
 el('pdfGenerate').onclick=generate;
 for(const id of ['pdfHighlights','pdfAnnotations','pdfRubric'])el(id).onchange=()=>{clearPreview();el('pdfPreviewEmpty').hidden=false;el('pdfPreviewEmpty').querySelector('h3').textContent=uiT('设置已更新');el('pdfExportStatus').textContent=uiT('点击“重新生成预览”以应用设置。');};
 el('pdfDownload').onclick=()=>{if(!result||!url)return;const a=document.createElement('a');a.href=url;a.download=result.filename;a.click();el('pdfExportStatus').textContent=uiT('已开始下载 PDF，请查看浏览器下载记录并核对文件。');};
 window.LabwisePdfExport={open(config){
  if(dialog.open)return;cleanup();target={...config};el('pdfExportSubtitle').textContent=config.label;
  for(const id of ['pdfHighlights','pdfAnnotations','pdfRubric'])el(id).checked=true;
  dialog.showModal();dialog.querySelector('.pdf-settings-body').scrollTop=0;void generate();
 }};
})();
