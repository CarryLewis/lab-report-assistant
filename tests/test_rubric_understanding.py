"""Regression coverage for natural rubric input -> saved snapshot -> scored review."""
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

import pilot_backend as backend
import rubric_ai
import rubric_scoring
from ai_fixtures import create_assignment, analysis_output


def understanding(source='方法30分，结果70分', weights=False, total=None):
    return {'input_type':'weights' if weights else 'points', 'summary':'按方法与结果两个维度评分。',
            'declared_total':total, 'questions':[], 'special_rules':[],
            'criteria':[{'id':cid,'name':name,'maximum_points':None if weights else maximum,
                         'weight_percent':maximum if weights else None,'descriptor':'','levels':[],
                         'source_quote':source}
                        for cid,name,maximum in [('methods','方法',30),('results','结果',70)]]}


def response(out, finish='stop'):
    return io.BytesIO(json.dumps({'choices':[{'finish_reason':finish,'message':{'content':json.dumps(out)}}]}).encode())


class RubricTestCase(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.data=patch.object(backend,'DATA',Path(self.temp.name));self.data.start()
        self.key=patch.object(backend,'KEY','');self.key.start()
        backend.init()

    def tearDown(self):
        self.key.stop();self.data.stop();self.temp.cleanup()

    def call(self,path,body=None):
        return backend.dispatch('GET' if body is None else 'POST','/api/pilot/'+path,body or {},None)

    def understand(self,source='方法30分，结果70分',out=None,**context):
        with patch.object(backend,'KEY','fictional-key'),patch.object(backend,'urlopen',return_value=response(out or understanding(source))) as upstream:
            result=self.call('rubric-understand',{'source_text':source,**context})
        self.assertEqual(upstream.call_count,1)
        payload=json.loads(upstream.call_args.args[0].data)
        self.assertEqual(json.loads(payload['messages'][1]['content'])['source_text'],source)
        self.assertEqual(payload['response_format'],{'type':'json_object'})
        return result

    def save(self,parsed,**body):
        return self.call('assignments',{'title':'自然输入作业','assignment_type':'实验报告','source_text':parsed['source_text'],
                                       'rubric_understanding':parsed,**body})['id']


class RubricUnderstandingTests(RubricTestCase):
    def test_natural_sentence_uses_model_and_save_never_regex_parses(self):
        for source in ['方法30分，结果70分','方法三十分，结果七十分','方法：30；结果：70']:
            with self.subTest(source=source):
                parsed=self.understand(source,assignment_type='实验报告')
                with patch('rubric_import.parse_source',side_effect=AssertionError('must not parse prose')):
                    aid=self.save(parsed)
                saved=next(a for a in self.call('bootstrap')['assignments'] if a['id']==aid)
                self.assertEqual(saved['rubric']['source_text'],source)
                self.assertEqual(saved['rubric']['total'],100)
                self.assertEqual(saved['rubric']['model'],'deepseek-flash')
                self.assertEqual(saved['rubric']['criteria'][0]['source_quote'],source)

    def test_percentage_and_twenty_point_scales_preserved(self):
        source='方法占30%，结果占70%'
        percent=rubric_ai.validate(understanding(source,weights=True),source)
        self.assertTrue(percent['ready']);self.assertTrue(percent['percentage'])
        self.assertEqual([c['maximum_points'] for c in percent['criteria']],[30,70])
        source+='，总分20分'
        points=rubric_ai.validate(understanding(source,weights=True,total=20),source)
        self.assertTrue(points['ready']);self.assertFalse(points['percentage'])
        self.assertEqual([c['maximum_points'] for c in points['criteria']],[6,14])
        self.assertEqual(rubric_ai.validate(points,source),points,'revalidation must not convert twice')

    def test_conflicts_and_missing_scores_stay_unresolved(self):
        source='方法30分，结果70分'
        out=understanding(source,total=80)
        parsed=rubric_ai.validate(out,source)
        self.assertFalse(parsed['ready']);self.assertIn('不一致',' '.join(parsed['messages']))
        out=understanding(source,weights=True);out['criteria'][1]['weight_percent']=60
        self.assertFalse(rubric_ai.validate(out,source)['ready'])
        out=understanding(source);out['criteria'][0]['maximum_points']=None
        self.assertIsNone(rubric_ai.validate(out,source)['criteria'][0]['maximum_points'])

    def test_holistic_levels_and_deductions_survive_save_and_snapshot(self):
        source='整体满分20分。优秀16–20分，论证充分。参考文献每缺一条扣2分，最多扣4分。'
        out={'input_type':'holistic','summary':'整体评分，并按规定扣分。','declared_total':20,'questions':[],
             'criteria':[{'id':'overall','name':'整体评价','maximum_points':20,'descriptor':'论证充分',
                          'source_quote':source,'levels':[{'label':'优秀','minimum':16,'maximum':20,
                          'descriptor':'论证充分','source_quote':'优秀16–20分，论证充分'}]}],
             'special_rules':[{'id':'refs','kind':'deduction','description':'参考文献每缺一条扣2分，最多扣4分。',
                               'maximum_adjustment':4,'source_quote':'参考文献每缺一条扣2分，最多扣4分。'}]}
        parsed=self.understand(source,out,assignment_type='实验报告');aid=self.save(parsed)
        report=self.call('reports',{'assignment_id':aid,'sample':True})
        self.assertEqual(report['assignment']['rubric']['special_rules'],parsed['special_rules'])
        self.assertEqual(report['assignment']['rubric']['criteria'][0]['levels'],parsed['criteria'][0]['levels'])
        updated=copy.deepcopy(parsed);updated['criteria'][0]['descriptor']='教师修正后的要求';updated['edited_by_teacher']=True
        self.call('assignments/'+aid,{'title':'修订','assignment_type':'实验报告','revision':1,'source_text':source,'rubric_understanding':updated})
        old=self.call('reports/'+report['id'])
        self.assertEqual(old['assignment']['rubric']['criteria'][0]['descriptor'],'论证充分')
        current=next(a for a in self.call('bootstrap')['assignments'] if a['id']==aid)
        self.assertTrue(current['rubric']['edited_by_teacher']);self.assertEqual(current['revision'],2)

    def test_changed_source_or_assignment_context_rejects_stale_understanding(self):
        parsed=self.understand(assignment_type='实验报告')
        for body in [{'source_text':'方法50分，结果50分'},{'instructions':'新增要求'},{'assignment_type':'研究计划'}]:
            with self.subTest(body=body),self.assertRaisesRegex(ValueError,'变化'):
                self.save(parsed,**body)

    def test_fabricated_source_evidence_is_rejected(self):
        out=understanding();out['criteria'][0]['source_quote']='编造的标准'
        with self.assertRaisesRegex(ValueError,'原文'):
            rubric_ai.validate(out,'方法30分，结果70分')

    def test_incomplete_draft_roundtrip_without_grading_activation(self):
        source='重视论证和证据，但还没确定分值。'
        out=understanding(source);out['input_type']='qualitative'
        for c in out['criteria']:c['maximum_points']=None
        out['questions']=['论证与证据各占多少分？']
        parsed=self.understand(source,out,assignment_type='实验报告')
        self.assertFalse(parsed['ready'])
        self.call('rubric-draft',{'title':'待完善','assignment_type':'实验报告','source_text':source,'rubric_understanding':parsed})
        draft=self.call('rubric-draft')['draft']
        self.assertEqual(draft['source_text'],source)
        self.assertEqual(draft['rubric_understanding']['questions'],out['questions'])
        self.assertEqual(self.call('bootstrap')['assignments'],[])
        with self.assertRaises(ValueError):self.save(parsed)

    def test_service_failures_do_not_fall_back_to_regex(self):
        for fake in [response(understanding(),finish='length'),io.BytesIO(b'not json')]:
            with patch.object(backend,'KEY','fake'),patch.object(backend,'urlopen',return_value=fake),self.assertRaises(ValueError):
                self.call('rubric-understand',{'source_text':'方法（30分）\n结果（70分）'})
        with patch.object(backend,'urlopen') as upstream,self.assertRaisesRegex(ValueError,'草稿'):
            self.call('rubric-understand',{'source_text':'方法30分，结果70分'})
        upstream.assert_not_called()
        with patch.object(backend,'KEY','fake'),patch.object(backend,'urlopen',side_effect=URLError('offline')),self.assertRaisesRegex(ValueError,'超时'):
            self.call('rubric-understand',{'source_text':'方法30分，结果70分'})


class RubricScoreTests(RubricTestCase):
    def report(self):
        source='方法30分，结果30分，讨论40分'
        out=understanding(source);out['criteria'][1]['maximum_points']=30
        out['criteria'].append({'id':'discussion','name':'讨论','maximum_points':40,'descriptor':'','source_quote':source,'levels':[]})
        parsed=self.understand(source,out,assignment_type='实验报告')
        aid=self.save(parsed)
        return self.call('reports',{'assignment_id':aid,'sample':True})

    def test_scores_require_complete_coverage_valid_evidence_and_valid_range(self):
        report=self.report();original=analysis_output()['score_suggestions']
        invalid=[]
        invalid.append(original[:-1])
        duplicate=copy.deepcopy(original);duplicate[1]=duplicate[0];invalid.append(duplicate)
        for field,value in [('criterion_id','invented'),('score',31),('score',True),('base_score',-1),('evidence',[]),('rationale','')]:
            items=copy.deepcopy(original);items[0][field]=value;invalid.append(items)
        items=copy.deepcopy(original);items[0]['evidence'][0]['quote']='fabricated';invalid.append(items)
        items=copy.deepcopy(original);items[0]['base_score']=20;invalid.append(items)
        for items in invalid:
            with self.subTest(items=items),self.assertRaises(ValueError):rubric_scoring.validate(items,report)
        result=rubric_scoring.validate(original,report)
        self.assertEqual(result['suggested_total'],70)

    def test_unknown_is_not_zero_and_partial_score_has_no_total(self):
        report=self.report();items=analysis_output()['score_suggestions']
        items[0].update(score=None,base_score=None,evidence=[],uncertainty='材料不足')
        result=rubric_scoring.validate(items,report)
        self.assertIsNone(result['suggested_total']);self.assertFalse(result['scoring_complete'])
        items[0]['uncertainty']=''
        with self.assertRaises(ValueError):rubric_scoring.validate(items,report)

    def test_deduction_arithmetic_direction_and_report_wide_cap(self):
        report=self.report();report['assignment']['rubric']['special_rules']=[{'id':'refs','kind':'deduction','maximum_adjustment':4}]
        items=analysis_output()['score_suggestions']
        items[0].update(score=16,adjustments=[{'rule_id':'refs','points':-2,'reason':'缺少一条参考文献，扣2分。'}])
        self.assertEqual(rubric_scoring.validate(items,report)['suggested_total'],68)
        items[1].update(score=21,adjustments=[{'rule_id':'refs','points':-3,'reason':'其他扣分'}])
        with self.assertRaisesRegex(ValueError,'上限'):rubric_scoring.validate(items,report)
        items[0]['adjustments'][0]['points']=2
        with self.assertRaisesRegex(ValueError,'方向'):rubric_scoring.validate(items,report)

    def test_score_generation_preserves_existing_teacher_work(self):
        report=self.report();path='reports/'+report['id']
        report=self.call(path+'/save',{'revision':report['revision'],'scores':{'methods':12},'teacher_summary':'教师概览','feedback':'教师反馈','notes':'私人笔记'})
        output=backend.validate_analysis(analysis_output(),report)
        output.update(mode='deepseek',model='fictional-model',generated=backend.now(),prompt_version='test')
        with patch.object(backend,'analyze',return_value=output) as analyze:
            scored=self.call(path+'/score',{'revision':report['revision']})
        self.assertEqual(scored['scores'],{'methods':12});self.assertEqual(scored['feedback'],'教师反馈')
        self.assertEqual(scored['notes'],'私人笔记');self.assertEqual(scored['teacher_summary'],'教师概览')
        self.assertEqual(scored['analysis']['suggested_total'],70)
        self.assertEqual(analyze.call_args.args[0]['assignment'],report['assignment'])
        self.assertEqual(self.call(path)['analysis'],scored['analysis'])

    def test_unreadable_visual_material_does_not_produce_complete_numeric_grade(self):
        report=self.report()
        report['word_source']={'version':'word-native-v1','objects':[{'id':'fig1'}]}
        output=analysis_output();output['visual_checks']=[{'object_id':'fig1','status':'unclear','summary':'无法读取图像'}]
        coverage={'objects':[{'id':'fig1','status':'image_sent'}],'warnings':[],'state':'complete'}
        with patch('word_source.inputs',return_value=({'objects':[],'tables':[]},[],coverage)),patch.object(backend,'KEY','fake'),patch.object(backend,'urlopen',return_value=response(output)):
            result=backend.analyze(report,'deepseek',{'model':'deepseek-flash'},None)
        self.assertIsNone(result['suggested_total']);self.assertTrue(all(s['score'] is None for s in result['score_suggestions']))


class DualProcessingTests(RubricTestCase):
    def test_code_mode_keeps_original_parser_and_does_not_call_model(self):
        with patch.object(backend,'urlopen') as upstream:
            parsed=self.call('rubric-import',{'source_text':'方法（30分）\n结果（70分）'})
            aid=self.call('assignments',{'title':'原代码版本','processing_mode':'code','source_text':parsed['source_text']})['id']
        upstream.assert_not_called()
        saved=next(a for a in self.call('bootstrap')['assignments'] if a['id']==aid)
        self.assertEqual(saved['rubric']['processing_mode'],'code')
        self.assertEqual(self.call('rubric-import',{'source_text':'方法30分，结果70分'})['processing_mode'],'code')
        report=self.call('reports',{'assignment_id':aid,'sample':True})
        legacy={'summary':'原有反馈','outline':[],'claims':[],'findings':[]}
        with patch.object(backend,'KEY','fake'),patch.object(backend,'urlopen',return_value=response(legacy)) as request:
            result=backend.analyze(report,'deepseek',{'model':'deepseek-flash'},None)
        self.assertNotIn('score_suggestions',result)
        self.assertNotIn('score_suggestions',json.loads(request.call_args.args[0].data)['messages'][0]['content'])
        self.assertEqual(result['prompt_version'],'writing-review-v3')
        with self.assertRaisesRegex(ValueError,'代码版本'):
            self.call('reports/'+report['id']+'/score',{'revision':report['revision']})

    def test_switching_assignment_method_keeps_old_report_snapshot(self):
        aid=self.call('assignments',{'title':'两版本','source_text':'方法（30分）\n结果（70分）'})['id']
        old=self.call('reports',{'assignment_id':aid,'sample':True})
        parsed=self.understand(assignment_type='实验报告')
        self.call('assignments/'+aid,{'title':'两版本','revision':1,'assignment_type':'实验报告','processing_mode':'ai',
                                     'source_text':parsed['source_text'],'rubric_understanding':parsed})
        new=self.call('reports',{'assignment_id':aid,'sample':True})
        self.assertEqual(self.call('reports/'+old['id'])['assignment']['rubric']['processing_mode'],'code')
        self.assertEqual(new['assignment']['rubric']['processing_mode'],'ai')
        self.assertEqual(new['assignment']['revision'],2)

    def test_drafts_are_separate_per_method_and_mismatched_save_rejected(self):
        for mode in ['code','ai']:
            self.call('rubric-draft',{'source_text':mode+' original text','processing_mode':mode})
        drafts=self.call('rubric-draft')['drafts']
        self.assertEqual({d['processing_mode']:d['source_text'] for d in drafts}, {'code':'code original text','ai':'ai original text'})
        parsed=self.understand(assignment_type='实验报告')
        with self.assertRaisesRegex(ValueError,'版本'):
            self.save(parsed,processing_mode='code')
