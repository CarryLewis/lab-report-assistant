const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync('teacher-live.js','utf8');const context=vm.createContext({window:{}});
vm.runInContext(source.split('/* BEGIN DOCUMENT OUTLINE */')[1].split('/* END DOCUMENT OUTLINE */')[0],context);
const {build,markdown}=context.window.LabwiseOutline;
const r={filename:'test.pdf',paragraphs:[
 {id:'p1',text:'Testing two diagnostic methods in a fictional experiment'},
 {id:'p2',text:'1. Introduction'},{id:'p3',text:'1.1 Aim'},{id:'p4',text:'Compare two diagnostic methods.'},
 {id:'p5',text:'1.2 Background'},{id:'p6',text:'Method A is convenient.'},
 {id:'p7',text:'2. Methods'},{id:'p8',text:'2.1 Sampling'},{id:'p9',text:'A sample was collected.'},
 {id:'p10',text:'2.2 Staining'},{id:'p11',text:'2.2.1 Preparation'},{id:'p12',text:'The sample was stained.'}],
 analysis:{outline:[],claims:[
 {title:'Compare diagnostic performance',paragraph_ids:['p4']},
 {title:'A convenient method',paragraph_ids:['p6']},
 {title:'Sampling and staining process',paragraph_ids:['p9','p12']}],findings:[{title:'Criticism must not be a table of contents entry'}]}};
const tree=build(r);
assert.equal(tree.sections,7);assert.equal(tree.claims,3);assert.equal(tree.children.length,2);
assert.equal(tree.children[0].children[0].children[0].title,'Compare diagnostic performance');
assert.equal(tree.children[1].children.at(-1).title,'Sampling and staining process'); // Spans subsections: attach at common parent.
assert.equal(tree.children[1].children[1].children[0].title,'2.2.1 Preparation');
const md=markdown(tree);assert.ok(md.includes('### 1.1 Aim\n- Compare diagnostic performance'));assert.ok(!md.includes('Criticism'));assert.ok(md.indexOf('- Sampling and staining process')>md.indexOf('## 2. Methods'));assert.ok(md.indexOf('- Sampling and staining process')<md.indexOf('### 2.1 Sampling'));
r.map_edits={'outline:p3':'Research objective','claims:p4':'Edited claim'};assert.equal(build(r).children[0].children[0].title,'Research objective');assert.ok(markdown(build(r)).includes('Edited claim'));
const flat=build({filename:'no-headings.pdf',paragraphs:[{id:'p1',text:'An ordinary opening sentence.'},{id:'p2',text:'Another paragraph.'}],analysis:{outline:[{title:'Overview',paragraph_ids:['p1']}],claims:[{title:'A real point',paragraph_ids:['p2']},{title:'Bad reference',paragraph_ids:['missing']}]}});
assert.equal(flat.sections,1);assert.equal(flat.claims,1);assert.equal(flat.children[0].children[0].title,'A real point');
assert.equal(context.window.LabwiseOutline.heading({text:'180 minutes'}),null);assert.equal(context.window.LabwiseOutline.heading({text:'0.10'}),null);assert.equal(context.window.LabwiseOutline.heading({text:'0.53'}),null);
assert.equal(build({filename:'empty.pdf',paragraphs:[]}).sections,0);
console.log('Document heading hierarchy, common-parent arguments, Markdown, edits and invalid-reference handling passed.');
