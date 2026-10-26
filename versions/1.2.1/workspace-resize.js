(function(){
  const workspace=document.getElementById('workspacePage');
  if(!workspace)return;
  const desktop=window.matchMedia('(min-width:901px)');
  const settings={
    rubric:{column:workspace.querySelector('.right'),variable:'--rubric-width',defaultWidth:340,min:260,max:520,collapsedClass:'rubric-collapsed',label:'评分细则'},
    assistant:{column:workspace.querySelector('.left'),variable:'--assistant-width',defaultWidth:300,min:220,max:460,collapsedClass:'assistant-collapsed',label:'报告理解与导航'}
  };
  const storageKey='labwise.workspace.layout.v1';
  let saved={};
  try{saved=JSON.parse(localStorage.getItem(storageKey)||'{}');}catch(_){saved={};}
  const clamp=(value,min,max)=>Math.min(max,Math.max(min,value));
  const availableMax=(key)=>{
    const other=key==='rubric'?'assistant':'rubric';
    if(!desktop.matches)return settings[key].max;
    const otherWidth=workspace.classList.contains(settings[other].collapsedClass)?48:(saved[other]?.width||settings[other].defaultWidth);
    const canvasWidth=workspace.clientWidth||window.innerWidth;
    return Math.max(settings[key].min,Math.min(settings[key].max,canvasWidth-440-otherWidth));
  };
  function persist(){try{localStorage.setItem(storageKey,JSON.stringify(saved));}catch(_){}}
  function applyWidth(key,value,announce=false){
    const item=settings[key];
    const width=clamp(Math.round(value),item.min,availableMax(key));
    saved[key]={...(saved[key]||{}),width};
    if(!workspace.classList.contains(item.collapsedClass))workspace.style.setProperty(item.variable,width+'px');
    if(announce)item.handle.setAttribute('aria-valuenow',String(width));
    return width;
  }
  function setCollapsed(key,collapsed){
    const item=settings[key];
    workspace.classList.toggle(item.collapsedClass,collapsed);
    saved[key]={...(saved[key]||{}),collapsed};
    if(collapsed)workspace.style.setProperty(item.variable,'48px');
    else applyWidth(key,saved[key].width||item.defaultWidth,true);
    item.toggle.textContent=collapsed?'‹':'›';
    item.toggle.setAttribute('aria-expanded',String(!collapsed));
    item.toggle.setAttribute('aria-label',(collapsed?'展开':'收起')+item.label);
    item.toggle.title=(collapsed?'展开':'收起')+item.label;
    persist();
  }
  function resetWidth(key){
    workspace.classList.remove(settings[key].collapsedClass);
    saved[key]={...(saved[key]||{}),collapsed:false,width:settings[key].defaultWidth};
    applyWidth(key,settings[key].defaultWidth,true);
    setCollapsed(key,false);
    showToast(settings[key].label+'已恢复默认宽度');
  }
  Object.entries(settings).forEach(([key,item])=>{
    const actions=document.createElement('div');
    actions.className='colhead-actions';
    const existing=item.column.querySelector('.colhead>:last-child');
    existing.replaceWith(actions);actions.append(existing);
    const toggle=document.createElement('button');
    toggle.type='button';toggle.className='panel-toggle';actions.append(toggle);item.toggle=toggle;
    toggle.onclick=()=>setCollapsed(key,!workspace.classList.contains(item.collapsedClass));

    const handle=document.createElement('div');
    handle.className='workspace-resize-handle';handle.tabIndex=0;handle.setAttribute('role','separator');handle.setAttribute('aria-orientation','vertical');handle.setAttribute('aria-label','调整'+item.label+'宽度');handle.setAttribute('aria-valuemin',String(item.min));handle.setAttribute('aria-valuemax',String(item.max));handle.title='拖动调整宽度；双击恢复默认';item.column.prepend(handle);item.handle=handle;
    let startX=0,startWidth=0;
    handle.addEventListener('pointerdown',event=>{
      if(!desktop.matches)return;
      startX=event.clientX;startWidth=item.column.getBoundingClientRect().width;
      handle.setPointerCapture(event.pointerId);handle.classList.add('dragging');document.body.classList.add('workspace-resizing');
    });
    handle.addEventListener('pointermove',event=>{
      if(!handle.hasPointerCapture(event.pointerId))return;
      applyWidth(key,startWidth-(event.clientX-startX),true);
    });
    const finish=event=>{
      if(handle.hasPointerCapture(event.pointerId))handle.releasePointerCapture(event.pointerId);
      handle.classList.remove('dragging');document.body.classList.remove('workspace-resizing');persist();
    };
    handle.addEventListener('pointerup',finish);handle.addEventListener('pointercancel',finish);handle.addEventListener('dblclick',()=>resetWidth(key));
    handle.addEventListener('keydown',event=>{
      if(!['ArrowLeft','ArrowRight','Home'].includes(event.key))return;
      event.preventDefault();
      if(event.key==='Home'){resetWidth(key);return;}
      const current=item.column.getBoundingClientRect().width;
      applyWidth(key,current+(event.key==='ArrowLeft'?16:-16),true);persist();
    });
  });
  Object.entries(settings).forEach(([key,item])=>{
    applyWidth(key,saved[key]?.width||item.defaultWidth,true);
    setCollapsed(key,Boolean(saved[key]?.collapsed));
  });
  window.addEventListener('resize',()=>{if(desktop.matches)Object.entries(settings).forEach(([key,item])=>applyWidth(key,saved[key]?.width||item.defaultWidth,true));});
})();
