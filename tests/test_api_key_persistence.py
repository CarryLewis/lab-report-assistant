import json
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pilot_backend as p


class APIKeyPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.patches = [
            patch.object(p, 'DATA', Path(self.temp.name)),
            patch.object(p, 'ENV_KEY', ''),
            patch.object(p, 'KEY', ''),
            patch.object(p, 'KEY_SOURCE', None),
        ]
        for item in self.patches:
            item.start()
        p.init()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def call(self, path, body=None):
        method = 'GET' if body is None else 'POST'
        return p.dispatch(method, '/api/pilot/' + path, body or {}, None)

    def test_saved_key_survives_restart_without_being_exposed(self):
        secret = 'sk-test-persistent-secret'
        result = self.call('settings', {'model': 'deepseek-flash', 'api_key': secret})
        self.assertTrue(result['has_key'])
        self.assertEqual(result['key_source'], 'saved')
        key_file = Path(self.temp.name) / 'deepseek_api_key'
        self.assertEqual(key_file.read_text(), secret)
        self.assertEqual(stat.S_IMODE(key_file.stat().st_mode), 0o600)
        bootstrap = self.call('bootstrap')
        self.assertNotIn(secret, json.dumps(bootstrap))
        self.assertEqual(bootstrap['settings']['key_source'], 'saved')

        p.KEY, p.KEY_SOURCE = '', None
        p.init()
        self.assertEqual(p.KEY, secret)
        self.assertEqual(p.KEY_SOURCE, 'saved')

    def test_delete_removes_saved_key(self):
        self.call('settings', {'model': 'deepseek-flash', 'api_key': 'sk-delete-me'})
        result = self.call('settings', {'model': 'deepseek-flash', 'clear_key': True})
        self.assertFalse(result['has_key'])
        self.assertIsNone(result['key_source'])
        self.assertFalse((Path(self.temp.name) / 'deepseek_api_key').exists())


if __name__ == '__main__':
    unittest.main()
