import base64
import io
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
import pilot_backend as p
from rubric_import import parse_source,extract

SOURCE='实验方法（30分）\n描述方法、对照与重复次数。\n结果与讨论（70分）\n解释证据与局限。'


class RubricImportTests(unittest.TestCase):
    def test_chinese_and_english_explicit_scores(self):
        r=parse_source(SOURCE)
        self.assertTrue(r['ready'])
        self.assertEqual(r['total'],100)
        self.assertIn('重复次数',r['criteria'][0]['descriptor'])
        r=parse_source('Methods: 30 points\nDescribe controls\nResults (70%)')
        self.assertFalse(r['ready'])  # mixed scales must be clarified
        self.assertTrue(parse_source('Methods: 30 points\nResults: 70 points')['ready'])

    def test_missing_and_conflicting_scores_not_invented(self):
        self.assertFalse(parse_source('Clear methods and critical discussion')['ready'])
        self.assertFalse(parse_source(SOURCE+'\n总分：80')['ready'])
        self.assertFalse(parse_source('Methods: 0 points')['ready'])
        self.assertFalse(parse_source('Methods 0–30 points')['ready'])

    def test_docx_import_and_table_cells(self):
        buff=io.BytesIO()
        with zipfile.ZipFile(buff,'w') as z:
            z.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'+''.join('<w:p><w:r><w:t>'+x+'</w:t></w:r></w:p>' for x in ['Methods','30 points','Use controls','Results','70 points','Interpret data'])+'</w:body></w:document>')
        result=extract({'filename':'rubric.docx','file':base64.b64encode(buff.getvalue()).decode()})
        self.assertTrue(result['ready'])
        self.assertEqual(result['criteria'][1]['name'],'Results')
        self.assertIn('Use controls',result['source_text'])

    def test_invalid_file_does_not_parse(self):
        with self.assertRaises(ValueError):
            extract({'filename':'old.doc','file':base64.b64encode(b'abc').decode()})
        with self.assertRaises(ValueError):
            extract({'filename':'x.docx','file':'!invalid!'})

    def test_pdf_uses_existing_text_extractor(self):
        with patch.object(p,'paragraphs_pdf',return_value=[{'id':'p1','text':'Methods: 30 points'},{'id':'p2','text':'Results: 70 points'}]):
            r=extract({'filename':'rubric.pdf','file':base64.b64encode(b'%PDF').decode()})
            self.assertTrue(r['ready'])
            self.assertEqual(r['filename'],'rubric.pdf')


class AssignmentEditingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.data=patch.object(p,'DATA',Path(self.temp.name))
        self.data.start();p.init()

    def tearDown(self):
        self.data.stop();self.temp.cleanup()

    def call(self,path,body=None):
        return p.dispatch('GET' if body is None else 'POST','/api/pilot/'+path,body or {},None)

    def test_update_preserves_report_snapshot_and_saved_library(self):
        created=self.call('assignments',{'title':'实验一','instructions':'Original requirements','source_text':SOURCE})
        report=self.call('reports',{'assignment_id':created['id'],'sample':True})
        a=next(x for x in self.call('bootstrap')['assignments'] if x['id']==created['id'])
        self.call('assignments/'+a['id'],{'revision':a['revision'],'title':'实验一（修订）','instructions':'New requirements','source_text':'方法（20分）\n结果（80分）'})
        updated=next(x for x in self.call('bootstrap')['assignments'] if x['id']==a['id'])
        self.assertEqual(updated['revision'],2)
        self.assertEqual(updated['rubric']['criteria'][0]['maximum_points'],20)
        old=self.call('reports/'+report['id'])
        self.assertEqual(old['assignment']['instructions'],'Original requirements')
        self.assertEqual(old['assignment']['rubric']['criteria'][0]['maximum_points'],30)
        with self.assertRaises(ValueError):
            self.call('assignments/'+a['id'],{'revision':1,'title':'Stale edit','source_text':SOURCE})
        with p.db() as con:
            self.assertEqual(con.execute('SELECT count(*) FROM assignment_versions').fetchone()[0],1)

    def test_unscored_text_cannot_silently_get_default_weights(self):
        with self.assertRaises(ValueError):
            self.call('assignments',{'title':'Bad import','source_text':'Discuss data quality and limitations'})

    def test_existing_database_migrates(self):
        with p.db() as con:
            con.execute('DROP TABLE assignments')
            con.execute('CREATE TABLE assignments (id TEXT PRIMARY KEY,title TEXT,instructions TEXT,rubric TEXT,created TEXT)')
        p.init()
        self.assertEqual(self.call('bootstrap')['assignments'][0]['revision'],1)

if __name__=='__main__':unittest.main()
