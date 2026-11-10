import io
import json
import unittest
from unittest.mock import patch
from urllib.error import URLError

import pilot_backend as backend
import word_review


def response(content):
    return io.BytesIO(json.dumps({'choices': [
        {'finish_reason': 'stop', 'message': {'content': json.dumps(content)}},
    ]}).encode())


def finding(title, **anchor):
    return {'title': title, 'criterion_id': 'results', 'kind': 'issue',
            'feedback': 'Check the reported result.', 'rationale': 'Source evidence.', **anchor}


def checked(object_id):
    return {'object_id': object_id, 'status': 'checked', 'summary': 'Read chart.'}


class WordReviewTests(unittest.TestCase):
    def setUp(self):
        self.objects = [{'id': 'v1', 'paragraph_id': 'p2'}, {'id': 'v2', 'paragraph_id': 'p5'}]
        self.coverage = {'state': 'complete', 'warnings': [], 'objects': [
            {**obj, 'status': 'image_sent', 'image_block_index': 2*i+1} for i, obj in enumerate(self.objects)
        ]}
        self.images = [
            block for obj in self.objects for block in (
                {'type': 'text', 'text': obj['id']},
                {'type': 'image_url', 'image_url': {'url': f'fixture:{obj["id"]}'}},
            )
        ]
        self.report = {
            'assignment': {'title': 'Fictional report', 'rubric': {'criteria': [{'id': 'results', 'name': 'Results'}]}},
            'paragraphs': [
                {'id': f'p{i}', 'text': f'Paragraph {i}', 'object_only': i in (2, 5)}
                for i in range(1, 9)
            ],
            'word_source': {'version': 'word-native-v1', 'objects': self.objects},
        }
        self.initial = {'summary': 'Review', 'outline': [], 'claims': [],
                        'visual_checks': [checked('v1')],
                        'findings': [
                            finding('Valid text', paragraph_ids=['p1'], quote='Paragraph 1'),
                            finding('Valid chart', object_id='v1'),
                            finding('Unlocated chart', paragraph_ids=['p5'], quote='pixel label'),
                            finding('Invented object', object_id='v99'),
                        ]}

    def run_review(self, retry):
        inputs = ({'objects': self.objects, 'tables': []}, self.images, self.coverage)
        with (patch('word_source.inputs', return_value=inputs),
              patch.object(backend, 'KEY', 'test-key'),
              patch.object(backend, 'urlopen', side_effect=[response(self.initial), retry]) as upstream):
            output = backend.analyze(self.report, 'deepseek', {'model': 'deepseek-flash'}, None)
        return output, upstream

    def test_preserves_valid_comments_and_repairs_only_the_missing_object(self):
        repair = {'visual_checks': [checked('v2'), checked('v1')],
                  'findings': [finding('Repair', object_id='v2', quote=''), finding('Out of scope', object_id='v1')]}
        out, upstream = self.run_review(response(repair))
        self.assertEqual([(f['title'], f['paragraph_ids']) for f in out['findings']],
                         [('Valid text', ['p1']), ('Valid chart', ['p2']), ('Repair', ['p5'])])
        self.assertEqual([c['status'] for c in out['visual_checks']], ['checked', 'checked'])
        payload = json.loads(upstream.call_args.args[0].data)
        blocks = payload['messages'][1]['content']
        context = json.loads(blocks[0]['text'])
        self.assertEqual([o['id'] for o in context['word_objects']], ['v2'])
        self.assertEqual([p['id'] for p in context['paragraphs']], ['p3', 'p4', 'p5', 'p6', 'p7'])
        self.assertEqual(blocks[2]['image_url']['url'], 'fixture:v2')
        self.assertEqual(upstream.call_count, 2)

    def test_failed_retry_keeps_unrelated_findings_and_marks_partial_coverage(self):
        out, upstream = self.run_review(URLError('offline'))
        self.assertEqual([f['title'] for f in out['findings']], ['Valid text', 'Valid chart'])
        self.assertEqual(out['coverage']['state'], 'partial')
        self.assertEqual([c['status'] for c in out['visual_checks']], ['checked', 'unclear'])
        self.assertEqual(upstream.call_count, 2)

    def test_structured_checks_distinguish_rounding_and_actual_discrepancies(self):
        tables = [
            {'id': 't1', 'rows': [['Zone diameter (mm)'], ['', 'Group A', 'Group B'],
                                  ['Plate 1', '13.5', '14'], ['Plate 2', '14', '15'], ['Plate 3', '14', '16'],
                                  ['Average', '13.8', '15']]},
            {'id': 't2', 'rows': [['Zone diameter (mm)'], ['', 'Group A', 'Group B'],
                                  ['Mean', '13.83', '15'], ['Observations', '2', '3']]},
            {'id': 't3', 'rows': [['Other measure'], ['', 'Group A', 'Group B'], ['Observations', '1', '2']]},
        ]
        charts = [{'id': 'v1', 'chart_title': 'Average zone diameter (mm)',
                   'chart_series': [{'categories': ['Group A', 'Group B'], 'values': ['13.83', '14']}]},
                  {'id': 'v2', 'chart_title': 'Average other measure',
                   'chart_series': [{'categories': ['Group A'], 'values': ['1']}]}]
        issues = word_review.data_checks(tables, charts)
        self.assertEqual([(x['reported_source_id'], x['quantity'], x['calculated'], x['reported']) for x in issues],
                         [('t2', 'n', '3', '2'), ('v1', 'mean', '15', '14')])
