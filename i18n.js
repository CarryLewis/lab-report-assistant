/* UI language is independent of report content, rubric snapshots and AI output. */
(() => {
 'use strict';
 const key='labwise.ui.language';
 let saved=null,parentLanguage=null;
 try{saved=localStorage.getItem(key);}catch{/* A query parameter still supports this session. */}
 try{if(parent!==window)parentLanguage=parent.LabwiseI18n?.locale;}catch{/* Standalone readers work too. */}
 const requested=new URLSearchParams(location.search).get('lang');
 const locale=[requested,parentLanguage,saved].find(value=>['en','zh-CN'].includes(value))||'zh-CN';
 document.documentElement.lang=locale;
 const dictionary=globalThis.LabwiseEnglish||{};
 function translate(value){
  const text=String(value??'');if(locale!=='en')return text;
  if(Object.hasOwn(dictionary,text))return dictionary[text];
  const trimmed=text.trim();
  if(trimmed&&Object.hasOwn(dictionary,trimmed))return text.slice(0,text.indexOf(trimmed))+dictionary[trimmed]+text.slice(text.indexOf(trimmed)+trimmed.length);
  return text;
 }
 function html(source){
  // Only called for application-authored HTML literals, before interpolating data.
  return source.replace(/\b(aria-label|title|placeholder)="([^"]*)"/g,(_,name,value)=>name+'="'+translate(value).replace(/&/g,'&amp;').replace(/"/g,'&quot;')+'"')
   .replace(/>([^<>]+)</g,(_,value)=>'>'+translate(value)+'<');
 }
 function chunk(value){return /<[a-z][a-z0-9-]*(?:\s|>)/i.test(value)?html(value):translate(value);}
 function t(text,...values){
  if(typeof text==='string')return chunk(text);
  return text.reduce((result,part,index)=>result+chunk(part)+(index<values.length?values[index]:''),'');
 }
 function translateStatic(){
  // Run once before application scripts render any imported or teacher-authored data.
  const walker=document.createTreeWalker(document.documentElement,NodeFilter.SHOW_TEXT,{acceptNode:n=>n.parentElement.closest('script,style,textarea,[data-no-i18n]')?NodeFilter.FILTER_REJECT:NodeFilter.FILTER_ACCEPT});
  const nodes=[];while(walker.nextNode())nodes.push(walker.currentNode);
  for(const node of nodes)node.data=translate(node.data);
  for(const element of document.querySelectorAll('[title],[aria-label],[placeholder]'))for(const attr of ['title','aria-label','placeholder'])if(element.hasAttribute(attr))element.setAttribute(attr,translate(element.getAttribute(attr)));
  // Datalist values are built-in choices, not saved assignment values.
  const defaultGenre=document.getElementById('assignmentType');
  if(defaultGenre&&locale==='en')defaultGenre.defaultValue=defaultGenre.value=translate(defaultGenre.defaultValue);
  if(locale==='en')for(const option of document.querySelectorAll('#assignmentTypes option'))option.value=translate(option.value);
 }
 function mount(){
  translateStatic();
  const actions=document.querySelector('.top-actions');if(!actions)return;
  const label=document.createElement('label');label.className='ui-language';label.textContent='语言 / Language ';
  const select=document.createElement('select');select.id='uiLanguage';select.setAttribute('aria-label','界面语言 / Interface language');
  for(const [value,text]of [['zh-CN','中文'],['en','English']]){const option=document.createElement('option');option.value=value;option.textContent=text;select.append(option);}select.value=locale;label.append(select);actions.prepend(label);
  select.addEventListener('change',()=>{
   const next=select.value;select.value=locale;
   if(typeof state!=='undefined'&&(state.busy||state.uploading||state.saving||state.navigating||submissionImport.running||assignmentEditor.loading||assignmentEditor.saving)){message(t('请等待当前操作完成。'));return;}
   if(typeof protectChange==='function'&&!protectChange())return;
   // protectChange has asked about unsaved edits. Avoid a second unload prompt.
   if(typeof state!=='undefined')state.dirty=false;
   if(typeof assignmentEditor!=='undefined')assignmentEditor.dirty=false;
   try{localStorage.setItem(key,next);}catch{/* URL fallback below. */}
   const url=new URL(location.href);url.searchParams.set('lang',next);location.replace(url.href);
  });
 }
 globalThis.LabwiseI18n={locale,t,translateStatic,mount};
})();
