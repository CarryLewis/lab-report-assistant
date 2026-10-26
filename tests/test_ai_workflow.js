const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync('teacher-live.js','utf8'),nodes={};
const state={section:'workspace',busy:false,saving:false,uploading:false,dirty:false,bootstrap:{},report:{id:'test',revision:1,notes:'Teacher note'}};
let latest={id:'test',revision:2,status:'ready',notes:'Teacher note',analysis:{mode:'deepseek',findings:[{},{}]}},rendered=0;
const context=vm.createContext({$:id=>nodes[id]??={textContent:''},state,statusNames:{ready:'AI 结果就绪'},document:{hidden:false},submissionImport:{running:false},assignmentEditor:{id:null},setInterval(){},drawReportList(){},renderMetrics(){},drawSavedSubmissions(){},api:async path=>path==='bootstrap'?{}:structuredClone(latest),renderReport:r=>{state.report=r;rendered++;}});
vm.runInContext(source.slice(source.indexOf('function analysisNotice'),source.indexOf('function openTeacherSection')),context);
(async()=>{
 await vm.runInContext('pollAutomaticResults()',context);assert.equal(rendered,1);assert.equal(state.report.revision,2);
 state.dirty=true;latest.revision=3;await vm.runInContext('pollAutomaticResults()',context);assert.equal(rendered,1);assert.equal(state.report.revision,2);assert.match(nodes.workNotice.textContent,/先保存当前修改/);
 state.dirty=false;state.busy=true;await vm.runInContext('pollAutomaticResults()',context);assert.equal(rendered,1,'Local discovery owns the UI while scanning');
 state.busy=false;await vm.runInContext('pollAutomaticResults()',context);assert.equal(rendered,2);assert.equal(state.report.revision,3);
 context.waiting={status:'waiting_key'};assert.match(vm.runInContext('analysisNotice(waiting)',context),/等待 AI/);
 console.log('Automatic AI result polling preserves teacher drafts and defers rendering during local discovery.');
})().catch(e=>{console.error(e);process.exitCode=1});
