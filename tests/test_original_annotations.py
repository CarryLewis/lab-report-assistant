import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import pilot_backend as p


class OriginalAnnotationTests(unittest.TestCase):
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
