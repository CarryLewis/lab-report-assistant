import base64
import hashlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject
import pilot_backend as p
import visual_discovery as v
from ai_fixtures import create_assignment

FIXTURE=Path(__file__).resolve().parents[1]/'examples/visual-audit-test.pdf'


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.data_patch=patch.object(p,'DATA',self.root);self.data_patch.start();p.init()
        aid=create_assignment()
        self.report=p.dispatch('POST','/api/pilot/reports',{'assignment_id':aid,'filename':'visuals.pdf','file':base64.b64encode(FIXTURE.read_bytes()).decode()},None)
        self.path='/api/pilot/reports/'+self.report['id']

    def tearDown(self):
        self.data_patch.stop();self.temp.cleanup()

    def call(self,action,**body):
        self.report=p.dispatch('POST',self.path+'/'+action,{'revision':self.report['revision'],**body},None)
        return self.report

    def scan(self):
        self.call('visual-scan')
        while self.report['visual_scan']['status']=='running':self.call('visual-scan-next',scan_id=self.report['visual_scan']['id'])
        return self.report

    def test_detection_coverage_dedup_and_persistence(self):
        r=self.scan();self.assertEqual(r['visual_scan']['processed'],3)
        self.assertEqual(r['visual_scan']['status'],'partial_completed')
        self.assertEqual([x['state'] for x in r['visual_scan']['pages']],['with_candidates','with_candidates','needs_supplement'])
        self.assertEqual(len(r['visual_objects']),3)
        table=next(o for o in r['visual_objects'] if o['page']==2)
        self.assertEqual(table['type'],'table');self.assertIn('table_lines',table['sources'])
        self.assertEqual(len([o for o in r['visual_objects'] if o['page']==2]),1)
        restored=p.dispatch('GET',self.path+'/visual-inventory',{},None)
        self.assertEqual(restored['scan']['id'],r['visual_scan']['id'])
        thumb=p.dispatch('GET',self.path+'/visual-thumbnail/'+table['id'],{},None)
        self.assertTrue(base64.b64decode(thumb['image']).startswith(b'\x89PNG'))
        self.assertEqual(r['visual_scan']['external_calls'],0)

    def test_pause_resume_idempotency_and_teacher_edits_survive_rescan(self):
        self.call('visual-scan');job=self.report['visual_scan']['id']
        self.call('visual-scan');self.assertEqual(job,self.report['visual_scan']['id'])
        self.call('visual-scan-next',scan_id=job);self.call('visual-scan-cancel',scan_id=job)
        self.assertEqual(self.report['visual_scan']['status'],'cancelled')
        oid=self.report['visual_objects'][0]['id']
        self.call('visual-object',id=oid,type='chart',title='Teacher corrected',decision='confirmed',source_sha256=self.report['source_sha256'])
        self.call('visual-scan');self.assertEqual(self.report['visual_scan']['processed'],1)
        while self.report['visual_scan']['status']=='running':self.call('visual-scan-next',scan_id=job)
        self.call('visual-scan',rescan=True)
        self.assertNotEqual(job,self.report['visual_scan']['id'])
        while self.report['visual_scan']['status']=='running':self.call('visual-scan-next',scan_id=self.report['visual_scan']['id'])
        edited=next(o for o in self.report['visual_objects'] if o['id']==oid)
        self.assertEqual(edited['title'],'Teacher corrected');self.assertEqual(edited['type'],'chart')
        self.assertEqual(len(self.report['visual_objects']),3)

    def test_failed_page_retry_and_bad_requests(self):
        self.call('visual-scan');job=self.report['visual_scan']['id']
        with patch.object(v,'scan_page',side_effect=ValueError('fixture page failure')):
            self.call('visual-scan-next',scan_id=job)
        self.assertEqual(self.report['visual_scan']['pages'][0]['state'],'failed')
        self.call('visual-scan',retry=True)
        self.assertEqual(self.report['visual_scan']['pages'][0]['state'],'pending')
        self.call('visual-scan-cancel',scan_id=job)
        for body in [dict(page=1,bbox=[0,0,0,1]),dict(page=True,bbox=[0,0,1,1]),dict(page=99,bbox=[0,0,1,1])]:
            with self.assertRaises(ValueError):self.call('visual-object',source_sha256=self.report['source_sha256'],**body)
        self.call('visual-object',page=1,bbox=[0,.1,.8,.8],source_sha256=self.report['source_sha256'])
        self.assertTrue(self.report['visual_objects'][-1]['manual'])
        self.assertEqual(self.report['visual_objects'][-1]['decision'],'pending')
        with self.assertRaises(ValueError):self.call('visual-object',page=1,bbox=[0,0,1,1],source_sha256='stale')
        with self.assertRaises(ValueError):p.dispatch('POST',self.path+'/visual-scan',{'revision':0},None)

    def test_vector_blank_and_rotated_crop_coordinates(self):
        writer=PdfWriter();page=writer.add_blank_page(width=600,height=800)
        stream=DecodedStreamObject();stream.set_data(b'1 w 100 200 m 100 500 l 400 500 l S 100 200 m 200 300 l 300 350 l 400 430 l S')
        page[NameObject('/Contents')]=writer._add_object(stream)
        target=self.root/'vector.pdf'
        with target.open('wb') as f:writer.write(f)
        found,status=v.scan_page(target,1,'vector')
        self.assertEqual(len(found),1);self.assertIn('vector_graphics',found[0]['sources'])
        self.assertAlmostEqual(found[0]['bbox'][0],96/600,places=5)
        reader=PdfReader(FIXTURE);pg=reader.pages[0];pg.cropbox.lower_left=(40,150);pg.cropbox.upper_right=(555,750);pg.rotate(90)
        rotated=PdfWriter();rotated.add_page(pg)
        with target.open('wb') as f:rotated.write(f)
        found,status=v.scan_page(target,1,'rotated')
        self.assertEqual(status['rotation'],90);self.assertEqual(len(found),1)
        for x in found[0]['bbox']:self.assertGreaterEqual(x,0);self.assertLessEqual(x,1)
        self.assertAlmostEqual(status['width'],600);self.assertAlmostEqual(status['height'],515)
        # PDF.js displays the rotated CropBox. The raster's original x range
        # becomes the displayed y range, measured relative to original crop x=40.
        self.assertAlmostEqual(found[0]['bbox'][1],(48-40-4)/515,places=5)
        blank=PdfWriter();blank.add_blank_page(width=600,height=800)
        with target.open('wb') as f:blank.write(f)
        found,status=v.scan_page(target,1,'blank')
        self.assertEqual(found,[]);self.assertEqual(status['state'],'no_candidates')

    def test_word_preview_is_pinned_and_shared(self):
        with p.db() as c:
            self.report['source_filename']='visuals.docx';p.persist(c,self.report)
        response={'content_type':'application/pdf','file':base64.b64encode(FIXTURE.read_bytes()).decode(),'warnings':[]}
        with patch('document_preview.preview',return_value=response) as converter:
            result=p.dispatch('GET',self.path+'/visual-preview',{},None)
            self.call('visual-scan')
            self.assertEqual(converter.call_count,1)
            self.assertEqual(result['sha256'],self.report['visual_scan']['preview_sha256'])
            self.assertEqual(base64.b64decode(result['file']),FIXTURE.read_bytes())


if __name__=='__main__':unittest.main()
