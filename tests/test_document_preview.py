import base64
import io
import subprocess
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from document_preview import preview, prepare_copy, converter_path


class DocumentPreviewTests(unittest.TestCase):
    def test_frozen_app_prefers_bundled_converter_over_system(self):
        with tempfile.TemporaryDirectory() as folder:
            contents = Path(folder).resolve() / 'Labwise 中文.app/Contents'
            bundled = contents / 'Helpers/LibreOffice.app/Contents/MacOS/soffice'
            bundled.parent.mkdir(parents=True)
            bundled.write_text('#!/bin/sh\nexit 0\n')
            bundled.chmod(0o755)
            with patch.dict(os.environ, {'LABWISE_SOFFICE': ''}), patch('document_preview.sys.frozen', True, create=True), patch('document_preview.sys.executable', str(contents / 'MacOS/Labwise')), patch('document_preview.shutil.which', return_value='/system/soffice') as which:
                self.assertEqual(converter_path(), str(bundled))
                which.assert_not_called()
                with patch.dict(os.environ, {'LABWISE_SOFFICE': '/missing/override'}):
                    which.return_value = None
                    self.assertIsNone(converter_path())
                which.return_value = '/system/soffice'
                bundled.unlink()
                self.assertEqual(converter_path(), '/system/soffice')

    def test_rejects_wrong_type_and_invalid_file(self):
        for body in ({'filename': 'x.pdf'}, {'filename': 'x.docx', 'file': '!'},
                     {'filename': 'x.docx', 'file': base64.b64encode(b'not zip').decode()}):
            with self.assertRaises(ValueError):
                preview(body)

    def test_missing_converter_has_explicit_compatibility_preview(self):
        data = io.BytesIO()
        with zipfile.ZipFile(data, 'w') as archive:
            archive.writestr('word/document.xml', '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Test content</w:t></w:r></w:p></w:body></w:document>')
        with patch('document_preview.converter_path', return_value=None):
            result=preview({'filename': 'x.docx', 'file': base64.b64encode(data.getvalue()).decode()})
        self.assertEqual(result['preview_mode'],'readable')
        self.assertIn('Test content',result['html'])
        self.assertTrue(result['warnings'])

    def test_paged_export_reports_missing_converter_without_html_fallback(self):
        raw = (Path(__file__).resolve().parents[1] / 'examples/ai-analysis-test.docx').read_bytes()
        body = {'filename': 'example.docx', 'file': base64.b64encode(raw).decode()}
        with patch('document_preview.converter_path', return_value=None), patch('document_preview.readable_preview') as fallback:
            with self.assertRaisesRegex(ValueError, 'LABWISE_SOFFICE'):
                preview(body, require_paged=True)
            fallback.assert_not_called()

    def test_paged_export_distinguishes_conversion_failures(self):
        raw = (Path(__file__).resolve().parents[1] / 'examples/ai-analysis-test.docx').read_bytes()
        body = {'filename': 'example.docx', 'file': base64.b64encode(raw).decode()}
        for failure, message in ((subprocess.TimeoutExpired('soffice', 60), '转换超时'),
                                 (OSError('cannot launch'), '无法启动'),
                                 (None, '未能将此文档转换')):
            with self.subTest(message=message), patch('document_preview.converter_path', return_value='/fake/soffice'), patch('document_preview.subprocess.run', side_effect=failure) as run, patch('document_preview.readable_preview') as fallback:
                run.return_value.returncode = 1
                with self.assertRaisesRegex(ValueError, message):
                    preview(body, require_paged=True)
                fallback.assert_not_called()

    def test_external_image_removed_from_conversion_copy(self):
        data = io.BytesIO()
        with zipfile.ZipFile(data, 'w') as archive:
            archive.writestr('word/document.xml', '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Test content</w:t></w:r></w:p></w:body></w:document>')
            archive.writestr('word/_rels/document.xml.rels', '<Relationships><Relationship TargetMode="External" Type="image" Target="https://example.com/image"/></Relationships>')
        _,files,warnings=prepare_copy(data.getvalue())
        self.assertNotIn(b'TargetMode="External"', files['word/_rels/document.xml.rels'])
        self.assertTrue(warnings)
