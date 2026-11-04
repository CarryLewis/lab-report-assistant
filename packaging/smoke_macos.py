"""Exercise the built executable without a source tree or Python environment."""
import argparse
import base64
import io
import hashlib
import json
import os
from pathlib import Path
import signal
import shutil
import socket
import subprocess
import tempfile
import time
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener
import zipfile

OPENER = build_opener(ProxyHandler({}))
ROOT = Path(__file__).resolve().parents[1]


def request(record, path, body=None, raw=False):
    headers = {'Content-Type':'application/json'} if body is not None else {}
    req = Request(record['url'] + path.lstrip('/'), data=json.dumps(body).encode() if body is not None else None, headers=headers)
    with OPENER.open(req, timeout=20) as response:
        data = response.read()
    return data if raw else json.loads(data)


def start(binary, data, ready, port=0):
    environment = {key:value for key,value in os.environ.items() if key not in
                   ('PYTHONPATH','PYTHONHOME','VIRTUAL_ENV','DEEPSEEK_API_KEY','LABWISE_DATA_DIR','LABWISE_PORT')}
    environment['LABWISE_SOFFICE'] = '/not-installed-for-this-smoke-test'
    process = subprocess.Popen([str(binary),'--serve','--no-browser','--data-dir',str(data),
                                '--port',str(port),'--ready-file',str(ready)],cwd=ready.parent,env=environment,
                               stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    deadline=time.monotonic()+30
    while time.monotonic()<deadline:
        if ready.exists():
            return process,json.loads(ready.read_text())
        if process.poll() is not None:
            raise RuntimeError('包内程序启动失败：'+str(process.communicate()))
        time.sleep(.1)
    process.kill()
    process.communicate()
    raise RuntimeError('包内程序启动超时。')


def stop(process):
    if process.poll() is None:
        process.send_signal(signal.SIGINT)
        try:
            process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.communicate(timeout=5)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('app',type=Path)
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args()
    source_app=args.app.resolve()
    checks=[]
    with tempfile.TemporaryDirectory(prefix='labwise-installed-smoke-') as work:
        root=Path(work);data=root/'data'
        installed=root/'Applications'/'Labwise.app'
        subprocess.run(['ditto',str(source_app),str(installed)],check=True)
        binary=installed/'Contents/MacOS/Labwise'
        occupied=socket.socket();occupied.bind(('127.0.0.1',0));occupied.listen()
        process,record=start(binary,data,root/'ready.json',occupied.getsockname()[1])
        try:
            assert record['port']!=occupied.getsockname()[1]
            assert request(record,'api/pilot/health')['instance_id']==record['instance_id']
            checks.append('packaged-runtime-and-port-fallback')
            for path in ('','review-layout.css','design-system.css','user-support.js','teacher-live.js','word-reader.html','vendor/pdfjs/pdf.mjs'):
                assert request(record,path,raw=True)
            checks.append('bundled-assets-without-source-environment')
            stylesheet=request(record,'design-system.css',raw=True)
            assert b'--font-ui:' in stylesheet and b'--icon-menu:' in stylesheet
            assert b'/design-system.css?v=1.3.6' in request(record,'',raw=True)
            for reader in ('word-reader.html','original-reader.html'):
                assert b'/design-system.css?v=1.3.6' in request(record,reader,raw=True)
            assert b'/review-layout.css?v=1.3.6' in request(record,'',raw=True)
            assert b'height:100dvh' in request(record,'review-layout.css',raw=True)
            checks.append('shared-typography-icons-and-compact-review-layout')
            profiles=request(record,'api/pilot/writing-profiles')['profiles']
            assert len(profiles)==8
            essay=next(p for p in profiles if p['id']=='academic_essay')
            source='\n\n'.join(f"{c['name']}（{c['maximum_points']}分）\n{c['descriptor']}" for c in essay['criteria'])
            created=request(record,'api/pilot/assignments',{'title':'虚构文体验收','assignment_type':essay['name'],'instructions':essay['instructions'],'source_text':source})
            saved=next(a for a in request(record,'api/pilot/bootstrap')['assignments'] if a['id']==created['id'])
            assert saved['writing_profile']['id']=='academic_essay'
            assert sum(c['maximum_points'] for c in saved['rubric']['criteria'])==100
            assert b'writingTemplate' in request(record,'assignment-editor.js',raw=True)
            checks.append('eight-writing-profiles-and-non-lab-rubric-persistence')
            page=request(record,'',raw=True)
            editor=request(record,'assignment-editor.js',raw=True)
            assert all(token in page for token in (b'rubricProcessingMode',b'rubricPreviewStatus',b'rubricPreviewHelp'))
            assert b'scheduleRubricPreview' in editor and b'if(imported)await inspectRubric' in editor
            assert request(record,'i18n-en.js',raw=True) and request(record,'i18n.js',raw=True)
            checks.append('automatic-rubric-preview-and-language-assets')
            natural='整体评价满分20分。优秀16至20分：论证充分。'
            understanding={'schema_version':'rubric-understanding.v1','input_type':'holistic','summary':'整体20分制',
                'declared_total':20,'questions':[],'special_rules':[],'source_text':natural,
                'context_key':hashlib.sha256(json.dumps([natural,'实验报告',''],ensure_ascii=False).encode()).hexdigest(),
                'criteria':[{'id':'overall','name':'整体评价','maximum_points':20,'descriptor':'论证充分','source_quote':natural,
                    'levels':[{'label':'优秀','minimum':16,'maximum':20,'descriptor':'论证充分','source_quote':'优秀16至20分：论证充分'}]}]}
            rich=request(record,'api/pilot/assignments',{'title':'虚构AI版本验收','assignment_type':'实验报告',
                'processing_mode':'ai','source_text':natural,'rubric_understanding':understanding})
            rich_saved=next(a for a in request(record,'api/pilot/bootstrap')['assignments'] if a['id']==rich['id'])
            assert rich_saved['rubric']['processing_mode']=='ai'
            assert rich_saved['rubric']['criteria'][0]['levels'][0]['maximum']==20
            assert saved['rubric']['processing_mode']=='code'
            for method in ('code','ai'):
                request(record,'api/pilot/rubric-draft',{'processing_mode':method,'source_text':method+' draft'})
            drafts=request(record,'api/pilot/rubric-draft')['drafts']
            assert {d['processing_mode'] for d in drafts}=={'code','ai'}
            checks.append('packaged-AI-understanding-and-separate-code-AI-drafts')

            assert not request(record,'api/pilot/bootstrap')['settings']['has_key']
            assignment=request(record,'api/pilot/assignments',{'title':'虚构安装验收','source_text':'方法（40分）\n说明步骤。\n结果（60分）\n说明局限。'})
            report=request(record,'api/pilot/reports',{'assignment_id':assignment['id'],'filename':'fictional.docx',
                           'file':base64.b64encode((ROOT/'examples/ai-analysis-test.docx').read_bytes()).decode()})
            assert request(record,'api/pilot/reports/'+report['id']+'/word-view')['html']
            scores={criterion['id']:criterion['maximum_points']*.8 for criterion in report['assignment']['rubric']['criteria']}
            report=request(record,'api/pilot/reports/'+report['id']+'/confirm',{
                'revision':report['revision'],'scores':scores,'notes':'PRIVATE_INSTALL_TEST_NOTE','feedback':'Fictional teacher feedback'})
            assert 'PRIVATE_INSTALL_TEST_NOTE' not in request(record,'api/pilot/reports/'+report['id']+'/export')['content']
            exported=request(record,'api/pilot/reports/'+report['id']+'/export-reviewed')
            package=base64.b64decode(exported['content'])
            with zipfile.ZipFile(io.BytesIO(package)) as archive:
                assert any(name.endswith('.docx') for name in archive.namelist())
            checks.append('word-import-manual-review-confirmation-and-export')
            try:
                request(record,'api/pilot/reports/'+report['id']+'/export-pdf',{'revision':report['revision']})
                raise AssertionError('Missing converter was silently accepted')
            except HTTPError as error:
                assert error.code==400 and 'LibreOffice' in json.load(error)['error']
            checks.append('missing-converter-is-actionable')
            backup=request(record,'api/pilot/backup',{})
            restored=request(record,'api/pilot/restore-backup',{'file':backup['content']})
            assert ' server.py' not in Path(restored['launcher']).read_text()
            assert Path(restored['directory'])!=data
            checks.append('packaged-backup-and-independent-restore')
            second,duplicate=start(binary,data,root/'duplicate.json')
            second.wait(timeout=5)
            assert duplicate['instance_id']==record['instance_id'] and process.poll() is None
            checks.append('repeat-launch-reuses-one-workspace')
        finally:
            occupied.close()
            stop(process)
        # Simulate replacing only the installed program, with its course data
        # stored elsewhere. This is not a claim about future schema migrations.
        shutil.rmtree(installed)
        subprocess.run(['ditto',str(source_app),str(installed)],check=True)
        process,reopened=start(binary,data,root/'reopened.json')
        try:
            loaded=request(reopened,'api/pilot/reports/'+report['id'])
            assert loaded['confirmed'] and loaded['scores']==scores and loaded['notes']=='PRIVATE_INSTALL_TEST_NOTE'
            assert loaded['feedback']=='Fictional teacher feedback'
            checks.append('restart-preserves-confirmed-teacher-records')
            checks.append('same-version-program-replacement-keeps-data')
            recovered,copy=start(binary,Path(restored['directory']),root/'restored.json')
            try:
                loaded_copy=request(copy,'api/pilot/reports/'+report['id'])
                assert loaded_copy['scores']==scores and loaded_copy['notes']=='PRIVATE_INSTALL_TEST_NOTE'
                checks.append('independent-restored-workspace-reopens')
            finally:
                stop(recovered)
        finally:
            stop(process)
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps({'application':'Labwise','passed':True,'checks':checks,
                                     'real_ai_called':False,'user_data_used':False},ensure_ascii=False,indent=2))
    print('包内程序安装验收通过：'+str(len(checks))+' 类检查。')


if __name__=='__main__':
    main()
