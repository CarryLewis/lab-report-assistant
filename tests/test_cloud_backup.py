"""Isolated snapshot round trips and mocked provider failures; no real accounts."""
import base64
import io
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import zipfile

import cloud_backup as cloud
import local_backup
import pilot_backend as p
import server
from ai_fixtures import create_assignment


class CloudBackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.folder = self.root / 'drive'
        self.folder.mkdir()
        self.patches = [patch.object(p, 'DATA', self.root / 'active'),
                        patch.object(p, 'KEY', ''), patch.object(p, 'ENV_KEY', ''),
                        patch.object(p, 'KEY_SOURCE', None),
                        patch.dict(os.environ, {'LABWISE_ONEDRIVE_CLIENT_ID': '12345678-1234-1234-1234-123456789012'})]
        for item in self.patches:
            item.start()
        cloud.SESSIONS.clear()
        cloud.DUE.clear()
        p.init()

    def tearDown(self):
        cloud.SESSIONS.clear()
        cloud.DUE.clear()
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def call(self, path, body=None):
        return p.dispatch('GET' if body is None else 'POST', '/api/pilot/cloud/' + path, body or {}, None)

    def configure(self, provider='icloud', interval=0):
        return self.call('configure', {'provider': provider, 'folder': str(self.folder), 'interval': interval})

    def document(self):
        assignment = create_assignment()
        output = io.BytesIO()
        with zipfile.ZipFile(output, 'w') as archive:
            archive.writestr('word/document.xml', '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Fictional measurement at 600 nm.</w:t></w:r></w:p></w:body></w:document>')
        report = p.dispatch('POST', '/api/pilot/reports', {'assignment_id': assignment,
            'filename': 'fictional.docx', 'file': base64.b64encode(output.getvalue()).decode()}, None)
        return p.dispatch('POST', '/api/pilot/reports/' + report['id'] + '/save',
            {'revision': report['revision'], 'notes': 'Private saved note', 'feedback': 'Teacher feedback'}, None)

    def test_folder_round_trip_preserves_original_and_excludes_credentials(self):
        report = self.document()
        self.configure()
        (p.DATA / 'deepseek_api_key').write_text('fictional-secret')
        pack = self.call('backup', {'provider': 'icloud'})
        self.assertEqual(pack['state'], 'local_written')
        items = self.call('history', {'provider': 'icloud'})['items']
        self.assertEqual(items[0]['name'], pack['name'])
        raw = (self.folder / 'Labwise Backups' / pack['name']).read_bytes()
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            self.assertNotIn('cloud-backup.json', archive.namelist())
            self.assertNotIn('deepseek_api_key', archive.namelist())
        before = (p.DATA / 'pilot.sqlite3').read_bytes()
        result = self.call('restore', {'provider': 'icloud', 'id': pack['name']})
        self.assertTrue(result['original_unchanged'])
        self.assertEqual(before, (p.DATA / 'pilot.sqlite3').read_bytes())
        with sqlite3.connect(Path(result['directory']) / 'pilot.sqlite3') as connection:
            recovered = json.loads(connection.execute('SELECT payload FROM reports WHERE id=?', (report['id'],)).fetchone()[0])
        self.assertEqual(recovered['notes'], 'Private saved note')
        self.assertTrue(Path(result['launcher']).exists())

    def test_configure_is_opt_in_and_names_do_not_collide(self):
        with patch.object(local_backup, 'create') as create:
            status = self.configure('onedrive_folder', 15)
            create.assert_not_called()
        self.assertEqual(status['targets']['onedrive_folder']['interval'], 15)
        with patch.object(cloud.time, 'strftime', return_value='20261104T010000Z'):
            a = cloud.backup('onedrive_folder')
            b = cloud.backup('onedrive_folder')
        self.assertNotEqual(a['name'], b['name'])
        self.assertFalse(list((self.folder / 'Labwise Backups').glob('*.partial')))
        self.assertEqual(self.call('status')['targets']['icloud']['interval'], 0)

    def test_folder_validation_and_disable_unavailable_target(self):
        for value in (str(p.DATA), str(p.DATA / 'child'), 'relative', str(self.root / 'missing')):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.call('configure', {'provider': 'icloud', 'folder': value, 'interval': 15})
        destination = self.folder / 'Labwise Backups'
        destination.symlink_to(p.DATA, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.configure()
        destination.unlink()
        self.configure(interval=15)
        self.folder.rmdir()
        result = self.call('configure', {'provider': 'icloud', 'folder': '', 'interval': 0})
        self.assertEqual(result['targets']['icloud']['interval'], 0)

    def test_restore_rejects_corrupt_symlink_unknown_and_oversize(self):
        self.configure()
        pack = cloud.backup('icloud')
        path = self.folder / 'Labwise Backups' / pack['name']
        path.write_bytes(b'incomplete download')
        with self.assertRaises(ValueError):
            cloud.restore('icloud', pack['name'])
        path.unlink()
        path.symlink_to(p.DATA / 'pilot.sqlite3')
        self.assertEqual(cloud.history('icloud'), [])
        for name in (pack['name'], '../pilot.sqlite3'):
            with self.assertRaises(ValueError):
                cloud.restore('icloud', name)
        path.unlink()
        path.write_bytes(b'x' * 9)
        with patch.object(local_backup, 'LIMIT', 8), self.assertRaises(ValueError):
            cloud.restore('icloud', pack['name'])
        self.assertFalse(list(self.root.glob('Labwise-restored-*')))

    def test_failed_backup_retains_previous_success_and_releases_lock(self):
        self.configure()
        good = cloud.backup('icloud')
        status = cloud.status()['targets']['icloud']
        with patch.object(local_backup, 'create', side_effect=ValueError('资料超过限额')):
            with self.assertRaises(ValueError):
                cloud.backup('icloud')
        current = cloud.status()['targets']['icloud']
        self.assertEqual(current['last_success'], status['last_success'])
        self.assertIn('限额', current['error'])
        self.assertEqual(cloud.history('icloud')[0]['name'], good['name'])
        cloud.backup('icloud')

    def test_inflight_operation_blocks_target_and_account_changes(self):
        self.configure()
        cloud.OPERATION.acquire()
        try:
            for action, args in ((cloud.configure, ({'provider': 'icloud', 'folder': str(self.folder), 'interval': 0},)),
                                 (cloud.disconnect, ()), (cloud.connect, ()), (cloud.history, ('icloud',))):
                with self.assertRaisesRegex(ValueError, '另一个'):
                    action(*args)
        finally:
            cloud.OPERATION.release()

    def test_device_authorization_poll_refresh_and_disconnect(self):
        with patch.object(cloud, 'request', return_value={'device_code': 'private-device-code',
                'user_code': 'VISIBLE-CODE', 'verification_uri': 'https://microsoft.com/devicelogin', 'expires_in': 900, 'interval': 5}):
            result = cloud.connect()
        self.assertNotIn('device_code', result)
        with patch.object(cloud, 'request') as request:
            self.assertEqual(cloud.poll()['state'], 'pending')
            request.assert_not_called()
        cloud.session()['pending']['next'] = 0
        with patch.object(cloud, 'request', return_value={'error': 'slow_down'}):
            cloud.poll()
        self.assertEqual(cloud.session()['pending']['interval'], 10)
        cloud.session()['pending']['next'] = 0
        with patch.object(cloud, 'request', return_value={'access_token': 'access-secret', 'refresh_token': 'refresh-secret', 'expires_in': 3600}):
            self.assertEqual(cloud.poll()['state'], 'connected')
        cloud.session()['tokens']['expires'] = 0
        with patch.object(cloud, 'request', return_value={'access_token': 'new-secret', 'expires_in': 3600}):
            self.assertEqual(cloud.access_token(), 'new-secret')
        self.assertEqual(cloud.session()['tokens']['refresh_token'], 'refresh-secret')
        self.assertNotIn('secret', json.dumps(cloud.status()))
        self.assertNotIn('secret', (p.DATA / 'cloud-backup.json').read_text())
        cloud.disconnect()
        self.assertFalse(cloud.status()['targets']['onedrive']['connected'])

    def test_authorization_expiry_denial_and_missing_client_id(self):
        with patch.dict(os.environ, {'LABWISE_ONEDRIVE_CLIENT_ID': ''}), self.assertRaises(ValueError):
            cloud.connect()
        cloud.session()['pending'] = {'expires': 0, 'next': 0}
        with self.assertRaisesRegex(ValueError, '过期'):
            cloud.poll()
        cloud.session()['pending'] = {'expires': time.monotonic() + 100, 'next': 0, 'device_code': 'private'}
        with patch.object(cloud, 'request', return_value={'error': 'access_denied'}), self.assertRaises(ValueError):
            cloud.poll()
        self.assertNotIn('pending', cloud.session())
        with self.assertRaises(ValueError):
            self.configure('onedrive', 15)

    def test_graph_backup_and_remote_restore_round_trip_with_pagination(self):
        self.document()
        cloud.status()
        payload = {}
        def graph(path, method='GET', body=None, binary=False):
            if method == 'PUT':
                name = path.split(':/')[1].removesuffix(':/content')
                payload.update(name=name, raw=body)
                return {'name': name, 'size': len(body)}
            if binary:
                return payload['raw']
            item = {'id': 'remote-id', 'name': payload['name'], 'size': len(payload['raw']), 'file': {}}
            if 'page=2' in path:
                return {'value': [item]}
            return {'value': [], '@odata.nextLink': cloud.GRAPH + '/next?page=2'}
        with patch.object(cloud, 'graph', side_effect=graph):
            self.assertEqual(cloud.backup('onedrive')['state'], 'uploaded')
            self.assertEqual(cloud.history('onedrive')[0]['id'], 'remote-id')
            result = cloud.restore('onedrive', 'remote-id')
            self.assertTrue(result['original_unchanged'])
            with self.assertRaises(ValueError):
                cloud.restore('onedrive', 'outside-app-folder')

    def test_graph_rejects_bad_pagination_and_upload_result(self):
        with patch.object(cloud, 'graph', return_value={'value': [], '@odata.nextLink': 'https://untrusted.example/token'}):
            with self.assertRaises(ValueError):
                cloud.history('onedrive')
        with patch.object(cloud, 'graph', return_value={'name': 'wrong', 'size': 1}):
            with self.assertRaisesRegex(ValueError, '校验'):
                cloud.backup('onedrive')

    def test_download_redirect_drops_bearer_and_rejects_untrusted_hosts(self):
        opener = unittest.mock.Mock()
        opener.open.side_effect = [HTTPError(cloud.GRAPH, 302, 'redirect', {'Location': 'https://download.1drv.com/file'}, io.BytesIO()), io.BytesIO(b'backup')]
        with patch.object(cloud, 'build_opener', return_value=opener):
            self.assertEqual(cloud.request(cloud.GRAPH, token='secret', binary=True), b'backup')
        first, second = [call.args[0] for call in opener.open.call_args_list]
        self.assertEqual(first.get_header('Authorization'), 'Bearer secret')
        self.assertIsNone(second.get_header('Authorization'))
        opener.open.side_effect = HTTPError(cloud.GRAPH, 302, 'redirect', {'Location': 'https://untrusted.example/file'}, io.BytesIO())
        with patch.object(cloud, 'build_opener', return_value=opener), self.assertRaises(ValueError):
            cloud.request(cloud.GRAPH, token='secret', binary=True)

    def test_scheduler_disabled_due_failure_and_restart(self):
        self.configure(interval=15)
        cloud.DUE[(str(p.DATA.resolve()), 'icloud')] = 0
        with patch.object(cloud, 'backup', side_effect=ValueError('offline')) as backup:
            cloud.tick()
            backup.assert_called_once_with('icloud')
            cloud.tick()
            backup.assert_called_once()
        self.configure(interval=0)
        with patch.object(cloud, 'backup') as backup:
            cloud.tick()
            backup.assert_not_called()
        stop = cloud.start()
        stop.set()
        stop.worker.join(1)
        self.assertFalse(stop.worker.is_alive())

    def test_malformed_config_and_invalid_requests_fail_without_changing_database(self):
        before = (p.DATA / 'pilot.sqlite3').read_bytes()
        for body in ({'provider': 'unknown'}, {'provider': 'icloud', 'interval': True}, {'provider': 'icloud', 'interval': -1}):
            with self.assertRaises(ValueError):
                self.call('configure', body)
        (p.DATA / 'cloud-backup.json').write_text('[]')
        with self.assertRaisesRegex(ValueError, '配置无法读取'):
            cloud.status()
        self.assertEqual(before, (p.DATA / 'pilot.sqlite3').read_bytes())

    def test_http_assets_routes_origin_and_scheduler_shutdown(self):
        with patch('auto_analysis.start'):
            http = server.create_server('127.0.0.1', 0)
        thread = threading.Thread(target=http.serve_forever, daemon=True)
        thread.start()
        base = f'http://127.0.0.1:{http.server_address[1]}'
        try:
            for path in ('/cloud-backup.js', '/cloud-backup.css', '/api/pilot/cloud/status'):
                with urlopen(base + path) as response:
                    self.assertEqual(response.status, 200)
            with self.assertRaises(HTTPError) as error:
                urlopen(Request(base + '/api/pilot/cloud/configure', data=b'{}', headers={
                    'Content-Type': 'application/json', 'Origin': 'https://untrusted.example'}))
            self.assertEqual(error.exception.code, 403)
            with self.assertRaises(HTTPError):
                urlopen(base + '/cloud_backup.py')
        finally:
            http.shutdown()
            http.server_close()
            thread.join(2)
        self.assertTrue(http.cloud_stop.is_set())
        self.assertFalse(http.cloud_stop.worker.is_alive())


if __name__ == '__main__':
    unittest.main()
