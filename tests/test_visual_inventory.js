const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const els={};function element(id){return els[id]??={id,hidden:false,disabled:false,dataset:{},children:[],value:'',addEventListener(){},append(...x){this.children.push(...x)},replaceChildren(...x){this.children=x},setAttribute(){},close(){this.closed=true}};}
['discoverVisuals','pauseVisualScan','rescanVisuals','retryVisualScan','saveVisualCandidate','closeVisualCapture','visualCaptureDialog','startVisualReview','visualInventory','visualScanProgress','visualCoverageList','visualPageCoverage','visualObjectList'].forEach(element);
let calls=[],saved=0,rendered=0,paused=false;
const state={report:{id:'r',revision:1,source_sha256:'source',visual_objects:[]},dirty:true};
const context=vm.createContext({$:element,state,node:(tag,cls,text)=>Object.assign(element('n'+Math.random()),{textContent:text}),safeAction:fn=>fn,save:async()=>{saved++;state.dirty=false},document:{querySelectorAll:()=>[]},visualCapture:{report_id:'r',source_sha256:'source',page:1,bbox:[.1,.1,.8,.8]},message(){},showOriginal:async()=>{},sendAnchor(){},pendingAnchor:null,
api:async(path,body)=>{calls.push({path,body});const r=structuredClone(state.report);r.revision++;
 if(path.endsWith('/visual-scan'))r.visual_scan={id:'j',status:'running',processed:0,page_count:2,pages:[{page:1,state:'pending'},{page:2,state:'pending'}]};
 if(path.endsWith('/visual-scan-next')){r.visual_scan.processed++;r.visual_scan.pages[r.visual_scan.processed-1].state='no_candidates';if(paused)vm.runInContext('inventoryPause=true',context);else if(r.visual_scan.processed===2)r.visual_scan.status='completed';}
 if(path.endsWith('/visual-scan-cancel'))r.visual_scan.status='cancelled';
 return r;},renderReport:r=>{state.report=r;rendered++;vm.runInContext('renderVisualInventory()',context);}});
vm.runInContext(fs.readFileSync('visual-inventory.js','utf8'),context);
(async()=>{
 await vm.runInContext('beginVisualScan()',context);assert.equal(saved,1);assert.equal(state.report.visual_scan.processed,2);assert.equal(state.busy,false);assert.match(els.visualScanProgress.textContent,/未执行 AI/);
 assert.deepEqual(calls.map(x=>x.body.revision),[1,2,3]);
 paused=true;calls=[];await vm.runInContext('beginVisualScan(true)',context);assert.equal(state.report.visual_scan.status,'cancelled');assert.equal(calls.at(-1).path,'reports/r/visual-scan-cancel');assert.equal(state.busy,false);
 const obj={id:'o',page:1,bbox:[0,0,1,1],source_sha256:'source'};context.obj=obj;await vm.runInContext('inventoryLocate(obj,true)',context);assert.equal(context.pendingAnchor.type,'labwise:capture-visual');assert.equal(vm.runInContext('inventoryEditId',context),'o');
 await els.saveVisualCandidate.onclick();assert.equal(calls.at(-1).body.id,'o');assert.equal(els.visualCaptureDialog.closed,true);
 context.obj.source_sha256='stale';await assert.rejects(vm.runInContext('inventoryLocate(obj)',context),/旧版/);
 console.log('Inventory scan sequencing, pause, local candidate save, and source-version guards passed.');
})().catch(e=>{console.error(e);process.exitCode=1});
