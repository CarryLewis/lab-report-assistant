import base64
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
import pilot_backend as p


class PilotWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.patch = patch.object(p, 'DATA', Path(self.temp.name))
        self.patch.start()
        p.init()

    def tearDown(self):
        self.patch.stop()
        self.temp.cleanup()

    def call(self, path, body=None):
        return p.dispatch('GET' if body is None else 'POST', '/api/pilot/'+path, body or {}, None)

    def sample(self):
        return self.call('reports', {'assignment_id':'sample-assignment','sample':True})

    def test_complete_workflow_and_rollback(self):
        r = self.sample()
        path = 'reports/'+r['id']
        with self.assertRaises(ValueError):
            self.call(path+'/export')
        r = self.call(path+'/analyze', {'mode':'example','revision':r['revision']})
        self.assertEqual(len(r['analysis']['findings']),2)
        scores = {c['id']: c['maximum_points']*.8 for c in r['assignment']['rubric']['criteria']}
        body = {'revision':r['revision'],'scores':scores,'reviews':{'1':'accepted','2':'edited'},'notes':'PRIVATE NOTE','feedback':'Instructor final feedback <unsafe>','suggestion_edits':{'2':'Edited feedback'}}
        saved = self.call(path+'/confirm',body)
        exported = self.call(path+'/export')
        self.assertNotIn('PRIVATE NOTE', exported['content'])
        self.assertIn('Instructor final feedback', exported['content'])
        structured = self.call(path+'/export-json')['content']
        self.assertEqual(structured['schema_version'], 'labwise-feedback-package.v1')
        self.assertFalse(structured['integration']['turnitin_sync'])
        self.assertEqual(len(structured['score']['criteria']), 3)
        self.assertEqual({item['teacher_decision'] for item in structured['evidence']}, {'accepted', 'edited'})
        self.assertNotIn('notes', structured)
        printable = self.call(path+'/export-html')['content']
        self.assertIn('Instructor-confirmed feedback', printable)
        self.assertIn('&lt;unsafe&gt;', printable)
        self.assertNotIn('PRIVATE NOTE', printable)
        word = base64.b64decode(self.call(path+'/export-docx')['content'])
        with zipfile.ZipFile(io.BytesIO(word)) as archive:
            document = archive.read('word/document.xml').decode()
        self.assertIn('Instructor final feedback', document)
        self.assertNotIn('PRIVATE NOTE', document)
        turnitin = self.call(path+'/export-turnitin')['content']
        self.assertIn('TURNITIN MANUAL-ENTRY SUMMARY', turnitin)
        self.assertNotIn('PRIVATE NOTE', turnitin)
        self.assertEqual(self.call(path)['suggestion_edits']['2'],'Edited feedback')
        with self.assertRaises(ValueError):
            self.call(path+'/save',body)  # stale revision
        versions = self.call(path+'/revisions')['revisions']
        restored = self.call(path+'/restore',{'revision':saved['revision'],'version_id':versions[0]['id']})
        self.assertFalse(restored['confirmed'])
        self.assertGreater(restored['revision'],saved['revision'])
        with self.assertRaises(ValueError):
            self.call(path+'/export')

    def test_unreviewed_and_out_of_range_scores_rejected(self):
        r=self.sample();path='reports/'+r['id']
        with self.assertRaises(ValueError):
            self.call(path+'/confirm',{'revision':r['revision'],'feedback':'Feedback'})
        with self.assertRaises(ValueError):
            self.call(path+'/save',{'revision':r['revision'],'scores':{'methods':999}})
        with self.assertRaises(ValueError):
            self.call(path+'/save',{'revision':r['revision'],'scores':{'methods':float('nan')}})

    def test_docx_and_structural_mode(self):
        out=io.BytesIO()
        with zipfile.ZipFile(out,'w') as z:
            z.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Results</w:t></w:r></w:p><w:p><w:r><w:t>Actual report text</w:t></w:r></w:p></w:body></w:document>')
        r=self.call('reports',{'assignment_id':'sample-assignment','filename':'real.docx','file':base64.b64encode(out.getvalue()).decode()})
        self.assertEqual(r['paragraphs'][1]['text'],'Actual report text')
        r=self.call('reports/'+r['id']+'/analyze',{'revision':r['revision'],'mode':'example'})
        self.assertEqual(r['analysis']['mode'],'structure')
        self.assertEqual(r['analysis']['findings'],[])
        with self.assertRaises(ValueError):
            p.paragraphs_docx(b'not a zip')

    def test_rubric_validation_and_snapshot(self):
        with self.assertRaises(ValueError):
            p.rubric_check({'name':'Bad','criteria':[{'id':'a','name':'A','weight':10},{'id':'a','name':'B','weight':20}]})
        r=self.sample()
        a=self.call('assignments',{'title':'New assignment','rubric':{'name':'Other','criteria':[{'id':'a','name':'A','weight':20}]}})
        self.assertNotEqual(a['id'],r['assignment']['id'])
        self.assertEqual(len(self.call('reports/'+r['id'])['assignment']['rubric']['criteria']),3)

    def test_model_evidence_validation(self):
        r=self.sample()
        output={'summary':'A summary','outline':[],'claims':[],'findings':[{'title':'Test','paragraph_ids':['p2'],'kind':'issue','criterion_id':'methods','quote':'fabricated quote','rationale':'Reason','feedback':'Feedback'}]}
        with self.assertRaises(ValueError):
            p.validate_analysis(output,r)
        output['findings'][0]['quote']='Each measurement was performed once'
        result=p.validate_analysis(output,r)
        self.assertEqual(result['findings'][0]['review'],'pending')
        output['findings'][0]['criterion_id']='nonexistent'
        with self.assertRaises(ValueError):
            p.validate_analysis(output,r)


if __name__=='__main__':
    unittest.main()
