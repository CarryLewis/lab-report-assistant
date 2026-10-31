'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
function setup({saved,query='',storageBlocked=false,parentLocale}={}){
 const writes=[],navigations=[],events={},texts=[{data:'工作台',parentElement:{closest:()=>null}}];
 const attributes={placeholder:'搜索章节、分论点…'};
 const placeholder={hasAttribute:key=>key in attributes,getAttribute:key=>attributes[key],setAttribute:(key,value)=>attributes[key]=value};
 const actions={prepend(label){this.label=label;}};
 function element(){return {children:[],append(...items){this.children.push(...items);},setAttribute(){},addEventListener(name,fn){events[name]=fn;}};}
 let cursor=0;
 const document={documentElement:{},getElementById:()=>null,createElement:element,createTreeWalker(){cursor=0;return {nextNode(){this.currentNode=texts[cursor++];return !!this.currentNode;}};},querySelector:()=>actions,querySelectorAll:selector=>selector==='[title],[aria-label],[placeholder]'?[placeholder]:[]};
 const context=vm.createContext({document,NodeFilter:{SHOW_TEXT:4,FILTER_ACCEPT:1,FILTER_REJECT:2},URL,URLSearchParams,location:{search:query,href:'http://localhost/'+query,replace:url=>navigations.push(url)},localStorage:{getItem(){if(storageBlocked)throw Error('blocked');return saved;},setItem(key,value){if(storageBlocked)throw Error('blocked');writes.push([key,value]);}},state:{dirty:false},submissionImport:{running:false},assignmentEditor:{dirty:false},protectChange:()=>true,message(){},parent:parentLocale?{LabwiseI18n:{locale:parentLocale}}:null});
 context.window=context;if(!parentLocale)context.parent=context;
 vm.runInContext(fs.readFileSync('i18n-en.js','utf8'),context);vm.runInContext(fs.readFileSync('i18n.js','utf8'),context);
 return {context,t:context.LabwiseI18n.t,document,actions,events,writes,navigations,texts,attributes};
}
const zh=setup();assert.equal(zh.t('工作台'),'工作台');assert.equal(zh.context.LabwiseI18n.locale,'zh-CN');
const en=setup({saved:'en'});assert.equal(en.t('工作台'),'Dashboard');assert.equal(en.document.documentElement.lang,'en');
const data='教师输入：工作台与中文原稿';assert.equal(en.t(['原文批注', ''],data),'Source annotations'+data,'template expressions must retain teacher data');
assert.equal(en.t('<button title="关闭">保存草稿</button>'),'<button title="Close">Save draft</button>');
en.context.LabwiseI18n.mount();assert.equal(en.texts[0].data,'Dashboard');assert.equal(en.attributes.placeholder,'Search sections or claims…');
const select=en.actions.label.children[0];select.value='zh-CN';en.context.protectChange=()=>false;en.events.change();assert.equal(en.navigations.length,0,'cancelled dirty guard must not navigate');assert.equal(en.writes.length,0);
en.context.protectChange=()=>true;en.context.state.busy=true;select.value='zh-CN';en.events.change();assert.equal(en.navigations.length,0,'busy work must block language changes');
en.context.state.busy=false;select.value='zh-CN';en.events.change();assert.equal(en.writes[0][1],'zh-CN');assert.match(en.navigations[0],/lang=zh-CN/);
const blocked=setup({storageBlocked:true,query:'?lang=en'});assert.equal(blocked.t('保存草稿'),'Save draft');
const frame=setup({saved:'zh-CN',parentLocale:'en'});assert.equal(frame.t('添加批注'),'Add annotation');
assert.equal(setup({saved:'en',query:'?lang=unknown'}).t('导出反馈'),'Export feedback');
assert.equal(en.t('未翻译的原文内容'),'未翻译的原文内容');
assert.equal(en.t(['',''],'工作台'),'工作台','data matching a UI key must also remain unchanged');
// Exercise real dynamic rendering code, in addition to the translation helpers.
en.context.uiT=en.t;
const reviewSource=fs.readFileSync('teacher-live.js','utf8');
vm.runInContext(reviewSource.slice(reviewSource.indexOf('const gradingNames='),reviewSource.indexOf('function node(')),en.context);
assert.equal(vm.runInContext('statusNames.queued',en.context),'Queued');
assert.equal(vm.runInContext('gradingNames.completed',en.context),'Completed');
const pdfSource=fs.readFileSync('pdf-export.js','utf8');
const htmlStart=pdfSource.indexOf('dialog.innerHTML=')+'dialog.innerHTML='.length;
const htmlEnd=pdfSource.indexOf(';\n document.body.append',htmlStart);
const exportMarkup=vm.runInContext(pdfSource.slice(htmlStart,htmlEnd),en.context);
assert.match(exportMarkup,/Export review PDF/);
assert.match(exportMarkup,/Include teacher source annotations/);
assert.ok(!/[\u3400-\u9fff]/.test(exportMarkup),'PDF dialog UI must be fully English');

console.log('UI languages, safe interpolation, static labels, persistence, reader inheritance, blocked storage and unsaved/busy guards passed.');
