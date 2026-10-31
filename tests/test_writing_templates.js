'use strict';
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const profiles=JSON.parse(fs.readFileSync('corpus/writing_profiles.json','utf8')).profiles;
const elements=new Map();
function element(){return {value:'',disabled:true,textContent:'',children:[],append(...x){this.children.push(...x);},replaceChildren(...x){this.children=x;}};}
const $=id=>{if(!elements.has(id))elements.set(id,element());return elements.get(id);};
$('assignmentType').value='实验报告';
let allowReplace=false,inspections=0,edits=0;
const sandbox={$,api:async()=>({profiles}),node:(tag,cls,text)=>({...element(),textContent:text}),
 safeAction:fn=>fn,assignmentEditor:{sequence:0},submissionImport:{running:false},
 window:{confirm:()=>allowReplace},clearTimeout,assignmentEdited:()=>edits++,
 inspectRubric:async()=>inspections++,message:()=>{}};
vm.createContext(sandbox);
sandbox.uiT=(text,...values)=>typeof text==='string'?text:text.reduce((s,part,i)=>s+part+(i<values.length?values[i]:''),'');
vm.runInContext(fs.readFileSync('assignment-editor.js','utf8').split('// Catalog selection is a preview.')[1].split('\n').slice(1).join('\n'),sandbox);
(async()=>{
 await sandbox.initWritingProfiles();
 assert.equal($('writingTemplate').children.length,8);
 $('instructions').value='Teacher requirements';$('rubricSource').value='Teacher rubric';
 $('writingTemplate').value='academic_essay';$('writingTemplate').onchange();
 assert.equal($('instructions').value,'Teacher requirements');
 assert.equal($('rubricSource').value,'Teacher rubric');
 await $('applyWritingTemplate').onclick();
 assert.equal($('rubricSource').value,'Teacher rubric');assert.equal(edits,0);
 allowReplace=true;await $('applyWritingTemplate').onclick();
 assert.equal($('assignmentType').value,'学术议论文／课程论文');
 assert.ok($('rubricSource').value.includes('中心论点（25分）'));
 assert.ok(!$('rubricSource').value.includes('实验方法'));
 assert.equal(edits,1);assert.equal(inspections,1);
 $('assignmentType').value='自定义随笔';sandbox.syncWritingTemplate();
 assert.equal($('writingTemplate').value,'general_writing');
 sandbox.assignmentEditor.saving=true;
 await assert.rejects($('applyWritingTemplate').onclick(),/等待/);
 assert.equal(edits,1);
 console.log('Eight genre choices, preview preservation, cancelled replacement, explicit application, custom-type fallback and busy-state protection passed.');
})().catch(error=>{console.error(error);process.exitCode=1;});
