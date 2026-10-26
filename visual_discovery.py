"""Local, resumable page-by-page visual inventory. No model/network calls."""
import base64
import hashlib
import io
import math
import re
import threading
import uuid
from pathlib import Path

VERSION = 'local-layout-1'
KINDS = ('chart', 'table', 'scientific_image', 'diagram', 'other', 'unknown')
CAPTION = re.compile(r'^(?:figure|fig\.?|table|图|表)\s*\d+', re.I)
RENDER_LOCK = threading.Lock()  # PDFium rendering is not thread-safe.


def valid_box(box):
    if (not isinstance(box, list) or len(box) != 4 or
        any(type(x) not in (int, float) or not math.isfinite(x) or not 0 <= x <= 1 for x in box) or
        box[2] <= box[0] or box[3] <= box[1]):
        raise ValueError('图表区域坐标无效。')
    return box


def area(b):
    return max(0,b[2]-b[0])*max(0,b[3]-b[1])


def overlap(a,b):
    shared=area([max(a[0],b[0]),max(a[1],b[1]),min(a[2],b[2]),min(a[3],b[3])])
    return shared / min(area(a),area(b)) if min(area(a),area(b)) else 0


def union(a,b):
    return [min(a[0],b[0]),min(a[1],b[1]),max(a[2],b[2]),max(a[3],b[3])]


def page_geometry(page):
    # pdfplumber exposes top-origin coordinates after page rotation. Clip to
    # the visible CropBox, which is also PDF.js's default viewport.
    from pdfminer.pdftypes import resolve1
    media=page.bbox
    left,bottom,right,top=[float(x) for x in page.page_obj.mediabox]
    raw=resolve1(page.page_obj.attrs.get('CropBox',page.page_obj.mediabox))
    rotation=page.rotation
    if rotation not in (0,90,180,270):raise ValueError('暂不支持该页面旋转角度。')
    def point(x,y):
        xy={0:(x-left,top-y),90:(y-bottom,x-left),180:(right-x,y-bottom),270:(top-y,right-x)}[rotation]
        return (xy[0]+media[0],xy[1]+media[1])
    corners=[point(float(x),float(y)) for x in (raw[0],raw[2]) for y in (raw[1],raw[3])]
    crop=[min(x for x,y in corners),min(y for x,y in corners),max(x for x,y in corners),max(y for x,y in corners)]
    bounds=[max(media[0],crop[0]),max(media[1],crop[1]),min(media[2],crop[2]),min(media[3],crop[3])]
    if area(bounds)<=0:raise ValueError('页面裁切区域无效。')
    # Keep pdfplumber's thumbnail projection aligned with the corrected rotated
    # CropBox; PDFium itself renders the PDF's native, correct visible crop.
    page.cropbox=tuple(bounds)
    return bounds


def normalized(box,bounds,pad=0):
    x,y,r,b=bounds;w,h=r-x,b-y
    clipped=[max(x,box[0]-pad),max(y,box[1]-pad),min(r,box[2]+pad),min(b,box[3]+pad)]
    if area(clipped)<=0:return None
    return [(clipped[0]-x)/w,(clipped[1]-y)/h,(clipped[2]-x)/w,(clipped[3]-y)/h]


def scan_page(pdf_path,number,preview_hash):
    import pdfplumber
    with pdfplumber.open(pdf_path) as document:
        page=document.pages[number-1];bounds=page_geometry(page)
        visible=page.crop(tuple(bounds));w,h=bounds[2]-bounds[0],bounds[3]-bounds[1]
        shapes=visible.lines+visible.rects+visible.curves
        if len(shapes)>5000 or len(visible.chars)>30000:
            raise ValueError('页面对象过多，请手动补选该页图表。')
        candidates=[]
        def add(box,kind,source,evidence):
            b=normalized(box,bounds,4)
            if b and (b[2]-b[0])*w>=20 and (b[3]-b[1])*h>=20:
                candidates.append({'bbox':b,'type':kind,'sources':[source],'evidence':[evidence]})
        for im in visible.images:
            add([im['x0'],im['top'],im['x1'],im['bottom']],'unknown','embedded_image','嵌入图片，科学类型待核实')
        # Ruled tables first, then borderless alignment candidates. A table needs
        # actual numeric cells, not merely paragraph text arranged in columns.
        table_boxes=[]
        for strategy in ('lines','text'):
            settings={'vertical_strategy':strategy,'horizontal_strategy':strategy,'min_words_vertical':3}
            for table in visible.find_tables(settings):
                rows=table.extract();cols=len(table.columns)
                numeric=sum(bool(re.fullmatch(r'[-+]?\d[\d.,%eE+−-]*',str(cell or '').strip())) for row in rows for cell in row)
                if cols<2 or len(rows)<3 or (strategy=='text' and numeric<3):continue
                box=list(table.bbox);table_boxes.append(box)
                add(box,'table','table_'+strategy,'表格行列结构候选，需核对边界')
        # Merge nearby vector primitives, not text glyphs. Expanding by 10 pt
        # joins axis ticks/bars; isolated tiny ornaments remain filtered.
        groups=[]
        for shape in shapes:
            box=[shape['x0'],shape['top'],shape['x1'],shape['bottom']]
            if any(overlap([box[0]-1,box[1]-1,box[2]+1,box[3]+1],tb)>.8 for tb in table_boxes):continue
            if area(box)>w*h*.9:continue  # page border/background
            changed=True
            while changed:
                changed=False
                for i,g in enumerate(groups):
                    if not (box[2]+10<g[0] or g[2]+10<box[0] or box[3]+10<g[1] or g[3]+10<box[1]):
                        box=union(box,groups.pop(i));changed=True;break
            groups.append(box)
        for box in groups:
            if box[2]-box[0]>=45 and box[3]-box[1]>=35:
                add(box,'unknown','vector_graphics','相邻矢量线条或曲线，可能为图表或示意图')
        # Caption anchors are discovery hints; linking is deliberately provisional.
        lines=visible.extract_text_lines() or []
        captions=[line for line in lines if CAPTION.match(line['text'].strip())]
        for line in captions:
            nearest=sorted(candidates,key=lambda c:abs((c['bbox'][3]*h+bounds[1])-line['top']))
            if nearest:
                candidate=nearest[0];bb=candidate['bbox'];lb=normalized([line['x0'],line['top'],line['x1'],line['bottom']],bounds,2)
                if lb and min(abs(bb[3]-lb[1]),abs(lb[3]-bb[1]))*h<65 and lb[0]<bb[2] and lb[2]>bb[0]:
                    candidate['caption_candidate']=line['text'][:1000]
                    candidate['bbox']=union(bb,lb)
        merged=[]
        for c in sorted(candidates,key=lambda c:0 if c['type']=='table' else 1):
            existing=next((g for g in merged if overlap(c['bbox'],g['bbox'])>.65),None)
            if existing:
                # A borderless-table heuristic often includes nearby prose.
                # Preserve the stronger ruled-table extent and caption.
                if not ('table_lines' in existing['sources'] and 'table_text' in c['sources']):
                    existing['bbox']=union(existing['bbox'],c['bbox'])
                existing['sources']=list(dict.fromkeys(existing['sources']+c['sources']))
                existing['evidence']=list(dict.fromkeys(existing['evidence']+c['evidence']))
                if c.get('caption_candidate'):existing['caption_candidate']=c['caption_candidate']
            else:merged.append(c)
        if len(merged)>80:raise ValueError('该页候选超过 80 项，请手动补选或拆分文档。')
        for c in merged:
            c['bbox']=[round(x,6) for x in c['bbox']]
            fingerprint=preview_hash+':'+str(number)+':'+','.join(f'{x:.3f}' for x in c['bbox'])
            c.update(id=hashlib.sha256(fingerprint.encode()).hexdigest()[:24],page=number,
                     decision='pending',manual=False,classification='candidate',detector=VERSION)
        scanned=len(visible.chars)<10 and bool(visible.images)
        unresolved=scanned or bool(shapes and not merged) or bool(captions and not merged)
        return merged,{'page':number,'state':'needs_supplement' if unresolved else ('with_candidates' if merged else 'no_candidates'),
                       'count':len(merged),'rotation':page.rotation,'bounds':bounds,
                       'message':'该页缺少可靠文字或版面依据，请在原页补选；尚未执行 OCR/视觉补扫。' if unresolved else '',
                       'width':w,'height':h}


def preview_file(r,root):
    source=root/'sources'/(r['id']+'.bin')
    if not source.is_file():raise ValueError('请先导入并保存原文件。')
    raw=source.read_bytes();digest=hashlib.sha256(raw).hexdigest()
    if digest!=r.get('source_sha256'):raise ValueError('原文件版本校验失败，请重新导入。')
    if r['source_filename'].lower().endswith('.docx'):
        # Reuse the same pinned PDF as the teacher's viewer, not a fresh conversion.
        pinned=r.get('visual_preview') or {}
        cached=root/'scan_previews'/(r['id']+'.pdf')
        if pinned.get('source_sha256')==digest and cached.is_file() and hashlib.sha256(cached.read_bytes()).hexdigest()==pinned.get('sha256'):
            return cached,pinned['sha256']
        from document_preview import preview
        converted=preview({'filename':r['source_filename'],'file':base64.b64encode(raw).decode()})
        if converted.get('content_type')!='application/pdf':raise ValueError('Word 兼容阅读视图无法可靠定位图表，请导出 PDF 后重新导入。')
        raw=base64.b64decode(converted['file']);cached.parent.mkdir(parents=True,exist_ok=True);cached.write_bytes(raw)
        digest_preview=hashlib.sha256(raw).hexdigest()
        r['visual_preview']={'sha256':digest_preview,'source_sha256':digest,'converter':'document_preview','warnings':converted.get('warnings',[])}
        return cached,digest_preview
    return source,digest


def inventory(r):
    return {'scan':r.get('visual_scan'),'objects':r.get('visual_objects',[]),'revision':r['revision'],'preview':r.get('visual_preview')}


def mutate(action,body,r,root):
    import pilot_backend as p
    objects=r.setdefault('visual_objects',[])
    if action=='visual-object':
        task=r.get('visual_scan')
        if task and task['status']=='running':raise ValueError('请先暂停扫描，再修订图表目录。')
        if body.get('source_sha256')!=r.get('source_sha256'):raise ValueError('原文件版本不一致。')
        pdf,digest=preview_file(r,root)
        from pypdf import PdfReader
        page_count=len(PdfReader(pdf).pages)
        oid=body.get('id');obj=next((o for o in objects if o['id']==oid),None)
        if oid and obj is None:raise ValueError('图表候选已变化，请重新加载。')
        page=body.get('page',obj['page'] if obj else None)
        if type(page) is not int or not 1<=page<=page_count:raise ValueError('图表页码无效。')
        box=valid_box(body.get('bbox',obj['bbox'] if obj else None))
        kind=body.get('type',obj['type'] if obj else 'unknown')
        decision=body.get('decision',obj['decision'] if obj else 'pending')
        if kind not in KINDS or decision not in ('pending','confirmed','excluded'):raise ValueError('图表类别或确认状态无效。')
        if not obj:
            if len(objects)>=1000:raise ValueError('每份报告最多保存 1,000 个候选。')
            obj={'id':uuid.uuid4().hex[:24],'sources':['teacher_selection'],'evidence':['教师在原页手动补选'],'manual':True}
            objects.append(obj)
        else:
            previous={key:obj.get(key) for key in ('page','bbox','type','title','decision','updated')}
            obj.setdefault('edit_history',[]).append({'before':previous,'at':p.now(),'actor':'teacher'})
            obj['edit_count']=obj.get('edit_count',0)+1
            obj['edit_history']=obj['edit_history'][-50:]
        obj.update(page=page,bbox=box,type=kind,decision=decision,preview_sha256=digest,source_sha256=r['source_sha256'],
                   title=p.text(body.get('title',obj.get('title','')),200),edited=True,updated=p.now())
        return
    if action=='visual-scan':
        old=r.get('visual_scan')
        pdf,digest=preview_file(r,root)
        if old and old['preview_sha256']==digest and old['detector']==VERSION and not body.get('rescan'):
            if old['status']=='cancelled':old['status']='running'
            if body.get('retry'):
                for pg in old['pages']:
                    if pg['state']=='failed':pg.update(state='pending',message='')
                old['status']='running'
                old['processed']=sum(pg['state']!='pending' for pg in old['pages'])
            return
        from pypdf import PdfReader
        count=len(PdfReader(pdf).pages)
        if not 1<=count<=200:raise ValueError('扫描支持 1–200 页。')
        r['visual_objects']=[o for o in objects if o.get('edited') and o.get('preview_sha256')==digest]
        r['visual_scan']={'id':uuid.uuid4().hex,'status':'running','detector':VERSION,'source_sha256':r['source_sha256'],
                          'preview_sha256':digest,'page_count':count,'processed':0,'created':p.now(),
                          'pages':[{'page':i,'state':'pending','message':''} for i in range(1,count+1)],
                          'external_calls':0,'excluded_previous':sum(not o.get('edited') for o in objects)}
        return
    job=r.get('visual_scan')
    if not job or body.get('scan_id')!=job['id']:raise ValueError('扫描任务已变化，请重新加载。')
    if action=='visual-scan-cancel':
        if job['status']=='running':job['status']='cancelled'
        return
    if action!='visual-scan-next':raise ValueError('未知扫描操作。')
    if job['status']!='running':return
    pdf,digest=preview_file(r,root)
    if digest!=job['preview_sha256']:raise ValueError('预览版本已变化，请重新扫描。')
    pg=next((x for x in job['pages'] if x['state']=='pending'),None)
    if pg:
        try:
            found,result=scan_page(pdf,pg['page'],digest)
            if len(objects)+len(found)>1000:raise ValueError('报告候选数量超过 1,000，需人工补查。')
            for obj in found:
                obj.update(source_sha256=r['source_sha256'],preview_sha256=digest)
                existing=next((o for o in objects if o['id']==obj['id'] or
                               (o.get('edited') and o['page']==obj['page'] and overlap(o['bbox'],obj['bbox'])>.8)),None)
                if existing is None:objects.append(obj)
            pg.update(result)
        except Exception as exc:
            pg.update(state='failed',message=str(exc) if isinstance(exc,ValueError) else '页面解析失败，可重试或手动补选。')
    job['processed']=sum(x['state']!='pending' for x in job['pages']);job['updated']=p.now()
    if all(x['state']!='pending' for x in job['pages']):
        job['status']='partial_completed' if any(x['state'] in ('failed','needs_supplement') for x in job['pages']) else 'completed'


def thumbnail(r,root,oid):
    obj=next((o for o in r.get('visual_objects',[]) if o['id']==oid),None)
    if not obj:raise LookupError('图表候选不存在。')
    pdf,digest=preview_file(r,root)
    if digest!=obj['preview_sha256']:raise ValueError('图表预览已过期。')
    import pdfplumber
    with pdfplumber.open(pdf) as doc:
        pg=doc.pages[obj['page']-1];bounds=page_geometry(pg);w,h=bounds[2]-bounds[0],bounds[3]-bounds[1]
        if w*h>10_000_000:raise ValueError('页面尺寸过大，无法生成缩略图。')
        b=obj['bbox'];box=(bounds[0]+b[0]*w,bounds[1]+b[1]*h,bounds[0]+b[2]*w,bounds[1]+b[3]*h)
        with RENDER_LOCK:
            image=pg.crop(box).to_image(resolution=min(96,1200*72/max(w,h))).original
        image.thumbnail((380,200));stream=io.BytesIO();image.save(stream,format='PNG')
        return {'image':base64.b64encode(stream.getvalue()).decode(),'content_type':'image/png'}
