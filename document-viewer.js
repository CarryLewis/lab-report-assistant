/* Original-page viewer: PDF stays local; DOCX is converted by the local service. */
(()=>{'use strict';
const input=document.getElementById('fileInput'),choose=document.getElementById('choose');
const container=document.querySelector('.center .document'),paper=document.getElementById('paper');
let file=null,url=null,generation=0;
const notice=document.createElement('div');notice.className='original-notice';notice.hidden=true;
const frame=document.createElement('iframe');frame.className='original-frame';frame.title='原文件 PDF 阅读器';frame.hidden=true;
const toolbar=document.createElement('div');toolbar.className='original-tools';toolbar.hidden=true;
const external=document.createElement('a');external.textContent='在独立窗口打开';external.target='_blank';external.rel='noopener';
const replace=document.createElement('button');replace.textContent='更换文件';replace.onclick=()=>input.click();
const fullscreen=document.createElement('button');fullscreen.textContent='全屏阅读';fullscreen.onclick=()=>{container.requestFullscreen?.().catch(()=>showToast('无法进入全屏，请在独立窗口打开。'));};
toolbar.append(external,replace,fullscreen);container.prepend(notice,toolbar,frame);
const subtitle=document.querySelector('.docname small');
function error(text){notice.textContent=text;notice.hidden=false;}
function clear(){if(url)URL.revokeObjectURL(url);url=null;frame.removeAttribute('src');frame.hidden=true;external.removeAttribute('href');toolbar.hidden=true;}
function present(blob){url=URL.createObjectURL(blob);frame.src=url+'#view=FitH';external.href=url;frame.hidden=false;toolbar.hidden=false;}
async function load(selected){const token=++generation;file=selected;clear();paper.hidden=true;container.classList.add('original-mode');document.querySelector('.pagehint').hidden=true;
document.getElementById('docTitle').textContent=file.name;subtitle.textContent=/\.pdf$/i.test(file.name)?'PDF · 原文件页面':'Word · 本机转换预览';
// Hide sample-only controls and prevent sample evidence from being mistaken for this document.
document.querySelectorAll('.doccontrols button').forEach(b=>{if(!b.classList.contains('turnitin-entry'))b.hidden=true;});
document.querySelectorAll('.workspace .left,.workspace .right').forEach(el=>el.inert=true);
error('正在准备原文件预览…');
try{if(!/\.(pdf|docx)$/i.test(file.name))throw Error('请选择 PDF 或 DOCX 文件。');if(file.size>10*1024*1024)throw Error('文件不能超过 10 MB。');
if(/\.pdf$/i.test(file.name)){present(new Blob([file],{type:'application/pdf'}));error('正在显示原始 PDF。可在阅读器中缩放、查找和翻页；若浏览器不支持内嵌预览，请在独立窗口打开。两侧示例批改暂不可用。');}
else{const bytes=new Uint8Array(await file.arrayBuffer());if(token!==generation)return;let binary='';for(let i=0;i<bytes.length;i+=8192)binary+=String.fromCharCode(...bytes.subarray(i,i+8192));const response=await fetch('/api/pilot/document-preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({filename:file.name,file:btoa(binary)})});const data=await response.json();if(token!==generation)return;if(!response.ok)throw Error(data.error||'预览失败');const raw=atob(data.file);const output=Uint8Array.from(raw,c=>c.charCodeAt(0));present(new Blob([output],{type:'application/pdf'}));error('Word 已在本机转换为分页预览。字体、公式或复杂排版可能与 Word 有差异；严格保留版式时，请从 Word 导出 PDF。两侧示例批改暂不可用。');}
}catch(err){if(token===generation){error(err.message);toolbar.hidden=false;external.hidden=true;return;}}external.hidden=false;
}
input.onchange=()=>{const selected=input.files[0];if(!selected)return;document.getElementById('filelabel').textContent='已选择：'+selected.name;choose.textContent='打开原文件';choose.onclick=()=>{showPage('workspace');load(selected);};if(!document.getElementById('workspacePage').classList.contains('hidden'))load(selected);};
window.addEventListener('beforeunload',()=>{if(url)URL.revokeObjectURL(url);});
})();
