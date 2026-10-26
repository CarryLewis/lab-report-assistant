'use strict';
const id=new URLSearchParams(location.search).get('report');let selection=null,model=null;
const $=id=>document.getElementById(id);
async function api(path){const response=await fetch('/api/pilot/'+path);const data=await response.json();if(!response.ok)throw Error(data.error||'读取失败');return data;}
function notify(type,data={}){parent.postMessage({type,...data},location.origin);}
function paint(findings,reviews){
 document.querySelectorAll('.source-badges').forEach(n=>n.remove());document.querySelectorAll('.has-issue,.has-strength').forEach(n=>n.classList.remove('has-issue','has-strength'));
 for(const finding of findings){
  let target=(finding.paragraph_ids||[]).map(pid=>document.querySelector('[data-paragraph-id="'+CSS.escape(pid)+'"]')).find(p=>p&&(!finding.quote||p.textContent.includes(finding.quote)));
  if(!target&&finding.quote){const candidates=[...document.querySelectorAll('[data-paragraph-id]')].filter(p=>p.textContent.includes(finding.quote));if(candidates.length===1)target=candidates[0];}
  if(!target)continue;
  target.classList.add('has-'+finding.kind);let badges=target.querySelector('.source-badges');
  if(!badges){badges=document.createElement('span');badges.className='source-badges';badges.contentEditable='false';target.prepend(badges);}
  const button=document.createElement('button');button.textContent=finding.id;button.title=finding.title;button.className=finding.kind+(reviews[finding.id]&&reviews[finding.id]!=='pending'?' confirmed':'');button.onclick=()=>notify('labwise:select-finding',{finding_id:finding.id});badges.append(button);
 }
}
function locate(data){
 if(window.CSS?.highlights)CSS.highlights.delete('source-evidence');
 document.querySelectorAll('.located').forEach(n=>n.classList.remove('located'));
 let target=Number.isInteger(data.word_index)?document.querySelector('[data-word-index="'+data.word_index+'"]'):null;
 if(!target&&data.paragraph_id)target=document.querySelector('[data-paragraph-id="'+CSS.escape(data.paragraph_id)+'"]');
 if(target&&data.quote&&!data.object_only&&!target.textContent.includes(data.quote))target=null;
 if(!target&&data.quote){const matches=[...document.querySelectorAll('[data-paragraph-id]')].filter(p=>p.textContent.includes(data.quote));if(matches.length===1)target=matches[0];}
 if(target){
  target.classList.add('located');let exact=false;
  if(data.quote&&window.Highlight&&window.CSS?.highlights){
   const walker=document.createTreeWalker(target,NodeFilter.SHOW_TEXT,{acceptNode:n=>n.parentElement.closest('.source-badges,.object-note')?NodeFilter.FILTER_REJECT:NodeFilter.FILTER_ACCEPT});
   const texts=[];while(walker.nextNode())texts.push(walker.currentNode);const value=texts.map(n=>n.data).join('');const offset=value.indexOf(data.quote);
   if(offset>=0){let cursor=0,start=null,end=null;for(const text of texts){if(start===null&&offset<cursor+text.length)start=[text,offset-cursor];if(offset+data.quote.length<=cursor+text.length){end=[text,offset+data.quote.length-cursor];break;}cursor+=text.length;}
    if(start&&end){const range=document.createRange();range.setStart(...start);range.setEnd(...end);CSS.highlights.set('source-evidence',new Highlight(range));exact=true;}
   }
  }
  target.scrollIntoView({block:'center',behavior:'smooth'});notify('labwise:locate-result',{found:true,message:exact?'已定位并标出 Word 原文证据句段。':'已定位到 Word 原文段落。'});
 }
 else notify('labwise:locate-result',{found:false,message:'此处无法唯一定位，请核对原 Word；未使用相似文字替代。'});
}
window.addEventListener('message',e=>{if(e.origin!==location.origin||e.source!==parent)return;if(e.data?.type==='labwise:locate')locate(e.data);if(e.data?.type==='labwise:review-marks')paint(e.data.findings||[],e.data.reviews||{});});
document.addEventListener('selectionchange',()=>{
 const s=window.getSelection(),quote=s?.toString().trim();let node=s?.anchorNode?.parentElement?.closest('[data-paragraph-id]');const end=s?.focusNode?.parentElement?.closest('[data-paragraph-id]');
 selection=quote&&quote.length<=4000&&node===end&&node?.dataset.paragraphId?{quote,paragraph_id:node.dataset.paragraphId,page:1}:null;
 $('addComment').disabled=!selection;
});
$('addComment').onclick=()=>{if(selection)notify('labwise:add-annotation',selection);};
$('downloadWord').onclick=async()=>{try{const source=await api('reports/'+id+'/source');const bytes=Uint8Array.from(atob(source.file),c=>c.charCodeAt(0));const url=URL.createObjectURL(new Blob([bytes],{type:'application/vnd.openxmlformats-officedocument.wordprocessingml.document'}));const a=document.createElement('a');a.href=url;a.download=source.filename;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}catch(e){$('status').textContent=e.message;}};
(async()=>{try{
 model=await api('reports/'+encodeURIComponent(id)+'/word-view');const doc=new DOMParser().parseFromString(model.html,'text/html');const page=doc.querySelector('.page');$('document').append(document.adoptNode(page));
 for(const obj of model.objects){if(obj.kind!=='chart')continue;const target=document.querySelector('[data-word-index="'+obj.paragraph_index+'"]');if(target){const label=document.createElement('div');label.className='object-note';label.textContent='Word 原生图表 '+obj.id.replace(/^v/,'')+' · 数据缓存：'+(obj.chart_text||'无法读取')+'。完整图表版式请在原 Word 核对。';target.append(label);}}
 const limit=document.createElement('p');limit.className='word-limit';limit.textContent='Word 阅读视图保留原文与表格、图片定位；分页和复杂版式可能与 Word 有差异。原 Word 文件保持不变。';$('document').prepend(limit);
 paint(model.findings||[],model.reviews||{});$('status').textContent='点击建议定位原段落';notify('labwise:reader-ready');
}catch(e){$('status').textContent=e.message;}})();
