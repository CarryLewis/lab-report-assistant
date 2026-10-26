const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const elements={},listeners={},sent=[];
function element(id){return elements[id]??=({id,hidden:false,children:[],contentWindow:{postMessage:d=>sent.push(d)},classList:{add(){},toggle(){}},setAttribute(){},replaceChildren(...children){this.children=children;},append(...children){for(const child of children){this.children.push(child);if(child.id)elements[child.id]=child;}},prepend(child){this.append(child);},remove(){delete elements[this.id];}});}
['sourceScroll','showOriginal','originalAnnotations','startVisualReview','closeVisualCapture','runVisualReview'].forEach(element);
let calls=0,fail=false,pending=null;
const context=vm.createContext({$:id=>elements[id],safeAction:fn=>fn,node:(tag,cls,text)=>Object.assign(element('tmp'+Math.random()),{textContent:text}),state:{report:{id:'report-a'}},window:{addEventListener:(type,fn)=>{listeners[type]=fn;}},location:{origin:'http://localhost'},URL:{createObjectURL:()=> 'blob:http://localhost/test',revokeObjectURL(){}},Blob,Uint8Array,atob,encodeURIComponent,api:async()=>{calls++;if(fail)throw Error('原件缺失');if(pending)return new Promise(resolve=>{pending=resolve;});return {filename:'report.pdf',file:Buffer.from('%PDF-test').toString('base64')};}});
const source=fs.readFileSync('teacher-live.js','utf8');vm.runInContext(source.slice(source.indexOf('let originalURL=null,')),context);
(async()=>{
 assert.ok(!source.includes('showExtracted'));assert.ok(!fs.readFileSync('index.html','utf8').includes('id="showExtracted"'));
 await vm.runInContext('showOriginal()',context);const reader=elements.originalFrame;assert.ok(reader.src.startsWith('/original-reader.html?'));
 await vm.runInContext('showOriginal()',context);assert.equal(elements.originalFrame,reader);assert.equal(calls,1);
 vm.runInContext("pendingAnchor={type:'labwise:locate',quote:'Evidence'}",context);listeners.message({origin:'http://evil',source:reader.contentWindow,data:{type:'labwise:reader-ready'}});assert.equal(sent.length,0);
 listeners.message({origin:'http://localhost',source:reader.contentWindow,data:{type:'labwise:reader-ready'}});assert.equal(sent[0].quote,'Evidence');
 vm.runInContext('clearOriginalPreview()',context);fail=true;await vm.runInContext('showOriginal()',context);assert.equal(elements.originalFrame,undefined);assert.ok(elements.originalNotice.children[0].textContent.includes('原件缺失'));
 fail=false;pending=true;const loading=vm.runInContext('showOriginal()',context);vm.runInContext('clearOriginalPreview()',context);pending({filename:'report.pdf',file:Buffer.from('%PDF-test').toString('base64')});await loading;assert.equal(elements.originalFrame,undefined);
 console.log('Original-only preview, reuse, trusted anchoring, error and cancellation passed.');
})().catch(e=>{console.error(e);process.exitCode=1;});
