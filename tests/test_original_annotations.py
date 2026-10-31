import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import pilot_backend as p


class OriginalAnnotationTests(unittest.TestCase):
    def test_missing_historical_scope_does_not_break_workbench_or_merge_reports(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(p, 'DATA', Path(folder)):
            p.init()
            snapshot = {'rubric': {'criteria': [{'id': 'c1', 'maximum_points': 100}]}}
            with p.db() as con:
                for ident in ('old-a', 'old-b'):
                    p.persist(con, {'id':ident,'revision':1,'filename':ident+'.pdf',
                                    'assignment':snapshot,'paragraphs':[],'status':'parsed','analysis':None})
            rows = p.dispatch('GET', '/api/pilot/bootstrap', {}, None)['reports']
            self.assertEqual(len({row['assignment_id'] for row in rows}), 2)
            opened = p.dispatch('POST', '/api/pilot/reports/old-a/start-review', {}, None)
            self.assertEqual(opened['assignment']['title'], '历史作业')
            self.assertEqual(opened['assignment']['rubric'], snapshot['rubric'])
            saved = p.dispatch('POST', '/api/pilot/reports/old-a/save', {'revision':1,'notes':'Retained note'}, None)
            self.assertEqual(saved['notes'], 'Retained note')
            self.assertEqual(p.dispatch('GET', '/api/pilot/reports/old-a', {}, None)['assignment'], snapshot)

    def test_annotations_reject_invalid_anchor_and_duplicate_ids(self):
        good = {'id': 'a1', 'page': 2, 'quote': 'original evidence', 'note': 'Review this'}
        self.assertEqual(p.validate_annotations([good]), [good])
        for value in ([dict(good, page=True)], [dict(good, page=0)], [dict(good, quote='')], [good, good], {}):
            with self.assertRaises(ValueError):
                p.validate_annotations(value)

    def test_save_and_reopen_retain_original_annotation(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(p, 'DATA', Path(folder)):
            p.init()
            with p.db() as con:
                report = {'id':'report','revision':1,'filename':'original.pdf','assignment':{'rubric':{'criteria':[{'id':'c1','maximum_points':100}]}},'paragraphs':[{'id':'p1','text':'evidence'}],'status':'parsed','analysis':None}
                p.persist(con, report)
            note = {'id':'a1','page':1,'quote':'evidence','note':'Check method'}
            result=p.dispatch('POST','/api/pilot/reports/report/save',{'revision':1,'annotations':[note]},None)
            self.assertEqual(result['annotations'],[note])
            reopened=p.dispatch('GET','/api/pilot/reports/report',{},None)
            self.assertEqual(reopened['annotations'],[note])
