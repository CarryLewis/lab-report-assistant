"""Offline, instructor-confirmed PDF: source pages, numbered feedback and rubric."""
import base64
import hashlib
import io
import re
import threading
import unicodedata
from collections import defaultdict
from pathlib import Path
from xml.sax.saxutils import escape

from pypdf import PdfReader, PdfWriter, Transformation
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, KeepTogether

INK = colors.HexColor('#243b50')
BLUE = colors.HexColor('#246d9a')
MUTED = colors.HexColor('#617587')
FONT_LOCK = threading.Lock()
MAX_PAGES = 200
MAX_BYTES = 120 * 1024 * 1024


def font_name():
    with FONT_LOCK:
        name = 'LabwiseUnicode'
        if name in pdfmetrics.getRegisteredFontNames():
            return name
        for path in ('/Library/Fonts/Arial Unicode.ttf',
                     '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf'):
            if Path(path).is_file():
                pdfmetrics.registerFont(TTFont(name, path))
                return name
        name = 'STSong-Light'
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(UnicodeCIDFont(name))
        return name


def safe_name(value):
    return re.sub(r'[\\/:*?"<>|\x00-\x1f]', '_', str(value)).strip('. ')[:100] or 'report'


def normalized(value):
    return ''.join(c for c in unicodedata.normalize('NFKC', value)
                   if not c.isspace() and c not in '\u00ad\u200b\ufeff')


def options_check(options):
    options = options or {}
    if not isinstance(options, dict):
        raise ValueError('PDF 导出设置无效。')
    result = {}
    for key in ('highlights', 'rubric', 'annotations'):
        value = options.get(key, True)
        if type(value) is not bool:
            raise ValueError('PDF 导出选项必须为开关值。')
        result[key] = value
    return result


def source_pdf(report, root):
    path = root / 'sources' / (report['id'] + '.bin')
    if not report.get('source_filename') or not path.is_file():
        raise ValueError('缺少原文件，无法导出包含原文的 PDF；请重新导入。')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != report.get('source_sha256'):
        raise ValueError('原文件校验失败，PDF 导出已停止。')
    if report['source_filename'].lower().endswith('.docx'):
        from document_preview import preview
        result = preview({'filename': report['source_filename'], 'file': base64.b64encode(raw).decode()}, require_paged=True)
        if result.get('content_type') != 'application/pdf':
            raise ValueError('PDF 导出需要 Word 分页转换组件 LibreOffice。请安装组件或配置 LABWISE_SOFFICE 后重试。')
        raw = base64.b64decode(result['file'])
        warnings = result.get('warnings', []) + ['Word 由本机分页转换，字体、公式或复杂对象的外观请在预览中核对。']
    elif report['source_filename'].lower().endswith('.pdf'):
        warnings = []
    else:
        raise ValueError('此原文件格式暂不支持 PDF 导出。')
    if len(raw) > 30 * 1024 * 1024:
        raise ValueError('原文 PDF 超过 30 MB，请分批处理。')
    reader = PdfReader(io.BytesIO(raw))
    if reader.is_encrypted or not 0 < len(reader.pages) <= MAX_PAGES:
        raise ValueError('原文 PDF 已加密或超过 200 页，无法导出。')
    # Normalize rotation once so text coordinates and copied page content agree.
    writer = PdfWriter()
    for page in reader.pages:
        added = writer.add_page(page)
        added.transfer_rotation_to_content()
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue(), warnings


def feedback_items(report, package, include_annotations=True):
    items = [dict(item, key='finding:' + item['id']) for item in package['evidence']]
    if include_annotations:
        for item in report.get('annotations', []):
            items.append({'key': 'annotation:' + item['id'], 'title': '教师原文批注',
                          'kind': 'annotation', 'criterion_id': '', 'paragraph_ids': [item.get('paragraph_id')],
                          'source_page': item.get('page') if not item.get('paragraph_id') else None,
                          'quote': item['quote'], 'feedback': item['note']})
    paragraphs = {p['id']: p['text'] for p in report.get('paragraphs', [])}
    for number, item in enumerate(items, 1):
        item['number'] = number
        if not (item.get('quote') or '').strip():
            item['quote'] = '\n'.join(paragraphs[pid] for pid in item['paragraph_ids'] if pid in paragraphs)
    return items


def locate_items(raw, items, report):
    """Only a unique normalized quote/context may produce a visible marker."""
    import pdfplumber
    from visual_discovery import page_geometry
    text, refs, bounds = [], [], []
    with pdfplumber.open(io.BytesIO(raw)) as pdf:
        for number, page in enumerate(pdf.pages):
            box = page_geometry(page)
            bounds.append(box)
            chars = page.crop(tuple(box)).chars
            if len(chars) > 100000:
                raise ValueError('原文页面文字对象过多，无法可靠生成批注。')
            for char in chars:
                value = normalized(char['text'])
                text.append(value)
                refs.extend([(number, char)] * len(value))
    text = ''.join(text)
    paragraphs = {p['id']: p['text'] for p in report.get('paragraphs', [])}

    def occurrences(needle):
        start = 0
        while needle:
            at = text.find(needle, start)
            if at < 0:
                break
            yield at
            start = at + 1

    for item in items:
        needle = normalized(item.get('quote') or '')
        matches = list(occurrences(needle)) if needle else []
        # Legacy PDF annotations already have a page selected by the teacher.
        if item.get('source_page'):
            matches = [at for at in matches if refs[at][0] + 1 == item['source_page']]
        if len(matches) > 1:
            contexts = [normalized(paragraphs.get(pid, '')) for pid in item['paragraph_ids']]
            narrowed = set()
            for context in contexts:
                if not context or needle not in context:
                    continue
                starts = list(occurrences(context))
                if len(starts) == 1:
                    narrowed.update(at for at in matches if starts[0] <= at and at + len(needle) <= starts[0] + len(context))
            if len(narrowed) == 1:
                matches = list(narrowed)
        item['boxes'] = {}
        if len(matches) != 1:
            item['location'] = '需核对位置：' + ('未提供可定位引文' if not needle else '引文重复' if matches else '分页原文中未匹配到引文')
            item['pages'] = []
            continue
        lines = defaultdict(list)
        for page, char in refs[matches[0]:matches[0] + len(needle)]:
            box = bounds[page]
            # Group text lines with a small baseline tolerance, retaining exact glyph bounds.
            key = (page, round(char['top'] / 3))
            lines[key].append((char['x0'] - box[0], char['top'] - box[1],
                               char['x1'] - box[0], char['bottom'] - box[1]))
        for (page, _), chars in lines.items():
            item['boxes'].setdefault(page, []).append([min(c[0] for c in chars), min(c[1] for c in chars),
                                                       max(c[2] for c in chars), max(c[3] for c in chars)])
        item['pages'] = sorted(p + 1 for p in item['boxes'])
        item['location'] = '原文第 ' + '、'.join(map(str, item['pages'])) + ' 页'
    return bounds


def paragraph(value, size=10, color=INK, leading=None):
    # Treat report and teacher text as text, never as ReportLab markup.
    clean = ''.join(c for c in str(value) if c in '\n\t' or ord(c) >= 32)
    style = ParagraphStyle('body', fontName=font_name(), fontSize=size, leading=leading or size * 1.65,
                           textColor=color, spaceAfter=8, wordWrap='CJK', alignment=TA_LEFT,
                           splitLongWords=True)
    return Paragraph(escape(clean).replace('\n', '<br/>'), style)


def text_document(story, label):
    out = io.BytesIO()
    def footer(c, doc):
        c.setFont(font_name(), 8)
        c.setFillColor(MUTED)
        c.drawString(44, 25, 'LABWISE  /  ' + label)
        c.drawRightString(A4[0] - 44, 25, str(doc.page))
    SimpleDocTemplate(out, pagesize=A4, leftMargin=44, rightMargin=44, topMargin=40,
                      bottomMargin=44, title='Labwise 教师已确认评阅').build(story, onFirstPage=footer, onLaterPages=footer)
    return PdfReader(io.BytesIO(out.getvalue()))


def summary(package, items, warnings):
    score = package['score']
    story = [paragraph('LABWISE  /  ASSESSMENT REPORT', 10, BLUE), Spacer(1, 16),
             paragraph('作业评阅报告', 25), paragraph(package['report']['filename'], 14),
             paragraph(package['assignment']['title'], 11, MUTED), Spacer(1, 12),
             paragraph(f"{score['total']:g} / {score['maximum']:g}", 32, BLUE),
             paragraph('教师已确认 · ' + (package['report'].get('student_alias') or '未填写学生姓名'), 10, MUTED)]
    rows = [[paragraph('评分维度', 10), paragraph('得分 / 满分', 10)]]
    rows.extend([paragraph(c['name']), paragraph(f"{c['score']:g} / {c['maximum_points']:g}")]
                 for c in score['criteria'])
    table = Table(rows, colWidths=[390, A4[0] - 478], repeatRows=1, hAlign='LEFT')
    table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#eef4f8')),
                               ('LINEBELOW', (0, 0), (-1, -1), .5, colors.HexColor('#dbe4eb')),
                               ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 10),
                               ('TOPPADDING', (0, 0), (-1, -1), 8)]))
    story += [table, Spacer(1, 18), paragraph('教师总评', 14),
              paragraph(package['final_feedback'] or '教师未填写总评。'), Spacer(1, 12),
              paragraph('阅读指引', 13), paragraph(f'后附原文页面及 {len(items)} 条评语。原文右侧旁批与后面的完整评语使用相同编号；旁批较长时显示节选，完整评语保留原文片段。绿色表示优点，黄色表示改进建议，蓝色表示教师批注。')]
    unresolved = sum(not item['pages'] for item in items)
    if unresolved:
        story.append(paragraph(f'{unresolved} 条评语需核对位置，已保留引文与段落编号，未在原文中猜测标注。', 10, colors.HexColor('#956321')))
    for warning in warnings:
        story.append(paragraph(warning, 9, MUTED))
    story.append(paragraph('确认时间：' + package['confirmation']['confirmed_at'], 9, MUTED))
    return text_document(story, '评分与总评')


def fitted_paragraph(value, width, height, size=9, color=INK):
    """Fit a literal excerpt without shrinking type or losing the full appendix text."""
    value = str(value)
    def make(text):
        block = paragraph(text, size, color, leading=size * 1.45)
        _, measured = block.wrap(width, height)
        return block, measured
    block, measured = make(value)
    if measured <= height:
        return block, measured
    low, high = 0, len(value)
    while low < high:
        middle = (low + high + 1) // 2
        if make(value[:middle].rstrip() + '…')[1] <= height:
            low = middle
        else:
            high = middle - 1
    return make(value[:low].rstrip() + '…')


def sidebar_layout(items, index, source_h, scale, y, top, bottom, width):
    located = [item for item in items if item['boxes'].get(index)]
    located.sort(key=lambda item: (min(box[1] for box in item['boxes'][index]), item['number']))
    # Dense pages retain every full comment in the appendix, with an explicit notice.
    visible = located[:10]
    omitted = len(located) - len(visible)
    bottom += 32 if omitted else 0
    if not visible:
        return [], omitted
    gap = 10
    budget = min(140, (top - bottom - gap * (len(visible) - 1)) / len(visible))
    cards = []
    cursor = top
    for item in visible:
        title, th = fitted_paragraph(f"#{item['number']}  {item['title']}", width - 20, 13.1, 9, BLUE)
        body, bh = fitted_paragraph(item['feedback'], width - 20, budget - th - 34, 9)
        height = th + bh + 34
        boxes = item['boxes'][index]
        quote_y = y + (source_h - min(box[1] for box in boxes)) * scale
        card_top = min(cursor, quote_y + 14)
        cards.append({'item': item, 'top': card_top, 'height': height,
                      'title': title, 'title_height': th, 'body': body, 'body_height': bh,
                      'quote_y': quote_y})
        cursor = card_top - height - gap
    # Push crowded notes upward from the bottom while preserving reading order.
    cursor = bottom
    for card in reversed(cards):
        card['top'] = max(card['top'], cursor + card['height'])
        cursor = card['top'] + gap
    return cards, omitted


def annotated_pages(raw, items, highlights):
    original = PdfReader(io.BytesIO(raw))
    output = PdfWriter()
    # Widen the sheet for notes; retain the same readable source scale as before.
    source_width, height = A4
    width = source_width + 210 if highlights else source_width
    note_x, note_width = source_width - 8, 190
    for index, page in enumerate(original.pages):
        left, bottom, right, top = map(float, page.cropbox)
        source_w, source_h = right - left, top - bottom
        scale = min((source_width - 88) / source_w, (height - 96) / source_h)
        x = (source_width - source_w * scale) / 2
        y = 44 + (height - 96 - source_h * scale) / 2
        sheet = output.add_blank_page(width, height)
        sheet.merge_transformed_page(page, Transformation().translate(-left, -bottom).scale(scale).translate(x, y))
        overlay = io.BytesIO()
        c = canvas.Canvas(overlay, pagesize=(width, height))
        c.setFont(font_name(), 9)
        c.setFillColor(MUTED)
        c.drawString(44, height - 29, f'原文 / 第 {index + 1} 页')
        c.drawRightString(width - 28, 25, f'原文 {index + 1} / {len(original.pages)}')
        c.drawString(44, 25, 'LABWISE  /  原文与对应评语')
        if highlights:
            c.setStrokeColor(colors.HexColor('#dbe4eb'))
            c.line(note_x - 14, 48, note_x - 14, height - 48)
            c.setFillColor(BLUE)
            c.drawString(note_x, height - 29, '旁批 / 编号对应后附完整评语')
            for item in items:
                boxes = item['boxes'].get(index, [])
                tint = '#bde9cd' if item['kind'] == 'strength' else '#c6e2f5' if item['kind'] == 'annotation' else '#ffed9d'
                c.saveState()
                c.setFillColor(colors.HexColor(tint))
                c.setFillAlpha(.43)
                for bx, by, br, bb in boxes:
                    c.rect(x + bx * scale, y + (source_h - bb) * scale,
                           max(2, (br - bx) * scale), (bb - by) * scale, stroke=0, fill=1)
                c.restoreState()
            cards, omitted = sidebar_layout(items, index, source_h, scale, y, height - 54, 54, note_width)
            for card in cards:
                item = card['item']
                card_top, card_height = card['top'], card['height']
                tint = '#edf8f1' if item['kind'] == 'strength' else '#edf5fc' if item['kind'] == 'annotation' else '#fff8e5'
                c.setStrokeColor(colors.HexColor('#adc2d2'))
                c.setLineWidth(.6)
                c.line(source_width - 34, card['quote_y'], note_x, card_top - 12)
                c.setFillColor(colors.HexColor(tint))
                c.roundRect(note_x, card_top - card_height, note_width, card_height, 5, stroke=0, fill=1)
                c.setFillColor(BLUE)
                c.circle(source_width - 34, card['quote_y'], 1.6, stroke=0, fill=1)
                card['title'].drawOn(c, note_x + 10, card_top - 9 - card['title_height'])
                card['body'].drawOn(c, note_x + 10, card_top - 14 - card['title_height'] - card['body_height'])
                c.setFillColor(MUTED)
                c.setFont(font_name(), 7)
                c.drawString(note_x + 10, card_top - card_height + 8, f"完整评语与原文片段见 #{item['number']}")
            if omitted:
                notice = paragraph(f'本页另有 {omitted} 条评语，详见后附完整评语。', 8, MUTED)
                _, nh = notice.wrap(note_width, 32)
                notice.drawOn(c, note_x, 54)
            elif not cards:
                notice = paragraph('本页没有可准确定位的旁批。完整评语及需核对位置的引文见后附评语页。', 9, MUTED)
                _, nh = notice.wrap(note_width, height)
                notice.drawOn(c, note_x, height - 64 - nh)
        c.save()
        sheet.merge_page(PdfReader(io.BytesIO(overlay.getvalue())).pages[0])
    return output


def comments(package, items, include_rubric):
    criteria = {c['id']: c for c in package['score']['criteria']}
    story = [paragraph('逐条评语', 22), paragraph('编号与前面的原文标记一致。以下仅包含教师确认采纳的建议及所选原文批注。', 10, MUTED)]
    if not items:
        story.append(paragraph('本次评阅没有逐条评语。请参阅评分与教师总评。'))
    for item in items:
        kind = '优点' if item['kind'] == 'strength' else '教师批注' if item['kind'] == 'annotation' else '改进建议'
        criterion = criteria.get(item['criterion_id'], {}).get('name', '')
        pids = '、'.join(str(pid) for pid in item['paragraph_ids'] if pid)
        entry = [Spacer(1, 9), paragraph(f"#{item['number']}  {item['title']}", 13, BLUE),
                 paragraph(' · '.join(filter(None, [kind, criterion, item['location'], pids])), 9, MUTED)]
        if item.get('quote'):
            entry.append(paragraph('原文片段：' + item['quote'], 10, MUTED))
        entry.append(paragraph(item['feedback']))
        story.append(KeepTogether(entry))
    if include_rubric:
        story += [PageBreak(), paragraph('评分细则', 22),
                  paragraph(package['assignment']['rubric_name'] + ' · v' + str(package['assignment']['rubric_version']), 10, MUTED)]
        for criterion in package['score']['criteria']:
            story.append(KeepTogether([Spacer(1, 12), paragraph(criterion['name'], 14, BLUE),
                                       paragraph(f"{criterion['score']:g} / {criterion['maximum_points']:g}", 19)]))
            story.append(paragraph(criterion.get('descriptor') or '该维度未填写文字评分细则。'))
    return text_document(story, '逐条评语与评分细则')


def build(report, root, options=None):
    from pilot_backend import feedback_package
    package = feedback_package(report)  # Reject drafts before reading/converting source.
    opts = options_check(options)
    raw, warnings = source_pdf(report, root)
    items = feedback_items(report, package, opts['annotations'])
    locate_items(raw, items, report)
    if not opts['highlights']:
        warnings.append('已关闭原文高亮、编号与旁批；请通过评语中的原文页码和引句对照阅读。')
    output = PdfWriter()
    output.append(summary(package, items, warnings), import_outline=False)
    source_start = len(output.pages)
    marked = annotated_pages(raw, items, opts['highlights'])
    for page in marked.pages:
        output.add_page(page)
    comment_start = len(output.pages)
    output.append(comments(package, items, opts['rubric']), import_outline=False)
    output.add_outline_item('评分与教师总评', 0)
    source_outline = output.add_outline_item('原文与旁批', source_start)
    for index in range(len(marked.pages)):
        output.add_outline_item('原文第 ' + str(index + 1) + ' 页', source_start + index, parent=source_outline)
    output.add_outline_item('逐条评语' + ('与评分细则' if opts['rubric'] else ''), comment_start)
    for number, page in enumerate(output.pages, 1):
        footer = io.BytesIO()
        page_size = (float(page.mediabox.width), float(page.mediabox.height))
        c = canvas.Canvas(footer, pagesize=page_size)
        c.setFont(font_name(), 8)
        c.setFillColor(MUTED)
        c.drawCentredString(page_size[0] / 2, 25, f'评阅报告 {number} / {len(output.pages)}')
        c.save()
        page.merge_page(PdfReader(io.BytesIO(footer.getvalue())).pages[0])
    output.add_metadata({'/Title': report['filename'] + ' · 教师评阅', '/Author': 'Labwise', '/Subject': '教师已确认评分与反馈'})
    result = io.BytesIO()
    output.write(result)
    if result.tell() > MAX_BYTES:
        raise ValueError('PDF 超过 120 MB，请分批导出。')
    return result.getvalue(), {'pages': len(output.pages), 'source_pages': len(marked.pages),
                              'comments': len(items), 'unlocated': sum(not item['pages'] for item in items),
                              'warnings': warnings}


def export(reports, root, title, options=None):
    if not reports:
        raise ValueError('没有可导出的作业。')
    if len(reports) > 200:
        raise ValueError('单次最多导出 200 份作业。')
    if any(not report.get('confirmed') for report in reports):
        raise ValueError('请先完成全部作业的教师确认，再合并导出 PDF。')
    options_check(options)
    source_total = sum((root / 'sources' / (r['id'] + '.bin')).stat().st_size
                       for r in reports if (root / 'sources' / (r['id'] + '.bin')).is_file())
    if source_total > MAX_BYTES:
        raise ValueError('原文件总量超过 120 MB，请按学生分别导出。')
    combined = PdfWriter()
    details = []
    generated_size = 0
    for report in sorted(reports, key=lambda r: (r.get('student_alias', ''), r['filename'], r['id'])):
        raw, info = build(report, root, options)
        generated_size += len(raw)
        if generated_size > MAX_BYTES:
            raise ValueError('合并 PDF 超过 120 MB，请按学生分别导出。')
        combined.append(PdfReader(io.BytesIO(raw)), outline_item=report.get('student_alias') or report['filename'])
        details.append({'filename': report['filename'], **info})
        if len(combined.pages) > 2000:
            raise ValueError('合并结果超过 2000 页，请按学生分别导出。')
    output = io.BytesIO()
    combined.add_metadata({'/Title': str(title) + ' · 已批改作业', '/Author': 'Labwise'})
    combined.write(output)
    if output.tell() > MAX_BYTES:
        raise ValueError('合并 PDF 超过 120 MB，请按学生分别导出。')
    return {'filename': safe_name(Path(title).stem) + '-reviewed.pdf', 'encoding': 'base64',
            'content_type': 'application/pdf', 'content': base64.b64encode(output.getvalue()).decode(),
            'summary': {'reports': len(reports), 'pages': len(combined.pages),
                        'comments': sum(d['comments'] for d in details),
                        'unlocated': sum(d['unlocated'] for d in details), 'details': details}}
