import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
import test_pilot
from ai_fixtures import analysis_output
import pilot_backend as p


class AIAnalysisTests(unittest.TestCase):
    setUp = test_pilot.PilotWorkflowTests.setUp
    tearDown = test_pilot.PilotWorkflowTests.tearDown
    call = test_pilot.PilotWorkflowTests.call
    sample = test_pilot.PilotWorkflowTests.sample
    def response(self, output=None, finish='stop'):
        return io.BytesIO(json.dumps({'choices':[{'finish_reason':finish,'message':{'content':json.dumps(output if output is not None else analysis_output())}}]}).encode())

    def test_real_request_contract_and_preserved_teacher_work(self):
        report=self.sample()
        path='reports/'+report['id']
        note={'id':'a1','page':1,'quote':'Each measurement was performed once','note':'Teacher comment'}
        report=self.call(path+'/save',{'revision':report['revision'],'teacher_summary':'My assessment','feedback':'My feedback','scores':{'methods':20},'annotations':[note]})
        with patch.object(p,'KEY','test-key'),patch.object(p,'urlopen',return_value=self.response()) as request:
            result=self.call(path+'/analyze',{'mode':'deepseek','revision':report['revision']})
        payload=json.loads(request.call_args.args[0].data)
        self.assertEqual(payload['response_format'],{'type':'json_object'})
        self.assertEqual(payload['thinking'],{'type':'disabled'})
        self.assertEqual(result['status'],'ready')
        self.assertEqual(len(result['analysis']['findings']),2)
        self.assertEqual(result['teacher_summary'],'My assessment')
        self.assertEqual(result['feedback'],'My feedback')
        self.assertEqual(result['scores'],{'methods':20})
        self.assertEqual(result['annotations'],[note])
        self.assertEqual(self.call(path)['analysis'],result['analysis'])

    def test_failure_is_saved_and_retry_can_succeed(self):
        report=self.sample();path='reports/'+report['id']
        with patch.object(p,'KEY','test-key'),patch.object(p,'urlopen',side_effect=URLError('offline')):
            failed=self.call(path+'/analyze',{'mode':'deepseek','revision':report['revision']})
        self.assertEqual(failed['status'],'failed');self.assertIn('网络',failed['error'])
        with patch.object(p,'KEY','test-key'),patch.object(p,'urlopen',return_value=self.response()):
            result=self.call(path+'/analyze',{'mode':'deepseek','revision':failed['revision']})
        self.assertEqual(result['status'],'ready');self.assertIsNone(result['error'])

    def test_invalid_evidence_truncated_response_and_missing_key(self):
        report=self.sample();config={'model':'deepseek-flash'}
        invalid=analysis_output();invalid['findings'][0]['quote']='Fabricated evidence'
        for response in [self.response(invalid),self.response(finish='length'),io.BytesIO(b'not json')]:
            with patch.object(p,'KEY','test-key'),patch.object(p,'urlopen',return_value=response),self.assertRaises(ValueError):
                p.analyze(report,'deepseek',config,None)
        with patch.object(p,'KEY',''),self.assertRaisesRegex(ValueError,'密钥'):
            p.analyze(report,'deepseek',config,None)
        with patch.object(p,'KEY','test-key'),patch.object(p,'urlopen',side_effect=HTTPError('https://api.deepseek.com',401,'Unauthorized',{},None)),self.assertRaisesRegex(ValueError,'401'):
            p.analyze(report,'deepseek',config,None)
