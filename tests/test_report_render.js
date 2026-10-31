const fs=require('fs'),vm=require('vm');
const assert=require('node:assert/strict');
const base={id:'fixture',filename:'fictional.docx',status:'ready',revision:1,updated:'2026-10-29',scores:{},reviews:{},
 assignment:{title:'Fixture',rubric:{name:'Fixture',version:'1',processing_mode:'code',criteria:[{id:'c',name:'Criterion',maximum_points:10}]}},
 paragraphs:[{id:'p1',text:'Introduction',heading:true},{id:'p2',text:'Evidence in the report.'}],
 analysis:{mode:'deepseek',generated:'2026-10-29',outline:[],claims:[],findings:[{id:'1',criterion_id:'c',kind:'strength',title:'Evidence',paragraph_ids:['p2'],quote:'Evidence',feedback:'Feedback',rationale:'Reason'}],coverage:{objects:[],warnings:[]},visual_checks:[]}};
const records=[base,{...structuredClone(base),id:'failed',status:'failed',analysis:null,error:'Analysis failed'}];

for(const legacy of [false,true]){const js='teacher-live.js',name=legacy?'Legacy DOM without AI panel':'Current DOM';
 const src=fs.readFileSync(js,'utf8'),markup=fs.readFileSync('index.html','utf8').replace(legacy?'id=\"aiScoreSuggestions\"':'__no_match__','id=\"legacyAIScores\"');
 for(const r of records){
 const ids=new Set([...markup.matchAll(/\bid="([^"]+)"/g)].map(x=>x[1])),els={};
 const el=()=>({value:'',children:[],dataset:{},style:{setProperty(){}},classList:{add(){},remove(){},toggle(){}},append(...x){this.children.push(...x)},replaceChildren(...x){this.children=x},setAttribute(){},querySelectorAll(){return []}});
 const ctx=vm.createContext({window:{},$:id=>ids.has(id)?els[id]??=el():null,node:()=>el(),state:{report:null},structuredClone,statusNames:{ready:'ready'},rubricMethodLabel:()=>'',clearOriginalPreview(){},renderProcessingNotice(){},total(){},applyPreferences(){},renderReviewSequence(){},renderAnnotations(){},safeAction:fn=>fn,clearLinks(){},link(){},showOriginal(){},document:{},uiT:(t,...v)=>typeof t==='string'?t:t.reduce((s,p,i)=>s+p+(v[i]??''),'')});
 let region=src.slice(src.indexOf('/* BEGIN DOCUMENT OUTLINE */'),src.indexOf('/* END DOCUMENT OUTLINE */'));
 vm.runInContext(region,ctx);ctx.LabwiseOutline=ctx.window.LabwiseOutline;
 const extract=(begin,end)=>vm.runInContext(src.slice(src.indexOf(begin),src.indexOf(end)),ctx);
 try{
 if(src.includes('function renderAIScores'))extract('function renderAIScores','function renderReport');
 extract('function renderReport',"\n$('outlineSearch').oninput");
 extract('function renderFindings','async function reveal');
 extract('function renderWordCoverage','function downloadBase64Package');
 ctx.record=r;vm.runInContext('renderReport(record)',ctx);console.log(name,r.status,'render succeeded');
 }catch(e){assert.fail(name+' '+r.status+': '+e.stack);}
 }
}
