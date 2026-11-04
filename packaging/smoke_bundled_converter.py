"""Relocate the trial app and exercise its bundled DOCX converter in isolation."""
import argparse
import base64
import io
import json
from pathlib import Path
import os
import subprocess
import tempfile

from pypdf import PdfReader
from smoke_macos import ROOT, request, start, stop


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('app', type=Path)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='labwise-bundled-word-') as work:
        root = Path(work).resolve()
        app = root / '移动应用 中文 路径/Labwise.app'
        subprocess.run(['ditto', str(args.app.resolve()), str(app)], check=True)
        converter = app / 'Contents/Helpers/LibreOffice.app/Contents/MacOS/soffice'
        assert converter.is_file()
        binary = app / 'Contents/MacOS/Labwise'
        env = {k:v for k,v in os.environ.items() if k not in
               ('LABWISE_SOFFICE','PYTHONPATH','PYTHONHOME','VIRTUAL_ENV','LABWISE_DATA_DIR')}
        env['PATH'] = '/usr/bin:/bin'
        preflight = root / 'preflight.json'
        subprocess.run([str(binary), '--self-test', '--report', str(preflight)], env=env, cwd=root, check=True)
        status = json.loads(preflight.read_text())
        assert status['paged_word_export'] and status['word_converter'] == str(converter), status
        process, record = start(binary, root/'data', root/'ready.json', converter=None)
        try:
            assignment = request(record, 'api/pilot/assignments', {
                'title':'虚构包内转换验收', 'source_text':'方法（100分）\n说明方法与重复次数。'})
            report = request(record, 'api/pilot/reports', {
                'assignment_id':assignment['id'], 'filename':'fictional.docx',
                'file':base64.b64encode((ROOT/'examples/ai-analysis-test.docx').read_bytes()).decode()})
            scores = {c['id']:c['maximum_points']*.8 for c in report['assignment']['rubric']['criteria']}
            report = request(record, 'api/pilot/reports/'+report['id']+'/confirm', {
                'revision':report['revision'], 'scores':scores,
                'notes':'PRIVATE_BUNDLED_CONVERTER_NOTE', 'feedback':'Bundled conversion verification.'})
            export = request(record, 'api/pilot/reports/'+report['id']+'/export-pdf', {'revision':report['revision']})
            pdf = PdfReader(io.BytesIO(base64.b64decode(export['content'])))
            text = '\n'.join(page.extract_text() for page in pdf.pages)
            assert 'Fictional Growth Curve Report' in text
            assert 'PRIVATE_BUNDLED_CONVERTER_NOTE' not in text
            assert export['summary']['details'][0]['source_pages'] > 0
            saved = request(record, 'api/pilot/reports/'+report['id'])
            assert saved['confirmed'] and saved['revision'] == report['revision']
            subprocess.run(['codesign', '--verify', '--deep', '--strict', str(app)], check=True)
            result = {'passed':True, 'version':status['version'],
                      'bundled_converter_used':True, 'external_converter_override':False,
                      'external_cli_path_removed':True, 'relocated_unicode_app_path':True,
                      'word_pdf_export':True, 'app_signature_valid_after_conversion':True,
                      'source_pages':export['summary']['details'][0]['source_pages'],
                      'user_data_used':False}
        finally:
            stop(process)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print('包内 LibreOffice 实际转换、移动路径与签名验收通过。')


if __name__ == '__main__':
    main()
