"""Source-bound DOCX extraction. Embedded content only; never fetch external links."""
import base64
import hashlib
import io
import json
import posixpath
import re
import zipfile
import xml.etree.ElementTree as E

W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
A='http://schemas.openxmlformats.org/drawingml/2006/main'
C='http://schemas.openxmlformats.org/drawingml/2006/chart'
VERSION='word-native-v1'


def package(raw):
    if len(raw)>10*1024*1024: raise ValueError('Word 文件不能超过 10 MB。')
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            if len(archive.infolist())>1500 or sum(i.file_size for i in archive.infolist())>40*1024*1024:
                raise ValueError('Word 文件解压后过大。')
            files={i.filename:archive.read(i) for i in archive.infolist()}
        if 'word/document.xml' not in files: raise ValueError('请提交未加密的 DOCX 文档。')
        if any(b'<!DOCTYPE' in b or b'<!ENTITY' in b for k,b in files.items() if k.endswith(('.xml','.rels'))):
            raise ValueError('不支持含实体定义的 Word 文档。')
        return files
    except (zipfile.BadZipFile,RuntimeError,KeyError): raise ValueError('Word 文件无效或已加密。')


def paragraph_text(p):
    def walk(n):
        if n is not p and n.tag=='{'+W+'}p': return ''
        if n.tag in ('{'+W+'}t','{http://schemas.openxmlformats.org/officeDocument/2006/math}t'): return n.text or ''
        if n.tag=='{'+W+'}tab': return '\t'
        if n.tag in ('{'+W+'}br','{'+W+'}cr'): return '\n'
        return ''.join(walk(c) for c in n)
    return walk(p).strip()


def extract(raw):
    files=package(raw);root=E.fromstring(files['word/document.xml']);digest=hashlib.sha256(raw).hexdigest()
    rels={r.get('Id'):r for r in E.fromstring(files.get('word/_rels/document.xml.rels',b'<Relationships/>'))}
    paragraphs=[];objects=[];warnings=[]
    for index,p in enumerate(root.iter('{'+W+'}p')):
        value=paragraph_text(p);pid='p'+str(len(paragraphs)+1);local=[]
        refs=[]
        for element in p.iter():
            if element.tag in ('{'+A+'}blip','{urn:schemas-microsoft-com:vml}imagedata','{'+C+'}chart'):
                rid=element.get('{'+R+'}embed') or element.get('{'+R+'}id') or element.get('{'+R+'}link')
                if rid and rid not in refs: refs.append(rid)
        for rid in refs:
            rel=rels.get(rid);oid='v'+str(len(objects)+1)
            item={'id':oid,'paragraph_id':pid,'paragraph_index':index,'status':'unreadable','kind':'image'}
            if rel is not None and rel.get('TargetMode','').lower()!='external':
                target=posixpath.normpath(posixpath.join('word',rel.get('Target','')))
                item['part']=target;blob=files.get(target,b'')
                if 'chart' in rel.get('Type',''):
                    item['kind']='chart'
                    try:
                        chart=E.fromstring(blob)
                        item['chart_series']=[{'name':' '.join(n.text or '' for n in ser.findall('.//{'+C+'}tx//{'+C+'}v')),'categories':[n.text or '' for n in ser.findall('.//{'+C+'}cat//{'+C+'}v')][:2000],'values':[n.text or '' for n in ser.findall('.//{'+C+'}val//{'+C+'}v')][:2000],'x':[n.text or '' for n in ser.findall('.//{'+C+'}xVal//{'+C+'}v')][:2000],'y':[n.text or '' for n in ser.findall('.//{'+C+'}yVal//{'+C+'}v')][:2000]} for ser in chart.iter('{'+C+'}ser')]
                        item['chart_text']=' | '.join((n.text or '') for n in chart.iter() if n.tag in ('{'+C+'}v','{'+A+'}t'))[:24000]
                        item['status']='chart_data_only'
                    except E.ParseError: pass
                elif blob.startswith((b'\x89PNG',b'\xff\xd8',b'GIF8')) or blob[:4]==b'RIFF' and blob[8:12]==b'WEBP':
                    item['status']='image_ready'
                else: item['status']='unsupported_image'
            else: item['status']='external_or_missing'
            local.append(oid);objects.append(item)
        if not refs and any(n.tag in ('{'+W+'}drawing','{'+W+'}pict','{'+W+'}object') for n in p.iter()):
            oid='v'+str(len(objects)+1);objects.append({'id':oid,'paragraph_id':pid,'paragraph_index':index,'kind':'drawing','status':'unsupported_drawing'});local.append(oid)
        if not value and not local: continue
        style=p.find('{'+W+'}pPr/{'+W+'}pStyle');heading=style is not None and 'heading' in style.get('{'+W+'}val','').lower()
        paragraphs.append({'id':pid,'text':value or '[Word 图表对象 '+', '.join(local)+']','heading':heading,'object_ids':local,
                           'anchor':{'part':'word/document.xml','paragraph_index':index,'source_sha256':digest},'object_only':not bool(value)})
    if not paragraphs or sum(len(p['text']) for p in paragraphs)>100000: raise ValueError('Word 正文为空或超过 100,000 字符。')
    if any(n.endswith(('footnotes.xml','endnotes.xml')) or re.fullmatch(r'word/(header|footer)\d+\.xml',n) for n in files):
        warnings.append('页眉、页脚及脚注不参与正文自动评分，请教师核对。')
    tables=[{'id':'t'+str(i+1),'rows':[[' '.join(paragraph_text(p) for p in cell.iter('{'+W+'}p')) for cell in row if cell.tag=='{'+W+'}tc'] for row in table if row.tag=='{'+W+'}tr']} for i,table in enumerate(root.iter('{'+W+'}tbl'))]
    return {'version':VERSION,'tables':tables,'paragraphs':paragraphs,'objects':objects,'warnings':warnings,'source_sha256':digest}


def inputs(report, root):
    source=root/'sources'/(report['id']+'.bin');raw=source.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=report['source_sha256']:raise ValueError('Word 原文件校验失败。')
    doc=extract(raw);files=package(raw);blocks=[];coverage=[];total=0
    for obj in doc['objects']:
        item=dict(obj)
        if obj['status']=='image_ready':
            data=files[obj['part']]
            if len(blocks)//2>=40 or total+len(data)>20*1024*1024:
                item['status']='over_limit'
            else:
                try:
                    from PIL import Image
                    im=Image.open(io.BytesIO(data));im.seek(0);im.thumbnail((2400,2400));output=io.BytesIO();im.convert('RGB').save(output,format='PNG');data=output.getvalue()
                    if len(data)>5*1024*1024: raise ValueError('图像过大')
                    blocks.extend([{'type':'text','text':'Word object '+obj['id']+' at paragraph '+obj['paragraph_id']},
                                   {'type':'image_url','image_url':{'url':'data:image/png;base64,'+base64.b64encode(data).decode()}}]);total+=len(data);item['status']='image_sent'
                except Exception: item['status']='unreadable_image'
        coverage.append(item)
    # Office-native charts and drawings need a rendering, never pretend cached values are visual inspection.
    needs_render=any(o['status'] not in ('image_sent',) for o in coverage)
    render_note=None
    if needs_render:
        try:
            from document_preview import preview
            converted=preview({'filename':report['source_filename'],'file':base64.b64encode(raw).decode()})
            if converted.get('content_type')!='application/pdf': raise ValueError('当前环境未提供图表版式渲染')
            import pypdfium2 as pdfium
            pdf=pdfium.PdfDocument(base64.b64decode(converted['file']))
            try:
                if len(pdf)>30: raise ValueError('Word 超过自动版式分析页数上限 30 页')
                rendered=[]
                for i in range(len(pdf)):
                    page=pdf[i]
                    try:
                        bitmap=page.render(scale=1.6)
                        try:
                            image=bitmap.to_pil();image.thumbnail((1800,2400));buf=io.BytesIO();image.save(buf,format='PNG');data=buf.getvalue()
                        finally:bitmap.close()
                    finally:page.close()
                    total+=len(data)
                    if total>24*1024*1024: raise ValueError('Word 图像总量超过自动分析上限')
                    rendered.extend([{'type':'text','text':f'Word layout rendering page {i+1}. Match objects to their Word paragraph anchors; do not invent an exact object-page mapping.'}, {'type':'image_url','image_url':{'url':'data:image/png;base64,'+base64.b64encode(data).decode()}}])
                blocks.extend(rendered)
                for obj in coverage:
                    if obj['status'] not in ('external_or_missing','over_limit'):obj['status']='image_sent' if obj['status']=='image_sent' else 'layout_sent'
            finally:pdf.close()
        except Exception:render_note='部分原生图形未能渲染；仅提取到的图表数据会参与分析，视觉细节需教师核对。'
    missing=[o for o in coverage if o['status'] not in ('image_sent','layout_sent')]
    warnings=doc['warnings']+([render_note] if render_note else [])
    if missing:warnings.append(str(len(missing))+' 个图形对象未完成视觉读取，请核对原 Word。')
    return doc,blocks,{'state':'partial' if warnings else 'complete','objects':coverage,'warnings':warnings}


def reading_view(raw):
    from document_preview import readable_preview
    doc=extract(raw);files=package(raw)
    return {**doc,'html':readable_preview(files, {p['anchor']['paragraph_index']:p['id'] for p in doc['paragraphs']})}
