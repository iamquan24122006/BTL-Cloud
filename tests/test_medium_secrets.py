"""Secret refresh must preserve the intended reader permissions under a strict umask."""
import json
import os
from pathlib import Path
import runpy
import stat
import tempfile
import unittest
from unittest.mock import patch


@unittest.skipUnless(os.name == 'posix', 'Linux runtime file permissions')
class MediumSecretPermissions(unittest.TestCase):
    def refresh(self, role):
        actual_path = Path
        with tempfile.TemporaryDirectory() as directory:
            root = actual_path(directory)
            deploy = {'role': role, 'region': 'ap-southeast-1', 'master_secret_arn': 'test-master',
                      'secrets': {'runtime_arn': 'test-runtime', 'redis_arn': 'test-redis',
                                  'redis_version': 'test-version', 'migration_arn': 'test-migration', 'admin_arn': 'test-admin'}}
            (root / 'deploy.json').write_text(json.dumps(deploy), encoding='utf-8')
            values = {'test-runtime': {'username': 'moodle_runtime', 'password': 'TestPassword' * 3},
                      'test-migration': {'username': 'moodle_migration', 'password': 'TestPassword' * 3},
                      'test-master': {'username': 'master', 'password': 'TestPassword' * 3},
                      'test-admin': {'username': 'admin', 'password': 'TestPassword' * 3, 'email': 'admin@example.invalid'},
                      'test-redis': {'token': 'TestRedisToken' * 3}}

            def secret(arguments, **kwargs):
                name = arguments[arguments.index('--secret-id') + 1]
                return json.dumps({'SecretString': json.dumps(values[name])})

            mode = os.umask(0o077)
            try:
                with patch('pathlib.Path', lambda value: root if str(value) == '/etc/moodle' else actual_path(value)), \
                        patch('subprocess.check_output', side_effect=secret), patch('os.fchown'):
                    runpy.run_path(str(actual_path(__file__).resolve().parents[1] / 'scripts/medium/refresh-config.py'))
            finally:
                os.umask(mode)
            files = set(p.name for p in root.iterdir()) - {'deploy.json'}
            expected = {'runtime.json'} if role == 'app' else {'runtime.json', 'migration.json', 'master.json', 'admin.json'}
            self.assertEqual(files, expected)
            for name in expected:
                self.assertEqual(stat.S_IMODE((root / name).stat().st_mode), 0o640, name)
                self.assertIsInstance(json.loads((root / name).read_text()), dict)

    def test_app_runtime_remains_readable_to_php_without_operator_secrets(self):
        self.refresh('app')

    def test_runner_secret_refresh_survives_restrictive_operator_umask(self):
        self.refresh('runner')
