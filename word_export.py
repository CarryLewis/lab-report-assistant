"""Review packages preserve the original DOCX and add native Word comments to a copy."""
import base64
import csv
import hashlib
import io
import json
import re
import threading
import zipfile
import xml.etree.ElementTree as E
from pathlib import Path
import word_source

W=word_source.W
REL='http://schemas.openxmlformats.org/package/2006/relationships'
CT='http://schemas.openxmlformats.org/package/2006/content-types'
COMMENTS='http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments'


_XML_LOCK=threading.Lock()

def xml_bytes(root, original=b''):
    with _XML_LOCK:
        return _xml_bytes(root,original)

def _xml_bytes(root, original=b''):
    declarations={}
    if original:
        for _,(prefix,uri) in E.iterparse(io.BytesIO(original),events=('start-ns',)):
            if prefix not in declarations:declarations[prefix]=uri
    for prefix,uri in declarations.items():
        if prefix!='xml' and not re.fullmatch(r'ns\d+',prefix):
            try:E.register_namespace(prefix,uri)
            except ValueError:pass
    result=E.tostring(root,encoding='utf-8',xml_declaration=True)
    # Compatibility attributes contain prefix values (mc:Ignorable, Requires).
    # Preserve those declarations even if ElementTree did not use the namespace.
    for prefix,uri in declarations.items():
        if prefix and prefix!='xml' and ('xmlns:'+prefix+'=').encode() not in result:
            root.set('xmlns:'+prefix,uri)
    return E.tostring(root,encoding='utf-8',xml_declaration=True)


def marked_word(raw, report, package):
    files=word_source.package(raw);root=E.fromstring(files['word/document.xml']);paragraphs=list(root.iter('{'+W+'}p'))
    source_hash=hashlib.sha256(raw).hexdigest()
    relpath='word/_rels/document.xml.rels';rels=E.fromstring(files.get(relpath,('<Relationships xmlns="'+REL+'"/>').encode()))
    existing=next((r for r in rels if r.get('Type')==COMMENTS),None)
    if existing is not None:
        import posixpath
        comment_path=posixpath.normpath(posixpath.join('word',existing.get('Target','comments.xml')))
        if existing.get('TargetMode','').lower()=='external' or not comment_path.startswith('word/'):
            raise ValueError('原 Word 的批注关系无效，请在 Word 中另存为 DOCX 后提交。')
    else:
        comment_path='word/comments.xml'
        ids={r.get('Id') for r in rels};rid='labwiseComments';i=1
        while rid in ids:rid='labwiseComments'+str(i);i+=1
        E.SubElement(rels,'{'+REL+'}Relationship',{'Id':rid,'Type':COMMENTS,'Target':'comments.xml'})
    comments=E.fromstring(files.get(comment_path,('<w:comments xmlns:w="'+W+'"/>').encode()))
    ids=[int(n.get('{'+W+'}id','-1')) for n in root.iter() if n.tag in ('{'+W+'}commentRangeStart','{'+W+'}commentReference')]
    ids.extend(int(n.get('{'+W+'}id','-1')) for n in comments if n.get('{'+W+'}id','').isdigit())
    next_id=max(ids,default=-1)+1;anchors=[]
    native={p['id']:p for p in report['paragraphs']}
    def locate(pid,quote):
        p=native.get(pid,{})
        anchor=p.get('anchor',{})
        if anchor.get('source_sha256')==source_hash and anchor.get('part')=='word/document.xml':
            index=anchor.get('paragraph_index')
            if type(index) is int and 0<=index<len(paragraphs):
                if quote and quote not in word_source.paragraph_text(paragraphs[index]):
                    raise ValueError('反馈引文与原 Word 段落不一致，未导出错误批注。')
                return index
        # Older reports lack immutable indices. Ambiguous text must be relinked, never guessed.
        needle=quote or p.get('text','')
        matches=[i for i,node in enumerate(paragraphs) if needle and needle in word_source.paragraph_text(node)]
        if len(matches)!=1:raise ValueError('历史批注无法唯一定位到 Word，请重新导入 Word 后核对。')
        return matches[0]
    def add(index,content,key):
        nonlocal next_id
        ident=str(next_id);next_id+=1;p=paragraphs[index]
        start=E.Element('{'+W+'}commentRangeStart',{'{'+W+'}id':ident});end=E.Element('{'+W+'}commentRangeEnd',{'{'+W+'}id':ident})
        p.insert(1 if len(p) and p[0].tag=='{'+W+'}pPr' else 0,start);p.append(end)
        reference=E.SubElement(p,'{'+W+'}r');E.SubElement(reference,'{'+W+'}commentReference',{'{'+W+'}id':ident})
        comment=E.SubElement(comments,'{'+W+'}comment',{'{'+W+'}id':ident,'{'+W+'}author':'Labwise · Teacher','{'+W+'}initials':'LW','{'+W+'}date':package['confirmation']['confirmed_at']})
        for line in content.splitlines():
            cp=E.SubElement(comment,'{'+W+'}p');run=E.SubElement(cp,'{'+W+'}r');t=E.SubElement(run,'{'+W+'}t');t.text=line
        anchors.append({'key':key,'word_paragraph_index':index,'comment_id':ident,'range':'paragraph'})
    for item in package['evidence']:
        index=locate(item['paragraph_ids'][0],item['quote'])
        add(index,'#'+item['id']+' · '+item['title']+'\n'+('原文：'+item['quote']+'\n' if item['quote'] else '')+item['feedback'],'finding:'+item['id'])
    for item in report.get('annotations',[]):
        add(locate(item.get('paragraph_id'),item['quote']),'原文批注\n'+item['quote']+'\n'+item['note'],'annotation:'+item['id'])
    # Summary is a comment, not appended body text: original page layout is retained.
    score=package['score'];summary=['评分总览',f"总分：{score['total']:g} / {score['maximum']:g}"]
    summary.extend(f"{c['name']}：{c['score']:g} / {c['maximum_points']:g}" for c in score['criteria'])
    if package['final_feedback']:summary.extend(['教师总评',package['final_feedback']])
    first=next((i for i,p in enumerate(paragraphs) if word_source.paragraph_text(p)),0)
    add(first,'\n'.join(summary),'score-summary')
    files['word/document.xml']=xml_bytes(root,files['word/document.xml']);files[comment_path]=xml_bytes(comments,files.get(comment_path,b''))
    files[relpath]=xml_bytes(rels,files.get(relpath,b''))
    types=E.fromstring(files['[Content_Types].xml'])
    if not any(n.get('PartName')=='/'+comment_path for n in types):E.SubElement(types,'{'+CT+'}Override',{'PartName':'/'+comment_path,'ContentType':'application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml'})
    files['[Content_Types].xml']=xml_bytes(types,files['[Content_Types].xml'])
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
        for name,data in files.items():archive.writestr(name,data)
    return output.getvalue(),anchors


def bundle(reports,root,title):
    from pilot_backend import feedback_package,feedback_html
    if not reports:raise ValueError('此作业题没有可导出的作业。')
    if any(not r.get('confirmed') for r in reports):raise ValueError('请先完成本题全部作业的评分确认，再一键导出。')
    if len(reports)>200:raise ValueError('单次导出最多 200 份作业。')
    output=io.BytesIO();packages=[];rows=[];source_total=0
    def safe(value):return re.sub(r'[\\/:*?"<>|\x00-\x1f]','_',value).strip('. ')[:100] or 'report'
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
        for r in reports:
            if not r.get('source_filename','').lower().endswith('.docx'):raise ValueError('本题含历史 PDF，请归档该记录或重新提交 Word 后导出。')
            raw=(root/'sources'/(r['id']+'.bin')).read_bytes();source_total+=len(raw)
            if source_total>120*1024*1024:raise ValueError('导出文件总量超过 120 MB，请分批处理。')
            if hashlib.sha256(raw).hexdigest()!=r.get('source_sha256'):raise ValueError('原 Word 文件校验失败，导出已中止。')
            package=feedback_package(r);annotated,anchors=marked_word(raw,r,package)
            package['word_anchors']=anchors;package['analysis_coverage']=(r.get('analysis') or {}).get('coverage');package['visual_checks']=(r.get('analysis') or {}).get('visual_checks',[]);package['source_sha256']=r['source_sha256'];package['annotations']=r.get('annotations',[])
            stem=safe(Path(r['filename']).stem)+'-'+r['id'][:8]
            archive.writestr('originals/'+stem+'.docx',raw);archive.writestr('reviewed/'+stem+'-reviewed.docx',annotated)
            archive.writestr('feedback/'+stem+'.html',feedback_html(package))
            score=package['score'];rows.append([r.get('student_alias',''),r['filename'],r['assignment']['title'],score['total'],score['maximum'],json.dumps(score['criteria'],ensure_ascii=False),r.get('confirmed_at') or r['updated']]);packages.append(package)
        csv_data=io.StringIO();writer=csv.writer(csv_data);writer.writerow(['Student','File','Assignment','Score','Maximum','Criterion scores','Confirmed at'])
        # Prevent spreadsheet formula evaluation of user-provided labels.
        for row in rows:writer.writerow(["'"+v if isinstance(v,str) and v.lstrip().startswith(('=','+','-','@')) else v for v in row])
        archive.writestr('scores.csv','\ufeff'+csv_data.getvalue());archive.writestr('feedback.json',json.dumps(packages,ensure_ascii=False,indent=2))
        archive.writestr('README.txt','Original Word files are preserved in originals/. Reviewed copies contain native Word paragraph comments and a grading summary comment. Open in Word and enable Review > Show Comments. Paragraph anchors and scores are in feedback.json. Private teacher notes are excluded. This is a Labwise export, not a native Turnitin import package.\n')
    return {'filename':safe(title)+'-review-package.zip','encoding':'base64','content_type':'application/zip','content':base64.b64encode(output.getvalue()).decode()}
