import io
import json
import unittest
from unittest.mock import patch

import pilot_backend as backend


class ReviewGuidanceTests(unittest.TestCase):
    def test_only_matching_assignment_receives_internal_guidance(self):
        names = (
            'Introduction', 'Methods', 'Results', 'Discussion',
            'Citations and References, and Formatting',
            'Structure & Organisation and Academic Writing Style',
        )
        weights = (20, 10, 20, 20, 10, 20)
        for rubric_identity, actual_weights, enabled in (
            ('Introduction to Scientific Method (ItSM1) Lab Report - Point Scale', weights, True),
            ('Generic Lab Report', weights, False),
            ('BS1084 Lab Report', (15, 15, 20, 20, 10, 20), False),
        ):
            with self.subTest(rubric_identity=rubric_identity, actual_weights=actual_weights):
                assignment = {
                    'title': 'Lab report',
                    'rubric': {
                        'name': 'Teacher rubric',
                        'original_source_text': rubric_identity,
                        'criteria': [
                            {'id': f'c{i}', 'name': name, 'maximum_points': weight}
                            for i, (name, weight) in enumerate(zip(names, actual_weights))
                        ],
                    },
                }
                report = {
                    'assignment': assignment,
                    'paragraphs': [{'id': 'p1', 'text': 'BS1084: fictional report.'}],
                }
                message = {'summary': 'Review', 'outline': [], 'claims': [], 'findings': []}
                response = {'choices': [
                    {'finish_reason': 'stop', 'message': {'content': json.dumps(message)}},
                ]}
                with (
                    patch.object(backend, 'KEY', 'test-key'),
                    patch.object(backend, 'urlopen', return_value=io.BytesIO(json.dumps(response).encode())) as request,
                ):
                    analysis = backend.analyze(report, 'deepseek', {'model': 'deepseek-flash'}, None)
                system, user = json.loads(request.call_args.args[0].data)['messages']
                self.assertEqual('Do not universally require a control t-test' in system['content'], enabled)
                self.assertEqual('bs1084-itsm1-v1' in analysis['prompt_version'], enabled)
                self.assertEqual(json.loads(user['content'])['assignment'], assignment)
                self.assertNotIn('37 条', system['content'] + user['content'])
