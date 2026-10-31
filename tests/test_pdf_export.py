import base64
import copy
import hashlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
import pdf_export as pdf
import pilot_backend as backend


class PdfExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'sources').mkdir()
        data = io.BytesIO()
        c = canvas.Canvas(data)
        c.drawString(60, 730, 'Each measurement was performed once.')
        c.drawString(60, 700, 'Growth increased from 0.08 to 0.72.')
        c.drawString(60, 670, 'Repeated evidence.')
        c.drawString(60, 640, 'Repeated evidence.')
        c.save()
        raw = data.getvalue()
        self.report = {'id': 'fictional', 'filename': '虚构实验.docx', 'source_filename': 'original.pdf',
                       'source_sha256': hashlib.sha256(raw).hexdigest(), 'student_alias': '演示学生',
                       'confirmed': True, 'confirmed_at': '2026-10-26T00:00:00+00:00', 'updated': '',
                       'revision': 1, 'notes': 'PRIVATE_TEACHER_NOTE', 'feedback': '请补充重复测量，并说明结论的限制。',
                       'assignment': {'id': 'task', 'title': '生长曲线实验', 'rubric': {
                           'name': '实验评分标准', 'version': '1', 'criteria': [
                               {'id': 'methods', 'name': '实验方法', 'maximum_points': 10, 'descriptor': '写明重复次数与校准方法。'}]}},
                       'scores': {'methods': 7}, 'reviews': {'1': 'edited', '2': 'rejected'},
                       'suggestion_edits': {'1': 'TEACHER_EDITED 建议增加生物学重复。'},
                       'paragraphs': [{'id': 'p1', 'text': 'Each measurement was performed once.'}],
                       'analysis': {'findings': [
                           {'id': '1', 'title': '重复测量', 'kind': 'issue', 'criterion_id': 'methods', 'paragraph_ids': ['p1'], 'quote': 'Each measurement was performed once', 'feedback': 'OLD_AI_FEEDBACK'},
                           {'id': '2', 'title': 'REJECTED_TITLE', 'kind': 'issue', 'criterion_id': 'methods', 'paragraph_ids': ['p1'], 'quote': 'Each measurement', 'feedback': 'REJECTED_FEEDBACK'}]},
                       'annotations': [{'id': 'note1', 'page': 1, 'quote': 'Growth increased', 'note': 'TEACHER_ANNOTATION 结果表达清楚。'}]}
        (self.root / 'sources' / 'fictional.bin').write_bytes(raw)

    def tearDown(self):
        self.temp.cleanup()

    def test_confirmed_pdf_preserves_source_and_student_feedback_only(self):
        raw, info = pdf.build(self.report, self.root)
        reader = PdfReader(io.BytesIO(raw))
        text = '\n'.join(p.extract_text() for p in reader.pages)
        self.assertIn('7 / 10', text)
        self.assertIn('TEACHER_EDITED', text)
        self.assertIn('TEACHER_ANNOTATION', text)
        for private in ('PRIVATE_TEACHER_NOTE', 'REJECTED_FEEDBACK', 'REJECTED_TITLE', 'OLD_AI_FEEDBACK'):
            self.assertNotIn(private, text)
        self.assertIn('Each measurement was performed once.', reader.pages[1].extract_text())
        self.assertEqual(info['source_pages'], 1)
        self.assertEqual(info['unlocated'], 0)
        self.assertEqual(info['comments'], 2)
        self.assertTrue(reader.outline)

    def test_margin_comments_and_quoted_appendix_share_numbers(self):
        raw, _ = pdf.build(self.report, self.root)
        reader = PdfReader(io.BytesIO(raw))
        source = reader.pages[1]
        self.assertGreater(float(source.mediabox.width), 780)
        margin_text = source.extract_text()
        for value in ('#1', '#2', 'TEACHER_EDITED', 'TEACHER_ANNOTATION', '旁批'):
            self.assertIn(value, margin_text)
        appendix = '\n'.join(page.extract_text() for page in reader.pages[2:])
        for value in ('原文片段：', 'Each measurement was performed once', 'Growth increased', 'TEACHER_EDITED'):
            self.assertIn(value, appendix)
        raw, _ = pdf.build(self.report, self.root, {'highlights': False})
        source = PdfReader(io.BytesIO(raw)).pages[1]
        self.assertAlmostEqual(float(source.mediabox.width), pdf.A4[0], places=3)
        self.assertNotIn('TEACHER_EDITED', source.extract_text())

    def test_dense_margin_layout_is_bounded_and_full_feedback_is_preserved(self):
        note = '建议补充测量方法、数据依据以及结论的适用条件。' * 100
        self.report['annotations'] = [dict(self.report['annotations'][0], id=f'n{i}', note=f'NOTE_{i} ' + note)
                                      for i in range(15)]
        raw, _ = pdf.build(self.report, self.root)
        reader = PdfReader(io.BytesIO(raw))
        self.assertIn('另有 6 条评语', reader.pages[1].extract_text())
        appendix = '\n'.join(page.extract_text() for page in reader.pages[2:])
        for i in range(15):
            self.assertIn(f'NOTE_{i} ', appendix)
        items = pdf.feedback_items(self.report, backend.feedback_package(self.report))
        original = (self.root / 'sources/fictional.bin').read_bytes()
        pdf.locate_items(original, items, self.report)
        cards, omitted = pdf.sidebar_layout(items, 0, 842, .88, 44, 788, 54, 190)
        self.assertEqual(omitted, 6)
        last_bottom = 788
        for card in cards:
            self.assertLessEqual(card['top'], last_bottom + .01)
            self.assertGreaterEqual(card['top'] - card['height'], 86)
            last_bottom = card['top'] - card['height'] - 10

    def test_missing_quote_uses_source_paragraph_in_full_comments(self):
        self.report['analysis']['findings'][0]['quote'] = ''
        raw, info = pdf.build(self.report, self.root)
        self.assertEqual(info['unlocated'], 0)
        appendix = '\n'.join(p.extract_text() for p in PdfReader(io.BytesIO(raw)).pages[2:])
        self.assertIn('原文片段：Each measurement was performed once.', appendix)

    def test_drafts_missing_and_changed_source_fail(self):
        draft = dict(self.report, confirmed=False)
        with self.assertRaisesRegex(ValueError, '教师确认'):
            pdf.build(draft, self.root)
        with self.assertRaisesRegex(ValueError, '校验失败'):
            pdf.build(dict(self.report, source_sha256='wrong'), self.root)
        (self.root / 'sources' / 'fictional.bin').unlink()
        with self.assertRaisesRegex(ValueError, '缺少原文件'):
            pdf.build(self.report, self.root)

    def test_repeated_missing_and_image_quotes_remain_unlocated(self):
        raw = (self.root / 'sources' / 'fictional.bin').read_bytes()
        items = [{'paragraph_ids': [], 'quote': q} for q in ('Repeated evidence.', 'Absent quote', '')]
        pdf.locate_items(raw, items, self.report)
        self.assertTrue(all(not item['pages'] and not item['boxes'] for item in items))
        self.assertIn('引文重复', items[0]['location'])

    def test_options_omit_annotations_and_rubric_and_visible_markers(self):
        raw, info = pdf.build(self.report, self.root, {'annotations': False, 'rubric': False, 'highlights': False})
        text = '\n'.join(p.extract_text() for p in PdfReader(io.BytesIO(raw)).pages)
        self.assertNotIn('TEACHER_ANNOTATION', text)
        self.assertNotIn('写明重复次数与校准方法。', text)
        self.assertEqual(info['comments'], 1)
        with self.assertRaises(ValueError):
            pdf.options_check({'annotations': 'false'})

    def test_word_requires_paged_converter(self):
        report = dict(self.report, source_filename='original.docx')
        with patch('document_preview.preview', return_value={'content_type': 'text/html'}) as convert:
            with self.assertRaisesRegex(ValueError, 'LibreOffice'):
                pdf.build(report, self.root)
            self.assertTrue(convert.call_args.kwargs['require_paged'])

    def test_rotated_source_still_locates(self):
        path = self.root / 'sources' / 'fictional.bin'
        reader = PdfReader(io.BytesIO(path.read_bytes()))
        writer = PdfWriter()
        writer.add_page(reader.pages[0].rotate(90))
        out = io.BytesIO(); writer.write(out); path.write_bytes(out.getvalue())
        report = dict(self.report, source_sha256=hashlib.sha256(out.getvalue()).hexdigest())
        _, info = pdf.build(report, self.root)
        self.assertEqual(info['unlocated'], 0)

    def test_batch_and_endpoints_reject_stale_revision_without_mutation(self):
        with patch.object(backend, 'DATA', self.root):
            backend.init()
            with backend.db() as c:
                backend.persist(c, self.report)
            route = '/api/pilot/reports/fictional/export-pdf'
            with self.assertRaisesRegex(ValueError, '已有更新'):
                backend.dispatch('POST', route, {'revision': 0}, None)
            pack = backend.dispatch('POST', route, {'revision': 1, 'options': {'rubric': False}}, None)
            self.assertTrue(base64.b64decode(pack['content']).startswith(b'%PDF-'))
            self.assertEqual(pack['summary']['reports'], 1)
            batch = backend.dispatch('GET', '/api/pilot/assignments/task/export-pdf', {}, None)
            self.assertEqual(batch['summary']['reports'], 1)
            saved = backend.dispatch('GET', '/api/pilot/reports/fictional', {}, None)
            self.assertTrue(saved['confirmed'])
            self.assertEqual(saved['revision'], 1)
        second = copy.deepcopy(self.report)
        second['id'] = 'second'
        (self.root / 'sources' / 'second.bin').write_bytes((self.root / 'sources' / 'fictional.bin').read_bytes())
        pack = pdf.export([second, self.report], self.root, '全班')
        self.assertEqual(pack['summary']['reports'], 2)
        self.assertEqual(pack['summary']['comments'], 4)
        second['confirmed'] = False
        with self.assertRaisesRegex(ValueError, '全部作业'):
            pdf.export([self.report, second], self.root, '全班')


if __name__ == '__main__':
    unittest.main()
