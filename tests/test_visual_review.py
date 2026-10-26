import base64
import hashlib
import io
import json
import struct
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError
import pilot_backend as p
import visual_review as v
from ai_fixtures import create_assignment


def png():
    def chunk(kind, data):
        return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',32,32,8,2,0,0,0))+chunk(b'IDAT',zlib.compress((b'\0'+b'\xff\xff\xff'*32)*32))+chunk(b'IEND',b'')


def output():
    return {'visual_type':'chart','explanation':'A rising curve with no visible error bars.',
            'observations':['The x-axis is time.'],
            'checks':[{'category':c,'status':'uncertain','evidence':'Cannot establish from this crop.',
                       'explanation':'Needs context.','recommendation':'Check source data.'} for c in v.CATEGORIES]}


class VisualReviewTests(unittest.TestCase):
    def test_column_statistics_and_missing_values(self):
        stats=v.data_statistics('time_min,OD600\n0,0.1\n30,0.3\n60,\n')
        self.assertEqual(stats['columns'][1]['numeric_count'],2)
        self.assertEqual(stats['columns'][1]['missing_count'],1)
        self.assertAlmostEqual(stats['columns'][1]['mean'],0.2)
        self.assertAlmostEqual(stats['columns'][1]['sample_sd'],2**.5/10)
        mixed=v.data_statistics('value\n0.1\nnot-readable\n')['columns'][0]
        self.assertNotIn('mean',mixed)
        for raw in ['x,x\n1,2','x\nnan','x\ninf','x,y\n1','x,y']:
            with self.assertRaises(ValueError):v.data_statistics(raw)

    def test_region_and_visual_output_validation(self):
        body={'page':1,'bbox':[0,0,1,1],'image':base64.b64encode(png()).decode()}
        self.assertEqual(v.prepare(body)['page'],1)
        for bad in [dict(body,page=True),dict(body,bbox=[0,1,1,0]),dict(body,image='not an image')]:
            with self.assertRaises(ValueError):v.prepare(bad)
        self.assertEqual(len(v.validate(output())['checks']),5)
        broken=output();broken['checks'].pop()
        with self.assertRaises(ValueError):v.validate(broken)

    def test_saved_visual_review_source_binding_and_teacher_decision(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(p,'DATA',Path(folder)),patch.object(p,'KEY','test-key'):
            p.init();aid=create_assignment()
            body={'assignment_id':aid,'sample':True};r=p.dispatch('POST','/api/pilot/reports',body,None)
            raw=b'saved-original-fixture';digest=hashlib.sha256(raw).hexdigest()
            (Path(folder)/'sources').mkdir();(Path(folder)/'sources'/(r['id']+'.bin')).write_bytes(raw)
            with p.db() as c:r.update(source_sha256=digest,source_filename='fixture.pdf');p.persist(c,r)
            path='/api/pilot/reports/'+r['id'];request={'revision':r['revision'],'source_sha256':digest,'page':1,'bbox':[0,0,1,1],'image':base64.b64encode(png()).decode(),'raw_data':'x\n1\n2'}
            with patch.object(v,'urlopen',return_value=io.BytesIO(json.dumps({'choices':[{'finish_reason':'stop','message':{'content':json.dumps(output())}}]}).encode())) as upstream:
                result=p.dispatch('POST',path+'/visual-review',request,None)
            sent=json.loads(upstream.call_args.args[0].data)
            self.assertEqual(sent['messages'][1]['content'][1]['type'],'image_url')
            self.assertEqual(json.loads(sent['messages'][1]['content'][0]['text'])['raw_csv'],'x\n1\n2')
            self.assertEqual(result['status'],'parsed');self.assertEqual(len(result['visual_reviews']),1)
            review=result['visual_reviews'][0];self.assertEqual(review['decision'],'pending')
            self.assertEqual(review['raw_data'],'x\n1\n2')
            image=p.dispatch('GET',path+'/visual-image/'+review['id'],{},None)
            self.assertEqual(base64.b64decode(image['image']),png())
            request['revision']=result['revision'];request['source_sha256']='stale'
            with self.assertRaisesRegex(ValueError,'版本不一致'):p.dispatch('POST',path+'/visual-review',request,None)
            confirmation={'revision':result['revision'],'feedback':'Teacher feedback','scores':{'methods':30,'results':30,'discussion':40}}
            with self.assertRaisesRegex(ValueError,'图表'):p.dispatch('POST',path+'/confirm',confirmation,None)
            confirmation['visual_decisions']={review['id']:'accepted'}
            confirmed=p.dispatch('POST',path+'/confirm',confirmation,None)
            self.assertEqual(confirmed['visual_reviews'][0]['decision'],'accepted')
            self.assertTrue(confirmed['confirmed'])

    def test_vision_network_errors_are_actionable(self):
        region=v.prepare({'page':1,'bbox':[0,0,1,1],'image':base64.b64encode(png()).decode()})
        with patch.object(v,'urlopen',side_effect=URLError('offline')),self.assertRaisesRegex(ValueError,'网络'):
            v.analyze(region,{},'test-key','deepseek-flash',None)
        with self.assertRaisesRegex(ValueError,'deepseek-flash'):
            v.analyze(region,{},'test-key','deepseek-v4-pro',None)

    def test_image_only_pdf_page_preserves_original_page_number(self):
        from pypdf import PdfWriter
        writer=PdfWriter();writer.add_blank_page(width=595,height=842)
        stream=io.BytesIO();writer.write(stream)
        paragraphs=p.paragraphs_pdf(stream.getvalue())
        self.assertEqual(len(paragraphs),1)
        self.assertEqual(paragraphs[0]['page'],1)
        self.assertTrue(paragraphs[0]['visual_only'])
