import base64
import io
import unittest
import zipfile
from unittest.mock import patch
from document_preview import preview, prepare_copy


class DocumentPreviewTests(unittest.TestCase):
    def test_rejects_wrong_type_and_invalid_file(self):
        for body in ({'filename': 'x.pdf'}, {'filename': 'x.docx', 'file': '!'},
                     {'filename': 'x.docx', 'file': base64.b64encode(b'not zip').decode()}):
            with self.assertRaises(ValueError):
                preview(body)

    def test_missing_converter_has_explicit_compatibility_preview(self):
        data = io.BytesIO()
        with zipfile.ZipFile(data, 'w') as archive:
            archive.writestr('word/document.xml', '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Test content</w:t></w:r></w:p></w:body></w:document>')
        with patch('document_preview.shutil.which', return_value=None):
            result=preview({'filename': 'x.docx', 'file': base64.b64encode(data.getvalue()).decode()})
        self.assertEqual(result['preview_mode'],'readable')
        self.assertIn('Test content',result['html'])
        self.assertTrue(result['warnings'])

    def test_external_image_removed_from_conversion_copy(self):
        data = io.BytesIO()
        with zipfile.ZipFile(data, 'w') as archive:
            archive.writestr('word/document.xml', '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Test content</w:t></w:r></w:p></w:body></w:document>')
            archive.writestr('word/_rels/document.xml.rels', '<Relationships><Relationship TargetMode="External" Type="image" Target="https://example.com/image"/></Relationships>')
        _,files,warnings=prepare_copy(data.getvalue())
        self.assertNotIn(b'TargetMode="External"', files['word/_rels/document.xml.rels'])
        self.assertTrue(warnings)
