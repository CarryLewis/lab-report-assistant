"""Offline Word preview from a sanitized copy, with a readable compatibility view."""
import base64
import binascii
import html
import io
import os
import posixpath
import re
import shutil
import struct
import subprocess
import tempfile
import zipfile
import zlib
import xml.etree.ElementTree as ET
from pathlib import Path

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
P = 'http://schemas.openxmlformats.org/package/2006/relationships'
CT = 'http://schemas.openxmlformats.org/package/2006/content-types'
M = 'http://schemas.openxmlformats.org/officeDocument/2006/math'
DANGEROUS_FIELD = re.compile(r'\b(INCLUDEPICTURE|INCLUDETEXT|LINK|DDEAUTO|DDE|DATABASE)\b', re.I)


def _xml(raw):
    if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
        raise ValueError('文档 XML 包含不支持的实体定义。')
    return ET.fromstring(raw)


def _owner(relationships):
    if relationships == '_rels/.rels':
        return ''
    parent, name = relationships.rsplit('/_rels/', 1)
    return parent + '/' + name[:-5]


def _placeholder():
    """A local gray cross replaces an image that exists only as an external link."""
    width, height = 240, 90
    rows = bytearray()
    for y in range(height):
        rows.append(0)
        for x in range(width):
            dark = abs(x * height - y * width) < 320 or abs((width-x)*height-y*width) < 320
            rows.extend((190, 198, 205) if dark else (239, 242, 245))
    def chunk(kind, payload):
        return struct.pack('!I', len(payload)) + kind + payload + struct.pack('!I', zlib.crc32(kind+payload)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!2I5B', width,height,8,2,0,0,0)) + chunk(b'IDAT',zlib.compress(rows)) + chunk(b'IEND',b'')


def _freeze_fields(root):
    """Keep cached field results, but remove instructions that can load other files."""
    parents = {child:parent for parent in root.iter() for child in parent}
    removed = 0
    stack = []
    for element in list(root.iter()):
        if element.tag == '{'+W+'}fldSimple' and DANGEROUS_FIELD.search(element.get('{'+W+'}instr','')):
            parent = parents.get(element)
            if parent is not None:
                index = list(parent).index(element)
                for child in list(element):
                    parent.insert(index, child); index += 1
                parent.remove(element); removed += 1
        elif element.tag == '{'+W+'}fldChar':
            kind = element.get('{'+W+'}fldCharType')
            if kind == 'begin':
                stack.append({'instructions':[], 'markers':[element]})
            elif stack:
                stack[-1]['markers'].append(element)
                if kind == 'end':
                    field = stack.pop()
                    if DANGEROUS_FIELD.search(''.join(n.text or '' for n in field['instructions'])):
                        for node in field['instructions'] + field['markers']:
                            parent = parents.get(node)
                            if parent is not None and node in list(parent):
                                parent.remove(node)
                        removed += 1
        elif element.tag == '{'+W+'}instrText' and stack:
            stack[-1]['instructions'].append(element)
    # Also freeze incomplete fields in damaged-but-readable documents.
    for field in stack:
        if DANGEROUS_FIELD.search(''.join(n.text or '' for n in field['instructions'])):
            for node in field['instructions']+field['markers']:
                parent=parents.get(node)
                if parent is not None and node in list(parent):
                    parent.remove(node)
            removed += 1
    return removed


def prepare_copy(raw):
    """Never resolve external relationships; preserve embedded resources/chart caches."""
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            infos=archive.infolist()
            if len(infos)>1500 or sum(i.file_size for i in infos)>40*1024*1024:
                raise ValueError('文档解压后过大。')
            names=[i.filename for i in infos]
            if len(names)!=len(set(names)) or any(n.startswith('/') or '..' in n.split('/') or '\\' in n for n in names):
                raise ValueError('文档内部文件结构无效。')
            if 'word/document.xml' not in names:
                raise ValueError('不是有效的 DOCX 文件。')
            files={info.filename:archive.read(info) for info in infos if not info.is_dir()}
        trees={name:_xml(data) for name,data in files.items() if name.endswith(('.xml','.rels'))}
    except (zipfile.BadZipFile, KeyError, ET.ParseError, RuntimeError, OSError):
        raise ValueError('无法读取 DOCX，请检查文件是否完整或是否加密。')
    warnings=[]; linked=0; fields=0; placeholders=0; removed_objects=0
    modified=set()
    placeholder_name='word/media/labwise-preview-missing.png'
    while placeholder_name in files:
        placeholder_name=placeholder_name.replace('.png','-copy.png')
    for rel_name, rels in list(trees.items()):
        if not rel_name.endswith('.rels'):
            continue
        owner=_owner(rel_name); removed=set()
        for relation in list(rels):
            target=relation.get('Target',''); external=relation.get('TargetMode','').lower()=='external'
            # Defensive: absolute URI/file targets must never be treated as embedded resources.
            absolute=bool(re.match(r'^[a-z][a-z0-9+.-]*:',target,re.I) or target.startswith(('//','\\\\')))
            if external or absolute:
                # Ordinary hyperlinks are clickable text, not loaded document content.
                if relation.get('Type','').endswith('/hyperlink') and re.match(r'^(https?://|mailto:)',target,re.I):
                    continue
                removed.add(relation.get('Id')); rels.remove(relation); linked+=1; modified.add(rel_name)
        root=trees.get(owner)
        if root is None or not removed:
            continue
        modified.add(owner)
        parents={child:parent for parent in root.iter() for child in parent}
        used_ids={r.get('Id') for r in rels}
        replacement=None
        def replacement_id():
            nonlocal replacement, placeholders
            if replacement is None:
                replacement='labwisePreviewImage'
                while replacement in used_ids:
                    replacement += '1'
                namespace=rels.tag.split('}')[0][1:] if '}' in rels.tag else ''
                ET.SubElement(rels, ('{'+namespace+'}' if namespace else '')+'Relationship', {
                    'Id':replacement,'Type':R+'/image',
                    'Target':posixpath.relpath(placeholder_name,posixpath.dirname(owner))})
                files[placeholder_name]=_placeholder(); placeholders+=1
            return replacement
        for element in list(root.iter()):
            bad=[key for key,value in element.attrib.items() if value in removed and
                 (key.startswith('{'+R+'}') or key.endswith('}relid'))]
            if not bad:
                continue
            local=element.tag.rsplit('}',1)[-1]
            if local in ('blip','imagedata'):
                embedded=element.get('{'+R+'}embed')
                for key in bad:
                    element.attrib.pop(key,None)
                if not embedded or embedded in removed:
                    element.set('{'+R+'}embed' if local=='blip' else '{'+R+'}id',replacement_id())
            elif local in ('externalData','OLEObject','altChunk','attachedTemplate','control'):
                parent=parents.get(element)
                if parent is not None:
                    parent.remove(element);removed_objects+=1
            else:
                for key in bad:
                    element.attrib.pop(key,None)
    for name,root in trees.items():
        if name.startswith('word/') and name.endswith('.xml'):
            field_count = _freeze_fields(root)
            fields += field_count
            if field_count: modified.add(name)
            # An internal HTML altChunk can itself contain links outside the package.
            for parent in root.iter():
                for element in list(parent):
                    if element.tag=='{'+W+'}altChunk':
                        parent.remove(element);removed_objects+=1;modified.add(name)
    if placeholders:
        content_types=trees.get('[Content_Types].xml')
        if content_types is not None and not any(n.get('Extension','').lower()=='png' for n in content_types):
            modified.add('[Content_Types].xml')
            ET.SubElement(content_types,'{'+CT+'}Default',{'Extension':'png','ContentType':'image/png'})
    # Embedded SVG may contain its own external references, outside .rels files.
    for name,data in list(files.items()):
        if not name.lower().endswith('.svg'):
            continue
        try:
            svg=_xml(data)
        except ET.ParseError:
            continue
        changed=False
        for parent in svg.iter():
            for element in list(parent):
                if element.tag.rsplit('}',1)[-1] in ('script','foreignObject'):
                    parent.remove(element);changed=True
            for attribute,value in list(parent.attrib.items()):
                local=attribute.rsplit('}',1)[-1].lower()
                if (local in ('href','src') and not value.startswith('#')) or (local=='style' and re.search(r'url\s*\(|@import',value,re.I)) or local.startswith('on'):
                    parent.attrib.pop(attribute);changed=True
            if parent.tag.rsplit('}',1)[-1]=='style' and re.search(r'url\s*\(|@import',parent.text or '',re.I):
                parent.text='';changed=True
        if changed:
            files[name]=ET.tostring(svg,encoding='utf-8',xml_declaration=True)
            warnings.append('内嵌图形中的外部资源未加载。')
    if linked or fields:
        warnings.append('预览副本已关闭外部数据更新；使用文档内嵌图片、图表缓存和已有字段结果。')
    if placeholders:
        warnings.append('仅存在于外部链接的图片以灰色占位图显示，未联网下载。')
    if removed_objects:
        warnings.append('链接对象或外部插入内容未加载；其已有图片或图表缓存尽量保留。')
    for name in modified:
        tree=trees[name]
        # Preserve prefixes used in markup-compatibility attributes such as Requires.
        declarations={}
        for event,pair in ET.iterparse(io.BytesIO(files[name]),events=('start-ns',)):
            prefix,uri=pair
            declarations[prefix]=uri
            if not re.fullmatch(r'ns\d+',prefix or ''):
                try: ET.register_namespace(prefix,uri)
                except ValueError: pass
        serialized=ET.tostring(tree,encoding='utf-8',xml_declaration=True)
        for prefix,uri in declarations.items():
            if prefix and prefix!='xml' and ('xmlns:'+prefix+'=').encode() not in serialized:
                tree.set('xmlns:'+prefix,uri)
        files[name]=ET.tostring(tree,encoding='utf-8',xml_declaration=True)
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
        for name,data in files.items():
            archive.writestr(name,data)
    return output.getvalue(),files,warnings


def readable_preview(files, paragraph_ids=None):
    """Safe HTML fallback for text, tables, formulas and embedded raster images."""
    root=_xml(files['word/document.xml']); rels={}
    if 'word/_rels/document.xml.rels' in files:
        for relation in _xml(files['word/_rels/document.xml.rels']):
            if relation.get('TargetMode','').lower()!='external':
                rels[relation.get('Id')]=posixpath.normpath(posixpath.join('word',relation.get('Target','')))
    paragraph_index={id(p):i for i,p in enumerate(root.iter('{'+W+'}p'))}
    image_bytes=0
    def inline(element):
        nonlocal image_bytes
        local=element.tag.rsplit('}',1)[-1]
        if element.tag in ('{'+W+'}t','{'+M+'}t'):
            return html.escape(element.text or '')
        if element.tag=='{'+W+'}tab': return '&emsp;'
        if element.tag in ('{'+W+'}br','{'+W+'}cr'): return '<br>'
        if local in ('blip','imagedata'):
            rid=element.get('{'+R+'}embed') or element.get('{'+R+'}id')
            data=files.get(rels.get(rid,''),b'')
            mime='image/png' if data.startswith(b'\x89PNG') else 'image/jpeg' if data.startswith(b'\xff\xd8') else 'image/gif' if data.startswith(b'GIF8') else None
            if mime and len(data)<=4*1024*1024 and image_bytes+len(data)<=12*1024*1024:
                image_bytes+=len(data)
                return '<img alt="文档内嵌图片" src="data:'+mime+';base64,'+base64.b64encode(data).decode()+'">'
            return '<span class="missing">[此图形无法在兼容预览中显示]</span>'
        content=''.join(inline(child) for child in element if child.tag not in ('{'+W+'}rPr','{'+W+'}pPr'))
        if element.tag=='{'+W+'}r':
            props=element.find('{'+W+'}rPr')
            if props is not None:
                for tag,wrapper in [('b','strong'),('i','em'),('u','u')]:
                    prop=props.find('{'+W+'}'+tag)
                    if prop is not None and prop.get('{'+W+'}val') not in ('0','false','off','none'):
                        content='<'+wrapper+'>'+content+'</'+wrapper+'>'
        return content
    def blocks(element):
        if element.tag=='{'+W+'}p':
            style=element.find('{'+W+'}pPr/{'+W+'}pStyle')
            heading=re.search(r'heading\s*([1-6])',style.get('{'+W+'}val',''),re.I) if style is not None else None
            tag='h'+heading.group(1) if heading else 'p'
            index=paragraph_index[id(element)]
            anchor=' data-word-index="'+str(index)+'" data-paragraph-id="'+html.escape((paragraph_ids or {}).get(index,''),quote=True)+'"' if paragraph_ids is not None else ''
            return '<'+tag+anchor+'>'+inline(element)+'</'+tag+'>'
        if element.tag=='{'+W+'}tbl':
            return '<table>'+''.join('<tr>'+''.join('<td>'+''.join(blocks(c) for c in cell)+'</td>' for cell in row if cell.tag=='{'+W+'}tc')+'</tr>' for row in element if row.tag=='{'+W+'}tr')+'</table>'
        return ''.join(blocks(child) for child in element)
    body=root.find('{'+W+'}body')
    content=blocks(body) if body is not None else ''
    if not content.strip():
        raise ValueError('文档未包含可预览的正文内容。')
    return '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"><style>body{margin:0;padding:24px;background:#525659;color:#202830;font:15px/1.8 Georgia,'Times New Roman',serif}.page{max-width:800px;margin:auto;background:white;padding:48px;box-sizing:border-box;overflow-wrap:anywhere}p{white-space:pre-wrap;min-height:1em}table{border-collapse:collapse;width:100%;margin:16px 0}td{border:1px solid #cfd6df;padding:8px;vertical-align:top}img{max-width:100%;height:auto}.missing{color:#8b6d45;font:12px system-ui}h1,h2,h3{line-height:1.4}@media(max-width:600px){body{padding:10px}.page{padding:24px}}</style></head><body><article class="page">'''+content+'</article></body></html>'


def preview(body):
    if not str(body.get('filename','')).lower().endswith('.docx'):
        raise ValueError('Word 预览支持 DOCX 文件；旧版 DOC 请先另存为 DOCX 或 PDF。')
    try:
        raw=base64.b64decode(body.get('file',''),validate=True)
    except (ValueError,TypeError,binascii.Error):
        raise ValueError('文档编码无效。')
    if not raw or len(raw)>10*1024*1024:
        raise ValueError('文档必须在 10 MB 以内。')
    prepared,files,warnings=prepare_copy(raw)
    converter=os.environ.get('LABWISE_SOFFICE') or shutil.which('libreoffice') or shutil.which('soffice')
    failure='本机未找到分页转换组件'
    if converter:
        with tempfile.TemporaryDirectory(prefix='labwise-preview-') as temp:
            folder=Path(temp);source=folder/'report.docx';source.write_bytes(prepared)
            profile=folder/'profile';(profile/'user').mkdir(parents=True)
            (profile/'user'/'registrymodifications.xcu').write_text('''<?xml version="1.0" encoding="UTF-8"?><oor:items xmlns:oor="http://openoffice.org/2001/registry"><item oor:path="/org.openoffice.Office.Common/Security/Scripting"><prop oor:name="MacroSecurityLevel" oor:op="fuse"><value>3</value></prop></item><item oor:path="/org.openoffice.Office.Writer/Content/Update"><prop oor:name="Link" oor:op="fuse"><value>2</value></prop><prop oor:name="Field" oor:op="fuse"><value>false</value></prop><prop oor:name="Chart" oor:op="fuse"><value>false</value></prop></item></oor:items>''')
            try:
                result=subprocess.run([converter,'-env:UserInstallation='+profile.as_uri(),'--headless','--norestore','--convert-to','pdf:writer_pdf_Export','--outdir',temp,str(source)],capture_output=True,timeout=60,check=False)
                output=folder/'report.pdf'
                if result.returncode==0 and output.is_file() and 0<output.stat().st_size<=30*1024*1024:
                    pdf=output.read_bytes()
                    if pdf.startswith(b'%PDF-'):
                        return {'file':base64.b64encode(pdf).decode('ascii'),'content_type':'application/pdf','preview_mode':'paged','warnings':warnings}
                failure='此文档的分页转换未完成'
            except subprocess.TimeoutExpired:
                failure='分页转换超时'
            except OSError:
                failure='分页转换组件暂不可用'
    return {'content_type':'text/html','html':readable_preview(files),'preview_mode':'readable',
            'warnings':warnings+[failure+'，已切换为兼容阅读视图；文本、表格和常见图片可阅读，但分页、图表及复杂排版可能不完整。']}
