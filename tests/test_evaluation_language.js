'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync('teacher-live.js','utf8'),html=fs.readFileSync('index.html','utf8');
const nodes={saveEvaluationLanguage:{disabled:false},evaluationLanguage:{value:'en'},evaluationLanguageStatus:{textContent:''}};
const calls=[],state={bootstrap:{settings:{model:'deepseek-flash',evaluation_language:'zh-CN'}}};
let reject=false;
const context=vm.createContext({$:id=>nodes[id],state,uiT:s=>s,api:async(path,body)=>{
 calls.push({path,body});if(reject)throw Error('Save failed');return body;
}});
vm.runInContext(source.slice(source.indexOf('async function saveEvaluationLanguage'),source.indexOf("$('evaluationLanguageForm').onsubmit")),context);
(async()=>{
 await context.saveEvaluationLanguage({preventDefault(){}});
 assert.equal(calls[0].path,'evaluation-language');
 assert.equal(calls[0].body.evaluation_language,'en');
 assert.equal(Object.keys(calls[0].body).length,1,'No key or model is required');
 assert.equal(state.bootstrap.settings.evaluation_language,'en');
 assert.equal(nodes.saveEvaluationLanguage.disabled,false);
 reject=true;nodes.evaluationLanguage.value='ja';
 await context.saveEvaluationLanguage({preventDefault(){}});
 assert.equal(state.bootstrap.settings.evaluation_language,'en','Failed save keeps saved setting');
 assert.equal(nodes.evaluationLanguageStatus.textContent,'Save failed');
 assert.equal(nodes.saveEvaluationLanguage.disabled,false);
 assert.match(html,/<form id="evaluationLanguageForm"/);
 assert.match(html,/aria-describedby="evaluationLanguageHelp"/);
 assert.match(source,/evaluationLanguage'\).value=data.settings.evaluation_language\|\|'zh-CN'/);
 console.log('Independent evaluation language save, error recovery and setting hydration passed.');
})().catch(error=>{console.error(error);process.exitCode=1;});
