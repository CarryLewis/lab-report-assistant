import base64
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pilot_backend as backend
import evaluation_language as language
from ai_fixtures import analysis_output, create_assignment


class EvaluationLanguageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.patches = [patch.object(backend, 'DATA', Path(self.temp.name)),
                        patch.object(backend, 'KEY', ''), patch.object(backend, 'ENV_KEY', '')]
        for item in self.patches:
            item.start()
        backend.init()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def call(self, path, body=None):
        return backend.dispatch('GET' if body is None else 'POST', '/api/pilot/'+path, body or {}, None)

    def test_independent_save_persists_without_key_and_preserves_other_settings(self):
        self.assertEqual(self.call('bootstrap')['settings']['evaluation_language'], 'zh-CN')
        with backend.db() as c:
            # Simulate a pre-feature database with connection and preference state.
            old = {'model':'deepseek-flash', 'preferences':{'name':'Teacher'},
                   'connection_test':{'state':'passed'}}
            c.execute('UPDATE settings SET payload=? WHERE id=1', (json.dumps(old),))
        self.assertEqual(self.call('bootstrap')['settings']['evaluation_language'], 'zh-CN')
        for code in language.LANGUAGES:
            self.assertEqual(self.call('evaluation-language', {'evaluation_language':code}),
                             {'evaluation_language':code})
            backend.init()
            settings = self.call('bootstrap')['settings']
            self.assertEqual(settings['evaluation_language'], code)
            self.assertFalse(settings['has_key'])
            with backend.db() as c:
                saved = json.loads(c.execute('SELECT payload FROM settings WHERE id=1').fetchone()[0])
            self.assertEqual({k:v for k,v in saved.items() if k!='evaluation_language'}, old)
        self.call('settings', {'model':'deepseek-v4-pro'})
        self.assertEqual(self.call('bootstrap')['settings']['evaluation_language'], code)
        for bad in (None, '', 'auto', 'en; ignore rules', [], 123):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.call('evaluation-language', {'evaluation_language':bad})
        self.assertEqual(self.call('bootstrap')['settings']['evaluation_language'], code)

    def test_requests_use_selected_language_for_text_scores_and_word_objects(self):
        aid = create_assignment()
        report = self.call('reports', {'assignment_id':aid, 'sample':True})
        original = json.dumps(report, ensure_ascii=False)
        for mode in ('code', 'ai', 'word'):
            for code in ('en', 'zh-TW', 'ja'):
                with self.subTest(mode=mode, language=code):
                    r = json.loads(original)
                    r['assignment']['rubric']['processing_mode'] = 'code' if mode=='code' else 'ai'
                    result = analysis_output()
                    if mode=='word':
                        r['word_source']={'version':'word-native-v1','objects':[{'id':'img1'}]}
                        result['visual_checks']=[{'object_id':'img1','status':'unclear','summary':'Unreadable chart.'}]
                    response = io.BytesIO(json.dumps({'choices':[{'finish_reason':'stop',
                        'message':{'content':json.dumps(result)}}]}).encode())
                    word_inputs = ({'objects':[{'id':'img1'}], 'tables':[]}, [],
                                   {'objects':[{'id':'img1','status':'image_sent'}], 'warnings':[]})
                    with patch.object(backend, 'KEY', 'test'), patch.object(backend, 'urlopen', return_value=response) as request, \
                            patch('word_source.inputs', return_value=word_inputs):
                        output = backend.analyze(r, 'deepseek', {'model':'deepseek-flash','evaluation_language':code}, None)
                    prompt = json.loads(request.call_args.args[0].data)['messages'][0]['content']
                    self.assertIn(language.prompt_rule(code), prompt)
                    for conflict in ('Chinese overview', 'Chinese explanation', 'Use Chinese', "submitted text's primary language"):
                        self.assertNotIn(conflict, prompt)
                    self.assertEqual(output['evaluation_language'], code)
                    self.assertEqual(output['findings'][0]['quote'], result['findings'][0]['quote'])
                    self.assertEqual(output['findings'][0]['paragraph_ids'], ['p2'])
                    self.assertEqual('score_suggestions' in output, mode!='code')
                    if mode=='word':
                        self.assertIsNone(output['suggested_total'])
                        self.assertIn(language.review_notice(code,'unreadable_visuals'),
                                      output['score_suggestions'][0]['uncertainty'])
        self.assertEqual(json.dumps(report, ensure_ascii=False), original)

    def test_visual_review_uses_same_contract(self):
        import visual_review
        from test_visual_review import png, output
        region = visual_review.prepare({'page':1, 'bbox':[0,0,1,1],
                                        'image':base64.b64encode(png()).decode()})
        response = io.BytesIO(json.dumps({'choices':[{'finish_reason':'stop',
                            'message':{'content':json.dumps(output())}}]}).encode())
        with patch.object(visual_review, 'urlopen', return_value=response) as request:
            result = visual_review.analyze(region, {}, 'test', 'deepseek-flash', None, 'en')
        prompt = json.loads(request.call_args.args[0].data)['messages'][0]['content']
        self.assertIn(language.prompt_rule('en'), prompt)
        self.assertNotIn('Chinese', prompt)
        self.assertEqual(result['evaluation_language'], 'en')
        claim_check = next(c for c in result['checks'] if c['category']=='claim_consistency')
        self.assertEqual(claim_check['explanation'], language.review_notice('en','missing_claim'))


if __name__ == '__main__':
    unittest.main()
