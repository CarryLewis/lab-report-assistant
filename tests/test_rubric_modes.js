'use strict';
const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const elements=new Map(),calls=[];
function element(){return {dataset:{},setAttribute(){},value:'',textContent:'',disabled:false,hidden:false,children:[],classList:{add(){},remove(){},toggle(){}},append(...x){this.children.push(...x);},replaceChildren(...x){this.children=x;}};}
const $=id=>{if(!elements.has(id))elements.set(id,element());return elements.get(id);};
$('rubricProcessingMode').value='ai';$('rubricSource').value='方法30分，结果70分';$('assignmentType').value='实验报告';
let pending;
const result={criteria:[{id:'a',name:'方法',maximum_points:30}],total:30,ready:true,messages:[],source_text:$('rubricSource').value};
const context=vm.createContext({$,node:(tag,cls,text)=>({...element(),textContent:text}),structuredClone,clearTimeout,setTimeout,submissionImport:{running:false},message(){},window:{confirm:()=>true},api:async(path,body)=>{calls.push(path);if(pending)return pending;return {...structuredClone(result),processing_mode:path==='rubric-import'?'code':'ai'};}});
const source=fs.readFileSync('assignment-editor.js','utf8');
vm.runInContext(source.slice(0,source.indexOf('function initAssignmentEditor()')),context);
vm.runInContext('showRubricPreview=p=>{assignmentEditor.ready=p.ready;}',context);
(async()=>{
 await vm.runInContext('inspectRubric()',context);assert.equal(calls.length,0,'typing AI text never makes a request');
 await vm.runInContext('inspectRubric(true)',context);assert.deepEqual(calls,['rubric-understand']);
 await vm.runInContext('inspectRubric()',context);assert.equal(calls.length,1,'save/reopen uses cached understanding');
 vm.runInContext('syncRubricMode()',context);$('rubricProcessingMode').value='code';vm.runInContext('switchRubricMode()',context);await new Promise(r=>setImmediate(r));
 assert.equal(calls.at(-1),'rubric-import');
 $('rubricProcessingMode').value='ai';vm.runInContext('switchRubricMode()',context);assert.equal(calls.length,2,'switching back restores AI cache');
 let finish;pending=new Promise(r=>finish=r);
 const work=vm.runInContext('inspectRubric(true)',context);$('rubricSource').value='修改后的原文';vm.runInContext('invalidateRubric()',context);finish(structuredClone(result));await work;pending=null;
 assert.equal(vm.runInContext('assignmentEditor.understanding',context),null,'stale model result must not replace changed input');
 // Candidate-score adoption leaves existing teacher entries intact.
 const inputs=[{dataset:{id:'a'},value:'11'},{dataset:{id:'b'},value:''},{dataset:{id:'c'},value:''}];
 $('scores').querySelectorAll=()=>inputs;
 context.state={report:{assignment:{rubric:{processing_mode:'ai',criteria:[{id:'a',name:'A',maximum_points:30},{id:'b',name:'B',maximum_points:30},{id:'c',name:'C',maximum_points:40}]}},analysis:{score_suggestions:[{criterion_id:'a',score:24},{criterion_id:'b',score:20},{criterion_id:'c',score:null}]}}};
 context.node=(tag,cls,text)=>({...element(),textContent:text});context.dirty=()=>{};context.total=()=>{};context.safeAction=fn=>fn;
 const review=fs.readFileSync('teacher-live.js','utf8');vm.runInContext(review.slice(review.indexOf('function applyAIScore'),review.indexOf('function renderReport')),context);
 vm.runInContext('renderAIScores()',context);const fill=$('aiScoreSuggestions').children.find(x=>x.textContent==='将建议填入空白评分');fill.onclick();
 assert.equal(inputs[0].value,'11');assert.equal(inputs[1].value,20);assert.equal(inputs[2].value,'');
 context.state.report.assignment.rubric.criteria[0].evaluation_maximum=100;
 Object.assign(context.state.report.analysis.score_suggestions[0],{raw_base_score:80,base_score:24});
 vm.runInContext('renderAIScores()',context);
 const conversion=$('aiScoreSuggestions').children.flatMap(x=>x.children||[]).find(x=>(x.textContent||'').includes('原始评价：80 / 100'));
 assert.ok(conversion);assert.ok(conversion.textContent.includes('折算基础分：24 / 30'));
 console.log('Dual mode routing/cache, no implicit AI calls, stale-result rejection, teacher-score preservation and unknown-score handling passed.');
})().catch(e=>{console.error(e);process.exitCode=1;});
