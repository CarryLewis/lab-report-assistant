import errno
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

import app_paths
import app_runtime as runtime
import document_preview
import pilot_backend as backend
import server


class DesktopRuntimeTests(unittest.TestCase):
    def test_installed_data_is_outside_program_and_source_data_is_unchanged(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            with patch.dict(os.environ, {'LABWISE_DATA_DIR':''}), patch.object(app_paths.Path,'home',return_value=home), patch.object(app_paths.sys,'platform','darwin'):
                with patch.object(app_paths.sys,'frozen',True,create=True):
                    for channel, name in [('stable','Labwise'),('beta','Labwise Beta')]:
                        with patch.object(app_paths,'release_channel',return_value=channel):
                            self.assertEqual(app_paths.data_directory(),home/'Library/Application Support'/name/'data')
                with patch.object(app_paths.sys,'frozen',False,create=True):
                    self.assertEqual(app_paths.data_directory(),app_paths.ROOT/'.labwise')
            with patch.dict(os.environ, {'LABWISE_DATA_DIR':str(home/'restored')}):
                self.assertEqual(app_paths.data_directory(),(home/'restored').resolve())

    def test_beta_metadata_and_default_workspace_are_explicit(self):
        self.assertEqual(app_paths.version(),'1.4.1')
        self.assertEqual(app_paths.release_channel(),'beta')
        self.assertEqual(app_paths.stable_version(),'1.3.7')
        status=runtime.preflight()
        self.assertEqual(status['release_channel'],'beta')
        self.assertEqual(status['stable_version'],'1.3.7')

    def test_older_program_resources_default_to_stable_channel(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(app_paths,'ROOT',Path(folder)):
            (Path(folder)/'VERSION').write_text('1.3.7')
            self.assertEqual(app_paths.release_channel(),'stable')
            self.assertEqual(app_paths.stable_version(),'1.3.7')

    def test_missing_component_is_optional_and_invalid_override_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ,{'LABWISE_SOFFICE':str(Path(folder)/'not-installed')}):
            self.assertIsNone(document_preview.converter_path())
            report = runtime.preflight()
            self.assertTrue(report['runtime_ok'])
            self.assertFalse(report['paged_word_export'])
            self.assertTrue(report['warnings'])

    def test_self_test_writes_report_without_opening_user_database(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)
            data=path/'not-created'
            report={'runtime_ok':True,'missing_resources':[]}
            with patch.object(runtime,'preflight',return_value=report):
                self.assertEqual(runtime.main(['--self-test','--data-dir',str(data),'--report',str(path/'report.json')]),0)
            self.assertFalse(data.exists())
            self.assertEqual(json.loads((path/'report.json').read_text()),report)

    def test_health_probe_requires_own_instance_and_never_uses_proxy(self):
        record={'port':8001,'instance_id':'expected'}
        opener=Mock()
        opener.open.return_value=io.BytesIO(json.dumps({'application':'Labwise','instance_id':'expected'}).encode())
        with patch.object(runtime,'build_opener',return_value=opener) as factory:
            self.assertTrue(runtime.probe_instance(record))
            self.assertEqual(factory.call_args.args[0].proxies,{})
        opener.open.return_value=io.BytesIO(json.dumps({'application':'Labwise','instance_id':'other'}).encode())
        with patch.object(runtime,'build_opener',return_value=opener):
            self.assertFalse(runtime.probe_instance(record))
        self.assertFalse(runtime.probe_instance({'port':'not-a-port'}))

    def test_port_conflict_falls_back_and_second_start_reuses_one_service(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(backend,'DATA',Path(folder)):
            stop=threading.Event()
            http=Mock(server_address=('127.0.0.1',8002),instance_id='one-instance')
            http.serve_forever.side_effect=stop.wait
            http.shutdown.side_effect=stop.set
            first=runtime.DesktopService(folder,8001)
            second=runtime.DesktopService(folder,8001)
            with patch.object(server,'create_server',side_effect=[OSError(errno.EADDRINUSE,'occupied'),http]) as create:
                try:
                    record=first.start()
                    self.assertEqual(record['port'],8002)
                    with patch.object(runtime,'probe_instance',return_value=True):
                        self.assertEqual(second.start(),record)
                    self.assertTrue(second.reused)
                    self.assertEqual(create.call_count,2)
                    second.stop()
                    self.assertTrue((Path(folder)/'app-instance.json').exists())
                finally:
                    first.stop()
            self.assertFalse((Path(folder)/'app-instance.json').exists())

    def test_non_port_failure_releases_lock_without_retrying(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(backend,'DATA',Path(folder)), patch.object(server,'create_server',side_effect=PermissionError(errno.EACCES,'denied')) as create:
            service=runtime.DesktopService(folder,8001)
            with self.assertRaises(PermissionError):
                service.start()
            self.assertIsNone(service.lock)
            self.assertEqual(create.call_count,1)

    def test_missing_tls_policy_resource_fails_preflight(self):
        with patch('ssl.create_default_context',side_effect=FileNotFoundError('certificate policy missing')):
            report=runtime.preflight()
        self.assertFalse(report['tls_ready'])
        self.assertFalse(report['runtime_ok'])

    def test_gui_preflight_closes_its_window_without_starting_service(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(runtime,'preflight',return_value={'runtime_ok':True,'missing_resources':[]}), patch('tkinter.Tk') as factory, patch.object(runtime.DesktopService,'start') as start:
            report=Path(folder)/'gui.json'
            self.assertEqual(runtime.main(['--self-test','--gui-self-test','--report',str(report)]),0)
            self.assertTrue(json.loads(report.read_text())['gui_ready'])
            factory.return_value.destroy.assert_called_once()
            start.assert_not_called()


if __name__ == '__main__':
    unittest.main()
