"""Network retry and concurrent import must never replace teacher work."""
import base64
import io
import json
import threading
import unittest
from unittest.mock import patch

import pilot_backend as p
import test_user_workflow
from ai_fixtures import create_assignment


class ImportRecoveryTests(unittest.TestCase):
    setUp = test_user_workflow.UserWorkflowTests.setUp
    tearDown = test_user_workflow.UserWorkflowTests.tearDown
    call = test_user_workflow.UserWorkflowTests.call

    def first(self):
        report = test_user_workflow.UserWorkflowTests.report(self)
        self.raw = (p.DATA / 'sources' / (report['id'] + '.bin')).read_bytes()
        return report

    def upload(self, filename='fictional.docx', token=None, assignment_id=None, raw=None):
        body = {'assignment_id': assignment_id or self.assignment_id, 'filename': filename,
                'file': base64.b64encode(self.raw if raw is None else raw).decode()}
        if token:
            body['import_token'] = token
        return self.call('reports', body)

    def test_retry_keeps_confirmed_scores_notes_and_history(self):
        report = self.first()
        report = self.call('reports/' + report['id'] + '/confirm', {
            'revision': report['revision'], 'notes': 'private note', 'feedback': 'teacher feedback',
            'scores': {'methods': 25, 'results': 24, 'discussion': 35}})
        revisions = self.call('reports/' + report['id'] + '/revisions')
        retried = self.upload()
        self.assertTrue(retried['import_reused'])
        for key in ('id', 'confirmed', 'confirmed_at', 'scores', 'notes', 'feedback', 'revision'):
            self.assertEqual(retried[key], report[key])
        self.assertEqual(revisions, self.call('reports/' + report['id'] + '/revisions'))
        self.assertEqual(len(self.call('bootstrap')['reports']), 1)

    def test_same_bytes_in_distinct_files_assignments_or_rubric_versions_stay_separate(self):
        report = self.first()
        other_file = self.upload(filename='another-student.docx')
        other_assignment = self.upload(assignment_id=create_assignment())
        self.call('assignments/' + self.assignment_id, {
            'revision': report['assignment']['revision'], 'title': 'Updated requirements',
            'instructions': 'New rubric snapshot', 'rubric': report['assignment']['rubric']})
        updated = self.upload()
        self.assertEqual(len({report['id'], other_file['id'], other_assignment['id'], updated['id']}), 4)
        self.assertNotEqual(report['assignment']['revision'], updated['assignment']['revision'])

    def test_retry_token_is_bound_even_when_original_file_already_existed(self):
        report = self.first()
        token = 'a' * 32
        first = self.upload(token=token)
        self.assertEqual(first['id'], report['id'])
        self.assertEqual(self.upload(token=token)['id'], report['id'])
        with self.assertRaisesRegex(ValueError, '另一份内容'):
            self.upload(token=token, filename='different.docx')

    def test_concurrent_uploads_create_one_report_and_one_analysis_job(self):
        self.first()
        results, errors = [], []
        def upload(token):
            try:
                results.append(self.upload(filename='concurrent.docx', token=token))
            except Exception as error:
                errors.append(error)
        threads = [threading.Thread(target=upload, args=(letter * 32,)) for letter in ('b', 'c')]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(5)
            self.assertFalse(thread.is_alive())
        self.assertFalse(errors)
        self.assertEqual(len({result['id'] for result in results}), 1)
        self.assertEqual(sum(bool(result.get('import_reused')) for result in results), 1)
        with p.db() as connection:
            self.assertEqual(connection.execute('SELECT count(*) FROM reports').fetchone()[0], 2)
            self.assertEqual(connection.execute('SELECT count(*) FROM analysis_jobs').fetchone()[0], 2)

    def test_archived_file_can_be_imported_as_a_new_report(self):
        report = self.first()
        self.call('reports/' + report['id'] + '/archive', {'revision': report['revision']})
        restored = self.upload()
        self.assertNotEqual(report['id'], restored['id'])
        self.assertTrue(self.call('reports/' + report['id'])['archived'])

    def test_word_request_uses_the_model_selected_in_settings(self):
        report = self.first()
        content = {'summary':'Fictional overview','outline':[],'claims':[],'findings':[],'visual_checks':[]}
        content['score_suggestions']=[{'criterion_id':c['id'],'base_score':None,'score':None,'rationale':'Not assessed',
                                      'evidence':[],'uncertainty':'Insufficient fixture','adjustments':[]} for c in report['assignment']['rubric']['criteria']]
        response = io.BytesIO(json.dumps({'choices':[{'finish_reason':'stop','message':{'content':json.dumps(content)}}]}).encode())
        with patch.object(p,'KEY','fictional-key'), patch.object(p,'urlopen',return_value=response) as request:
            result = p.analyze(report,'deepseek',{'model':'deepseek-v4-pro'},None)
        self.assertEqual(json.loads(request.call_args.args[0].data)['model'], 'deepseek-v4-pro')
        self.assertEqual(result['model'], 'deepseek-v4-pro')


if __name__ == '__main__':
    unittest.main()
