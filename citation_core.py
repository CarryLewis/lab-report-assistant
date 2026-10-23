"""Phase-one deterministic author/year citation extraction; no model calls."""
import hashlib
import re

YEAR = r'(?:19|20)\d{2}[a-z]?'
AUTHOR = r'[A-Z][A-Za-z’\-]+(?:\s+(?:Health|Organization|World|et al\.|and|[A-Z][A-Za-z’\-]+|&))*'
PATTERN = re.compile(r'(?P<author>' + AUTHOR + r'),?\s*\(?(?P<year>' + YEAR + r')\)?')


def inspect(paragraphs, style='unspecified', completeness='complete'):
    if style not in ('unspecified', 'apa-7') or completeness not in ('complete', 'fragment'):
        raise ValueError('不支持的引用样式或输入完整性。')
    references, citations, issues = [], [], []
    in_refs = False
    for p in paragraphs:
        value = p['text'].strip()
        if re.fullmatch(r'(?:\d+[.\s]*)?(?:references|bibliography|参考文献)', value, re.I):
            in_refs = True
            continue
        if in_refs:
            year = re.search(YEAR, value)
            doi = re.search(r'10\.\d{4,9}/[^\s]+', value)
            ref = {'id': 'ref-' + p['id'], 'paragraph_id': p['id'], 'text': value, 'author': value.split(',')[0].strip(), 'year': year.group() if year else None, 'doi': doi.group().rstrip('.,;') if doi else None, 'format_issues': []}
            if not year:
                ref['format_issues'].append('未识别到出版年份，需人工核对。')
            if style == 'apa-7' and year and not re.search(r'\(' + year.group() + r'\)\.', value):
                ref['format_issues'].append('APA 7 基础规则：年份应置于括号内并后接句点。')
            if style == 'apa-7' and doi and 'https://doi.org/' not in value:
                ref['format_issues'].append('APA 7 基础规则：DOI 应写为 https://doi.org/… URL。')
            references.append(ref)
        else:
            for match in PATTERN.finditer(value):
                author = match['author'].strip()
                citations.append({'id': f"cit-{p['id']}-{match.start()}", 'paragraph_id': p['id'], 'start': match.start(), 'end': match.end(), 'text': match.group(), 'author': author, 'year': match['year'], 'context': value, 'reference_ids': []})
    used = set()
    for citation in citations:
        candidates = [r['id'] for r in references if r['year'] == citation['year'] and r['author'].lower().split()[0] == citation['author'].lower().split()[0]]
        citation['reference_ids'] = candidates
        citation['link_status'] = 'matched' if len(candidates) == 1 else 'ambiguous' if candidates else 'unresolved'
        used.update(candidates)
    for ref in references:
        if ref['id'] not in used:
            issues.append({'kind': 'unused_reference', 'reference_id': ref['id']})
        if ref['doi'] and sum(r['doi'] == ref['doi'] for r in references) > 1:
            issues.append({'kind': 'duplicate_doi', 'reference_id': ref['id']})
    return {'schema_version': '1.0', 'parser_version': 'author-year-basic-1', 'source_hash': hashlib.sha256(str(paragraphs).encode()).hexdigest(), 'style': style, 'completeness': completeness, 'citations': citations, 'references': references, 'issues': issues, 'limitations': ['基础作者—年份识别；编号制、ibid、跨段参考条目和完整 CSL 排版尚未支持。', '未匹配表示当前输入中未确认对应来源；片段输入不能据此判定原报告漏列。', '内容支持尚未分析。']}
