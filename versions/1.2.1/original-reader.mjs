import {getDocument,GlobalWorkerOptions} from '/vendor/pdfjs/pdf.mjs';
import {PDFViewer,EventBus,PDFLinkService,PDFFindController} from '/vendor/pdfjs/pdf_viewer.mjs';
GlobalWorkerOptions.workerSrc='/vendor/pdfjs/pdf.worker.mjs';
const $=id=>document.getElementById(id),eventBus=new EventBus();
const links=new PDFLinkService({eventBus});
const findController=new PDFFindController({eventBus,linkService:links});
const measureToolbar=()=>document.documentElement.style.setProperty('--reader-toolbar-height',$('tools').getBoundingClientRect().height+'px');
measureToolbar();
new ResizeObserver(measureToolbar).observe($('tools'));
const viewer=new PDFViewer({container:$('viewerContainer'),viewer:$('viewer'),eventBus,linkService:links,findController,annotationMode:0});
links.setViewer(viewer);
let task;
const fail=e=>{$('readerState').textContent='加载失败';$('error').hidden=false;$('error').textContent='原文件暂时无法显示：'+e.message+'。请返回后重新加载，或在独立窗口打开。';};
eventBus.on('pagesinit',()=>{viewer.currentScaleValue=$('scale').value;parent.postMessage({type:'labwise:reader-ready'},location.origin);});
eventBus.on('pagerendered',()=>{$('readerState').textContent='原文件';});
eventBus.on('pagechanging',e=>{$('page').value=e.pageNumber;$('prev').disabled=e.pageNumber===1;$('next').disabled=e.pageNumber===viewer.pagesCount;});
$('prev').onclick=()=>{if(viewer.currentPageNumber>1)viewer.currentPageNumber--;};
$('next').onclick=()=>{if(viewer.currentPageNumber<viewer.pagesCount)viewer.currentPageNumber++;};
$('page').onchange=()=>{const value=Number($('page').value);if(Number.isInteger(value)&&value>=1&&value<=viewer.pagesCount)viewer.currentPageNumber=value;else $('page').value=viewer.currentPageNumber;};
$('scale').onchange=()=>{viewer.currentScaleValue=$('scale').value;};
let lastWidth=0;
new ResizeObserver(entries=>{const width=entries[0].contentRect.width;if(width<=0||width===lastWidth)return;lastWidth=width;if(viewer.pdfDocument&&['page-width','page-fit'].includes($('scale').value)){const page=viewer.currentPageNumber;viewer.currentScaleValue=$('scale').value;viewer.currentPageNumber=page;}}).observe($('viewerContainer'));
try{
 const source=new URLSearchParams(location.search).get('file');
 if(!source?.startsWith('blob:'+location.origin+'/'))throw Error('文件地址无效');
 $('download').href=source;
 task=getDocument({url:source,cMapUrl:'/vendor/pdfjs/cmaps/',cMapPacked:true,standardFontDataUrl:'/vendor/pdfjs/standard_fonts/',wasmUrl:'/vendor/pdfjs/wasm/',isEvalSupported:false,enableXfa:false});
 task.onPassword=()=>{fail(Error('文件已加密，请上传未加密版本'));task.destroy();};
 const pdf=await task.promise;viewer.setDocument(pdf);links.setDocument(pdf);$('count').textContent='/ '+pdf.numPages;$('page').max=pdf.numPages;$('prev').disabled=true;$('next').disabled=pdf.numPages===1;
}catch(e){fail(e);}
window.addEventListener('pagehide',()=>task?.destroy());

let selection=null,locating=false;
function notify(message,found){parent.postMessage({type:'labwise:locate-result',message,found},location.origin);}
window.addEventListener('message',event=>{
 if(event.origin!==location.origin||event.source!==parent||event.data?.type!=='labwise:locate')return;
 const {quote,page}=event.data;if(typeof quote!=='string'||!quote.trim()||quote.length>100000)return;
 if(Number.isInteger(page)&&page>=1&&page<=viewer.pagesCount)viewer.currentPageNumber=page;
 locating=true;eventBus.dispatch('find',{source:window,type:'',query:quote,phraseSearch:true,caseSensitive:false,entireWord:false,highlightAll:true,findPrevious:false,matchDiacritics:false});
});
eventBus.on('updatefindcontrolstate',event=>{
 if(!locating||event.state===3)return;
 if(event.state===1){locating=false;notify('原文件中未找到这段证据，需人工核对；已保留原文件视图。',false);}
 else if(event.state===0||event.state===2){locating=false;notify('已在原文件中高亮证据。重复内容请结合上下文核对。',true);}
});
$('viewerContainer').addEventListener('pointerup',()=>{
 const selected=window.getSelection();const quote=selected?.toString().trim();const start=selected?.anchorNode?.parentElement?.closest('.page'),end=selected?.focusNode?.parentElement?.closest('.page');
 selection=quote&&quote.length<=4000&&start&&start===end?{quote,page:Number(start.dataset.pageNumber)}:null;
 $('addAnnotation').disabled=!selection;
 if(selection)parent.postMessage({type:'labwise:selection',...selection},location.origin);
});
$('addAnnotation').onclick=()=>{if(selection)parent.postMessage({type:'labwise:add-annotation',...selection},location.origin);};

// Capture pixels from a PDF render, so vector plots and tables are included too.
let visualSelecting=false;
function cancelVisualSelection(){document.querySelectorAll('.visual-select-layer').forEach(el=>el.remove());visualSelecting=false;}
async function captureVisual(pageNumber,bbox){
 cancelVisualSelection();$('readerState').textContent='正在准备图表截图…';
 try{
  const page=await viewer.pdfDocument.getPage(pageNumber),base=page.getViewport({scale:1});
  const scale=Math.min(2,2000/base.width,2600/base.height),viewport=page.getViewport({scale});
  const canvas=document.createElement('canvas');canvas.width=Math.ceil(viewport.width);canvas.height=Math.ceil(viewport.height);
  await page.render({canvasContext:canvas.getContext('2d'),viewport,annotationMode:0}).promise;
  const crop=document.createElement('canvas');crop.width=Math.max(1,Math.round((bbox[2]-bbox[0])*canvas.width));crop.height=Math.max(1,Math.round((bbox[3]-bbox[1])*canvas.height));
  if(Math.min(crop.width,crop.height)<24)throw Error('选区太小，请重新框选图表与图注。');
  crop.getContext('2d').drawImage(canvas,bbox[0]*canvas.width,bbox[1]*canvas.height,crop.width,crop.height,0,0,crop.width,crop.height);
  const image=crop.toDataURL('image/png').split(',')[1];if(image.length>5300000)throw Error('截图过大，请缩小图表选区。');
  const text=await page.getTextContent();const page_text=text.items.map(item=>item.str||'').join(' ').slice(0,16000);
  parent.postMessage({type:'labwise:visual-capture',page:pageNumber,bbox,image,page_text},location.origin);$('readerState').textContent='截图已就绪，请确认审核';
 }catch(error){$('readerState').textContent=error.message;}
}
function selectVisual(){
 if(!viewer.pdfDocument)return;cancelVisualSelection();visualSelecting=true;
 const pageNumber=viewer.currentPageNumber,pageView=viewer.getPageView(pageNumber-1);
 const layer=document.createElement('div');layer.className='visual-select-layer';
 const instruction=document.createElement('span');instruction.className='visual-select-instruction';instruction.textContent='拖动框选图表及图注 · Esc 取消';layer.append(instruction);
 const rectangle=document.createElement('div');rectangle.className='visual-selection-box';layer.append(rectangle);pageView.div.append(layer);
 let start=null;
 const point=event=>{const rect=layer.getBoundingClientRect();return [Math.max(0,Math.min(1,(event.clientX-rect.left)/rect.width)),Math.max(0,Math.min(1,(event.clientY-rect.top)/rect.height))];};
 layer.onpointerdown=event=>{event.preventDefault();start=point(event);layer.setPointerCapture(event.pointerId);};
 layer.onpointermove=event=>{if(!start)return;const end=point(event);Object.assign(rectangle.style,{left:Math.min(start[0],end[0])*100+'%',top:Math.min(start[1],end[1])*100+'%',width:Math.abs(end[0]-start[0])*100+'%',height:Math.abs(end[1]-start[1])*100+'%'});};
 layer.onpointerup=event=>{if(!start)return;const end=point(event),bbox=[Math.min(start[0],end[0]),Math.min(start[1],end[1]),Math.max(start[0],end[0]),Math.max(start[1],end[1])];void captureVisual(pageNumber,bbox);};
}
$('selectVisual').onclick=selectVisual;
$('reviewVisualPage').onclick=()=>{if(viewer.pdfDocument)void captureVisual(viewer.currentPageNumber,[0,0,1,1]);};
window.addEventListener('keydown',event=>{if(event.key==='Escape'&&visualSelecting)cancelVisualSelection();});
window.addEventListener('message',event=>{
 if(event.origin!==location.origin||event.source!==parent||event.data?.type!=='labwise:visual-region')return;
 const {page,bbox}=event.data;if(!Number.isInteger(page)||page<1||page>viewer.pagesCount||!Array.isArray(bbox)||bbox.length!==4||bbox.some(x=>!Number.isFinite(x)||x<0||x>1)||bbox[2]<=bbox[0]||bbox[3]<=bbox[1])return;
 viewer.currentPageNumber=page;document.querySelectorAll('.visual-region-highlight').forEach(el=>el.remove());
 const layer=document.createElement('div');layer.className='visual-region-highlight';Object.assign(layer.style,{left:bbox[0]*100+'%',top:bbox[1]*100+'%',width:(bbox[2]-bbox[0])*100+'%',height:(bbox[3]-bbox[1])*100+'%'});viewer.getPageView(page-1).div.append(layer);
});

window.addEventListener('message',event=>{if(event.origin===location.origin&&event.source===parent&&event.data?.type==='labwise:start-visual')selectVisual();});
