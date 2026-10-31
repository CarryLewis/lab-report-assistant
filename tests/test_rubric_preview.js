'use strict';
const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
function element(){return {value:'',textContent:'',dataset:{},children:[],disabled:false,hidden:false,classList:{add(){},remove(){},toggle(){}},setAttribute(k,v){this[k]=v;},append(...x){this.children.push(...x);},replaceChildren(...x){this.children=x;},checkValidity(){return true;}};}
function setup(mode='ai'){
 const nodes={},calls=[],$=id=>nodes[id]??=element();$('rubricProcessingMode').value=mode;$('assignmentType').value='实验报告';
 const source='方法（30分）\n结果（70分）';
 const result={source_text:source,criteria:[{id:'m',name:'方法',maximum_points:30,descriptor:''},{id:'r',name:'结果',maximum_points:70,descriptor:''}],total:100,ready:true,messages:[]};
 const c=vm.createContext({$,node:(tag,cls,text)=>({...element(),tag,className:cls,textContent:text}),structuredClone,setTimeout,clearTimeout,Uint8Array,btoa,message(){},window:{confirm:()=>true},submissionImport:{running:false}});
 c.api=async(path,body)=>{calls.push({path,body,stage:$('rubricPreviewPanel').dataset.state});return body.extract_only?{source_text:source}:structuredClone(result);};
 vm.runInContext(fs.readFileSync('assignment-editor.js','utf8').split('function initAssignmentEditor()')[0],c);
 return {c,$,calls,source,result};
}
const file={name:'rubric.docx',size:4,arrayBuffer:async()=>new Uint8Array([1,2,3,4]).buffer};
(async()=>{
 for(const mode of ['ai','code']){
  const {c,$,calls,source}=setup(mode);c.file=file;
  await vm.runInContext('importRubricDocument(file)',c);
  assert.deepEqual(calls.map(x=>x.path),['rubric-import',mode==='ai'?'rubric-understand':'rubric-import']);
  assert.equal(calls[0].stage,'reading');assert.equal(calls[1].stage,'analyzing');
  assert.equal($('rubricPreviewPanel').hidden,false);assert.equal($('rubricPreviewPanel').dataset.state,'ready');
  assert.equal($('rubricSource').value,source);assert.equal($('rubricSource').disabled,false);
  const criterion=$('rubricPreview').children.find(x=>x.className==='criterion-preview');
  const name=criterion.children[0].children[0];name.value='教师修正';name.onchange();
  assert.equal(vm.runInContext('assignmentEditor.understanding.criteria[0].name',c),'教师修正');
  if(mode==='ai')assert.equal($('rubricSource').value,source,'AI preview edits preserve original text');
 }
 const {c,$,source}=setup();c.file=file;let count=0;c.api=async()=>{if(count++===0)return {source_text:source};throw Error('模型未连接');};
 await assert.rejects(vm.runInContext('importRubricDocument(file)',c),/模型未连接/);
 assert.equal($('rubricPreviewPanel').dataset.state,'error');assert.equal($('rubricSource').value,source);
 assert.equal($('understandRubric').disabled,false);assert.equal(vm.runInContext('assignmentEditor.ready',c),false);
 assert.equal($('rubricPreview').children.at(-1).textContent,source,'failure leaves original visible beside the input');
 console.log('Word import auto-preview for both modes, reading/processing states, editable results, original preservation and recoverable AI failure passed.');
})().catch(e=>{console.error(e);process.exitCode=1;});
