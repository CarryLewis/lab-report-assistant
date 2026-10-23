"""Local rubric-text extraction. Never invent missing scores or call a model."""
import base64
import re
from pathlib import Path

# Accept explicit criterion maxima; grade ranges are not interpreted as maxima.
SCORED = re.compile(r'^(.+?)\s*(?:[（(]\s*(\d+(?:\.\d+)?)\s*(分|marks?|points?|%)\s*[）)]|[:：|]\s*(\d+(?:\.\d+)?)\s*(分|marks?|points?|%)?|\s+(\d+(?:\.\d+)?)\s*(分|marks?|points?|%))\s*(?:[-—:：，,;；]\s*(.*))?$', re.I)
TOTAL = re.compile(r'^(总分|合计|满分|total(?:\s+(?:marks|points|score))?)(?:\s|[:：（(]|$)', re.I)


def parse_source(source):
    if not isinstance(source,str) or len(source)>50000:
        raise ValueError('评分细则请控制在 50,000 字符以内。')
    source=source.strip()
    criteria=[]
    intro=[]
    units=set()
    unresolved=[]
    declared_total=None
    lines=[line.strip() for line in source.splitlines() if line.strip()]
    combined=[]
    i=0
    while i<len(lines):
        # Join adjacent criterion/score cells from document tables, only when
        # the score has an explicit unit; plain numbers remain ambiguous.
        if i+1<len(lines) and not SCORED.match(lines[i]) and re.fullmatch(r'[（(]?\s*\d+(?:\.\d+)?\s*(分|marks?|points?|%)\s*[）)]?',lines[i+1],re.I):
            score=lines[i+1].strip('（）() ')
            combined.append(lines[i]+'：'+score)
            i+=2
        else:
            combined.append(lines[i])
            i+=1
    for original in combined:
        line=re.sub(r'^\s*(?:[-*•]\s*|\d+[.、)]\s*)','',original.strip())
        if not line:
            continue
        if TOTAL.match(line):
            values=re.findall(r'\d+(?:\.\d+)?',line)
            if len(values)==1:
                declared_total=float(values[0])
            continue
        match=SCORED.match(line)
        # PDF and Word tables often put the maximum in a separate paragraph.
        score_only=re.fullmatch(r'(\d+(?:\.\d+)?)\s*(分|marks?|points?|%)',line,re.I)
        if score_only and intro and not criteria:
            line=intro.pop()+'：'+line
            match=SCORED.match(line)
        elif score_only and criteria:
            unresolved.append(original)
        if match:
            groups=match.groups()
            name=groups[0].strip(' -—:：|')
            if re.search(r'\d\s*[-–—]\s*$',name) or re.match(r'^(excellent|good|pass|fail|优秀|良好|及格)\b',name,re.I):
                unresolved.append(original)
                continue
            score=float(groups[1] or groups[3] or groups[5])
            unit=(groups[2] or groups[4] or groups[6] or '分').lower()
            units.add('%' if unit=='%' else 'points')
            if not name or score<=0 or score>10000:
                unresolved.append(original)
                continue
            criteria.append({'id':'criterion_'+str(len(criteria)+1),'name':name[:200],'maximum_points':score,'descriptor':groups[7] or ''})
        elif criteria:
            # A line that looks like another scored item must not silently become a descriptor.
            if re.search(r'\d+\s*(?:分|marks?|points?|%)',line,re.I) and not re.search(r'\d\s*[-–—]\s*\d',line):
                unresolved.append(original)
            criteria[-1]['descriptor']+='\n'+line
        else:
            intro.append(line)
    errors=[]
    if not source:
        errors.append('请上传文件，或粘贴评分细则。')
    elif not criteria:
        errors.append('还没有识别到各项分值。请在每项名称后补充满分，例如“实验方法（30分）”。')
    if unresolved:
        errors.append('有部分分值未能确定，请核对后调整对应文字：'+ '；'.join(unresolved[:3]))
    if len(units)>1:
        errors.append('发现百分比和分数混用，请统一分值的表达方式后保存。')
    if len(criteria)>30:
        errors.append('评分项目超过 30 项，请合并后保存。')
    total=sum(x['maximum_points'] for x in criteria)
    if declared_total is not None and abs(total-declared_total)>.01:
        errors.append(f'识别到的各项分值合计为 {total:g}，与原文总分 {declared_total:g} 不一致，请核对。')
    for c in criteria:
        c['descriptor']=c['descriptor'].strip()
        if len(c['descriptor'])>4000:
            errors.append('单项评分描述过长，请精简后保存。')
    return {'source_text':source,'criteria':criteria,'total':total,'ready':bool(criteria) and not errors,'messages':errors,'percentage':'%' in units}


def extract(body):
    source=body.get('source_text','')
    filename=''
    if body.get('file'):
        from pilot_backend import paragraphs_docx,paragraphs_pdf
        filename=Path(str(body.get('filename',''))).name
        if len(filename)>200:
            raise ValueError('文件名称过长，请重命名后导入。')
        try:
            raw=base64.b64decode(body['file'],validate=True)
        except (ValueError,TypeError):
            raise ValueError('文件读取失败，请重新选择。')
        suffix=Path(filename).suffix.lower()
        if suffix=='.docx':
            paragraphs=paragraphs_docx(raw)
        elif suffix=='.pdf':
            paragraphs=paragraphs_pdf(raw)
        else:
            raise ValueError('请选择 Word（.docx）或 PDF 文件；旧版 .doc 请先另存为 .docx。')
        source='\n'.join(p['text'] for p in paragraphs)
    result=parse_source(source)
    result['filename']=filename
    return result
