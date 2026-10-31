import base64
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
import zipfile

import pilot_backend as backend
from rubric_import import parse_source
import writing_profiles


class WritingProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.data = patch.object(backend, 'DATA', Path(self.temp.name))
        self.key = patch.object(backend, 'KEY', '')
        self.data.start(); self.key.start(); backend.init()

    def tearDown(self):
        self.key.stop(); self.data.stop(); self.temp.cleanup()

    def call(self, path, body=None):
        return backend.dispatch('GET' if body is None else 'POST', '/api/pilot/' + path, body or {}, None)

    def create(self, profile):
        source = '\n\n'.join(f"{c['name']}（{c['maximum_points']}分）\n{c['descriptor']}" for c in profile['criteria'])
        return self.call('assignments', {'title': profile['name'] + '测试', 'assignment_type': profile['name'],
                         'instructions': profile['instructions'], 'source_text': source})['id']

    def import_text(self, aid, fixture):
        document = ET.Element('w:document', {'xmlns:w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'})
        body = ET.SubElement(document, 'w:body')
        for paragraph in fixture['paragraphs']:
            p = ET.SubElement(body, 'w:p')
            if paragraph['heading']:
                prop = ET.SubElement(p, 'w:pPr'); ET.SubElement(prop, 'w:pStyle', {'w:val':'Heading1'})
            ET.SubElement(ET.SubElement(p, 'w:r'), 'w:t').text = paragraph['text']
        buff = io.BytesIO()
        with zipfile.ZipFile(buff, 'w') as archive:
            archive.writestr('word/document.xml', ET.tostring(document))
        return self.call('reports', {'assignment_id':aid, 'filename':fixture['id']+'.docx',
                         'file':base64.b64encode(buff.getvalue()).decode()})

    def test_each_genre_import_and_ai_request_use_own_snapshot_and_wording(self):
        profiles = self.call('writing-profiles')['profiles']
        fixtures = {x['profile_id']:x for x in map(json.loads, (writing_profiles.ROOT/'corpus/texts.seed.jsonl').read_text().splitlines())}
        self.assertEqual(len(profiles), 8)
        self.assertEqual(len({p['id'] for p in profiles}), 8)
        all_examples = set()
        for profile in profiles:
            with self.subTest(profile=profile['id']):
                aid = self.create(profile)
                report = self.import_text(aid, fixtures[profile['id']])
                saved = report['assignment']['writing_profile']
                self.assertEqual(saved['id'], profile['id'])
                self.assertEqual(sum(c['maximum_points'] for c in profile['criteria']), 100)
                quote = report['paragraphs'][1]['text']
                output = {'summary':'测试概览', 'outline':[], 'claims':[], 'visual_checks':[], 'findings':[
                    {'title':'候选反馈', 'criterion_id':'criterion_1', 'kind':'strength',
                     'paragraph_ids':[report['paragraphs'][1]['id']], 'quote':quote,
                     'rationale':'待教师核对', 'feedback':'依据原文的候选反馈'}]}
                output['score_suggestions']=[{'criterion_id':c['id'],'base_score':None,'score':None,'rationale':'尚需核对',
                                             'evidence':[],'uncertainty':'测试材料不足','adjustments':[]} for c in report['assignment']['rubric']['criteria']]
                response = io.BytesIO(json.dumps({'choices':[{'finish_reason':'stop','message':{'content':json.dumps(output)}}]}).encode())
                with patch.object(backend,'KEY','test-key'), patch.object(backend,'urlopen',return_value=response) as request:
                    result = backend.analyze(report,'deepseek',{'model':'deepseek-flash'},None)
                payload = json.loads(request.call_args.args[0].data)
                self.assertNotIn('Analyze this English lab report',payload['messages'][0]['content'])
                context = json.loads(payload['messages'][1]['content'][0]['text'])
                self.assertEqual(context['writing_context']['profile_id'],profile['id'])
                self.assertNotIn('writing_profile',context['assignment'])
                self.assertEqual(result['writing_profile_id'],profile['id'])
                for example in context['writing_context']['wording_reference_only']:
                    self.assertEqual(example['scope'],profile['id'])
                    self.assertEqual(example['status'],'draft')
                    self.assertTrue(example['requires_current_text_evidence'])
                    self.assertNotIn(example['id'],all_examples)
                    all_examples.add(example['id'])
        self.assertEqual(len(all_examples),80)

    def test_revising_assignment_preserves_old_genre_and_custom_rubric_scale(self):
        proposal = writing_profiles.for_type('研究计划')
        aid = self.create(proposal)
        fixture = json.loads((writing_profiles.ROOT/'corpus/texts.seed.jsonl').read_text().splitlines()[3])
        report = self.import_text(aid, fixture)
        self.call('assignments/'+aid, {'revision':1,'title':'Changed genre','assignment_type':'课程论文',
                  'instructions':'Custom essay','source_text':'原创论证（12分）\n回应问题\n语言（8分）\n表达清楚'})
        old = self.call('reports/'+report['id'])
        self.assertEqual(old['assignment']['writing_profile']['id'],'research_proposal')
        updated = next(a for a in self.call('bootstrap')['assignments'] if a['id']==aid)
        self.assertEqual(updated['writing_profile']['id'],'academic_essay')
        self.assertEqual(sum(c['maximum_points'] for c in updated['rubric']['criteria']),20)
        self.assertEqual(writing_profiles.review_context(updated)['wording_reference_only'],[])

    def test_legacy_labels_and_custom_types_have_safe_fallbacks(self):
        self.assertEqual(writing_profiles.for_type('课程论文')['id'],'academic_essay')
        self.assertEqual(writing_profiles.for_type('自定义短评')['id'],'general_writing')
        assignment={'rubric':{'criteria':[{'name':'Custom'}]}}
        self.assertEqual(writing_profiles.review_context(assignment)['profile_id'],'lab_report')
        assignment['assignment_type']='自定义短评'
        self.assertEqual(writing_profiles.review_context(assignment)['profile_id'],'general_writing')
        # Editing a returned profile cannot mutate another request's template.
        profile=writing_profiles.for_type('反思写作');profile['cautions'].clear()
        self.assertTrue(writing_profiles.for_type('反思写作')['cautions'])


if __name__ == '__main__':
    unittest.main()
