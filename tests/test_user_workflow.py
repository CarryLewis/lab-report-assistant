import base64
import hashlib
import io
import json
import sqlite3
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import auto_analysis
import local_backup
import pilot_backend as p
from ai_fixtures import create_assignment


class UserWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.patches = [patch.object(p, 'DATA', self.root / 'active'),
                        patch.object(p, 'KEY', ''), patch.object(p, 'ENV_KEY', ''),
                        patch.object(p, 'KEY_SOURCE', None)]
        for item in self.patches:
            item.start()
        p.init()
        self.assignment_id = create_assignment()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def call(self, path, body=None):
        return p.dispatch('GET' if body is None else 'POST', '/api/pilot/' + path, body or {}, None)

    def report(self):
        output = io.BytesIO()
        with zipfile.ZipFile(output, 'w') as archive:
            archive.writestr('word/document.xml', '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Fictional measurement at 600 nm.</w:t></w:r></w:p></w:body></w:document>')
        return self.call('reports', {'assignment_id': self.assignment_id, 'filename': 'fictional.docx',
                                     'file': base64.b64encode(output.getvalue()).decode()})

    def configure(self, **overrides):
        return self.call('settings', {'model': 'deepseek-flash', 'api_key': 'sk-fictional-test-only', **overrides})

    def test_connection_result_persists_and_changes_invalidate_it(self):
        self.configure()
        self.assertNotIn('connection_test', self.call('bootstrap')['settings'])
        with patch.object(p, 'analyze', return_value={'model': 'deepseek-flash'}):
            self.call('test-analysis', {})
        settings = self.call('bootstrap')['settings']
        self.assertEqual(settings['connection_test']['state'], 'passed')
        self.assertNotIn('_connection_key_hash', settings)
        self.configure(api_key='', model='deepseek-v4-pro')
        self.assertNotIn('connection_test', self.call('bootstrap')['settings'])
        with patch.object(p, 'analyze', side_effect=ValueError('not available')):
            with self.assertRaises(ValueError):
                self.call('test-analysis', {})
        self.assertEqual(self.call('bootstrap')['settings']['connection_test']['state'], 'failed')
        self.configure(model='deepseek-v4-pro', api_key='another-fictional-key')
        self.assertNotIn('connection_test', self.call('bootstrap')['settings'])

    def test_old_inflight_test_cannot_validate_changed_configuration(self):
        self.configure()
        def changed(*args):
            self.configure(model='deepseek-v4-pro')
            return {'model': 'deepseek-flash'}
        with patch.object(p, 'analyze', side_effect=changed):
            with self.assertRaisesRegex(ValueError, '配置已变化'):
                self.call('test-analysis', {})
        self.assertNotIn('connection_test', self.call('bootstrap')['settings'])

    def test_background_analysis_preserves_draft_saved_while_running(self):
        self.configure()
        r = self.report()
        started, release = threading.Event(), threading.Event()
        def analyze(*args):
            started.set()
            if not release.wait(5):
                raise AssertionError('worker not released')
            return {'mode': 'deepseek', 'model': 'deepseek-flash', 'findings': [], 'summary': 'Fictional overview'}
        errors = []
        def worker():
            try:
                auto_analysis.run_one(None)
            except Exception as error:
                errors.append(error)
        with patch.object(p, 'analyze', side_effect=analyze):
            thread = threading.Thread(target=worker)
            thread.start()
            try:
                self.assertTrue(started.wait(3))
                current = self.call('reports/' + r['id'])
                self.assertEqual(current['status'], 'analyzing')
                saved = self.call('reports/' + r['id'] + '/save', {
                    'revision': current['revision'], 'notes': 'private draft',
                    'feedback': 'teacher feedback', 'scores': {'methods': 12}, 'reviews': {}})
                self.assertEqual(saved['notes'], 'private draft')
                with self.assertRaises(ValueError):
                    self.call('reports/' + r['id'] + '/confirm', {'revision': saved['revision']})
            finally:
                release.set()
                thread.join(5)
        self.assertFalse(thread.is_alive())
        self.assertFalse(errors)
        final = self.call('reports/' + r['id'])
        self.assertEqual(final['status'], 'ready')
        self.assertEqual(final['notes'], 'private draft')
        self.assertEqual(final['scores'], {'methods': 12})
        self.assertEqual(final['feedback'], 'teacher feedback')
        with self.assertRaises(ValueError):
            self.call('reports/' + r['id'] + '/save', {'revision': saved['revision'], 'notes': 'stale'})

    def test_backup_restore_keeps_active_data_and_excludes_credentials(self):
        self.configure()
        r = self.report()
        saved = self.call('reports/' + r['id'] + '/save', {
            'revision': r['revision'], 'notes': 'private saved note', 'scores': {'methods': 21},
            'feedback': 'feedback', 'reviews': {}})
        pack = self.call('backup', {})
        with zipfile.ZipFile(io.BytesIO(base64.b64decode(pack['content']))) as archive:
            self.assertNotIn('deepseek_api_key', archive.namelist())
            self.assertIn('sources/' + r['id'] + '.bin', archive.namelist())
        active = p.DATA
        before = (active / 'pilot.sqlite3').read_bytes()
        restored = self.call('restore-backup', {'file': pack['content']})
        copy = Path(restored['directory'])
        self.assertNotEqual(copy, active)
        self.assertEqual(before, (active / 'pilot.sqlite3').read_bytes())
        self.assertFalse((copy / 'deepseek_api_key').exists())
        self.assertTrue(Path(restored['launcher']).is_file())
        with sqlite3.connect(copy / 'pilot.sqlite3') as connection:
            report = json.loads(connection.execute('SELECT payload FROM reports WHERE id=?', (r['id'],)).fetchone()[0])
            self.assertEqual(report['notes'], saved['notes'])
            self.assertEqual(report['scores'], saved['scores'])
            self.assertEqual(connection.execute('SELECT count(*) FROM revisions').fetchone()[0], 1)
            self.assertEqual(connection.execute('SELECT state FROM analysis_jobs').fetchone()[0], 'failed')

    def test_legacy_analyzer_still_blocks_save_to_avoid_stale_overwrite(self):
        r = self.report()
        with p.db() as connection:
            r['status'] = 'analyzing'
            p.persist(connection, r)
        with self.assertRaisesRegex(ValueError, '旧版分析'):
            self.call('reports/' + r['id'] + '/save', {'revision': r['revision'], 'notes': 'unsafe update'})
        self.assertEqual(self.call('reports/' + r['id'])['notes'], '')

    def test_restore_rejects_path_traversal_and_corrupt_archive_without_writing(self):
        self.report()
        pack = self.call('backup', {})
        raw = io.BytesIO(base64.b64decode(pack['content']))
        output = io.BytesIO()
        with zipfile.ZipFile(raw) as source, zipfile.ZipFile(output, 'w') as destination:
            for name in source.namelist():
                destination.writestr(name, source.read(name))
            destination.writestr('../outside.txt', 'not allowed')
        with self.assertRaises(ValueError):
            self.call('restore-backup', {'file': base64.b64encode(output.getvalue()).decode()})
        with self.assertRaises(ValueError):
            self.call('restore-backup', {'file': 'not a backup'})
        self.assertFalse(list(self.root.glob('Labwise-restored-*')))
        self.assertFalse((self.root / 'outside.txt').exists())

    def test_backup_missing_source_is_not_reported_as_complete(self):
        r = self.report()
        (p.DATA / 'sources' / (r['id'] + '.bin')).unlink()
        with self.assertRaisesRegex(ValueError, '缺失'):
            self.call('backup', {})

    def test_invalid_manifest_and_failed_launcher_do_not_publish_partial_restore(self):
        self.report()
        pack = self.call('backup', {})
        raw = io.BytesIO(base64.b64decode(pack['content']))
        output = io.BytesIO()
        with zipfile.ZipFile(raw) as source, zipfile.ZipFile(output, 'w') as target:
            for name in source.namelist():
                target.writestr(name, '[]' if name == 'manifest.json' else source.read(name))
        with self.assertRaises(ValueError):
            self.call('restore-backup', {'file': base64.b64encode(output.getvalue()).decode()})
        with patch.object(local_backup.os, 'chmod', side_effect=OSError('disk failure')):
            with self.assertRaises(OSError):
                self.call('restore-backup', {'file': pack['content']})
        self.assertFalse(list(self.root.glob('Labwise-restored-*')))
        self.assertFalse(list(self.root.glob('.labwise-restore-*')))
        self.assertEqual(len(self.call('bootstrap')['reports']), 1)

    def test_restore_checks_original_references_in_historical_versions(self):
        report = self.report()
        self.call('reports/' + report['id'] + '/save', {'revision': report['revision'], 'notes':'saved'})
        pack = self.call('backup', {})
        source = zipfile.ZipFile(io.BytesIO(base64.b64decode(pack['content'])))
        path = self.root / 'modified.sqlite3'
        path.write_bytes(source.read('pilot.sqlite3'))
        connection = sqlite3.connect(path)
        with connection:
            version_id, payload = connection.execute('SELECT id,payload FROM revisions').fetchone()
            historical = json.loads(payload)
            historical['source_sha256'] = 'not-the-backed-up-source'
            connection.execute('UPDATE revisions SET payload=? WHERE id=?', (json.dumps(historical),version_id))
        connection.close()
        database = path.read_bytes()
        manifest = json.loads(source.read('manifest.json'))
        manifest['files']['pilot.sqlite3'] = hashlib.sha256(database).hexdigest()
        output = io.BytesIO()
        with source, zipfile.ZipFile(output,'w') as target:
            for name in source.namelist():
                value = database if name=='pilot.sqlite3' else json.dumps(manifest).encode() if name=='manifest.json' else source.read(name)
                target.writestr(name,value)
        with self.assertRaises(ValueError):
            self.call('restore-backup', {'file': base64.b64encode(output.getvalue()).decode()})
        self.assertFalse(list(self.root.glob('Labwise-restored-*')))

    def test_installed_app_restore_launcher_does_not_expect_source_python_script(self):
        self.report()
        pack=self.call('backup',{})
        with patch.object(local_backup.sys,'frozen',True,create=True):
            restored=self.call('restore-backup',{'file':pack['content']})
        script=Path(restored['launcher']).read_text()
        self.assertNotIn(' server.py',script)
        self.assertIn('LABWISE_DATA_DIR=',script)


if __name__ == '__main__':
    unittest.main()
