"""Medium CLI guards tested offline; these do not certify AWS/Moodle acceptance."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import yaml

from scripts.medium_bundle import build_bundle
from src import moodle_cloud as cli


class MediumTests(unittest.TestCase):
    def setUp(self):
        self.config = cli.load_config(cli.ROOT / 'config/medium.example.yaml')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'input.yaml'

    def load(self, config):
        self.path.write_text(yaml.safe_dump(config), encoding='utf-8')
        return cli.load_config(self.path)

    def test_medium_schema_and_offline_render(self):
        with patch.object(cli, 'run') as run, patch.object(cli, 'ROOT', self.root):
            config = self.load(self.config)
            values = json.loads(cli.render(config).read_text())
            self.assertNotIn('backend', values)
            self.assertEqual(values['size'], 'medium')
            run.assert_not_called()

    def test_negative_medium_inputs(self):
        cases = [
            ('account_id', 111111111111), ('domain', 'moodle.example.com/path'),
            ('wwwroot', 'http://moodle.example.com'), ('ami_id', 'latest'),
            ('certificate_arn', self.config['certificate_arn'].replace('ap-southeast-1', 'us-east-1')),
            ('availability_zones', ['ap-southeast-1a'] * 2),
            ('availability_zones', ['us-east-1a', 'us-east-1b']),
            ('availability_zones', {}), ('vpc_cidr', '0.0.0.0/16'),
            ('vpc_cidr', '10.43.0.1/16'), ('db_allocated_storage', True),
            ('backup_bucket', ''), ('backup_bucket', self.config['backend']['bucket']),
            ('db_instance_type', 'db.r8g.48xlarge'), ('redis_node_type', 'latest'),
            ('hosted_zone_id', 'Z123;whoami'), ('backend', {'bucket': 'good-bucket', 'region': 'us-east-1'}),
        ]
        for key, value in cases:
            with self.subTest(key=key, value=value), self.assertRaises(cli.ConfigError):
                self.load(dict(self.config, **{key: value}))

    def test_rds_backup_retention_preserves_default_and_supports_restricted_accounts(self):
        legacy = dict(self.config)
        legacy.pop('db_backup_retention_days', None)
        self.assertEqual(self.load(legacy)['db_backup_retention_days'], 7)
        for days in (1, 35):
            config = self.load(dict(legacy, db_backup_retention_days=days))
            with patch.object(cli, 'ROOT', self.root):
                self.assertEqual(json.loads(cli.render(config).read_text())['db_backup_retention_days'], days)
        for value in (0, 36, True, 1.5, '1'):
            with self.subTest(value=value), self.assertRaises(cli.ConfigError):
                self.load(dict(legacy, db_backup_retention_days=value))

    def test_nested_unknown_keys_and_secret_values_rejected(self):
        for section in ('artifact', 'backend', 'secrets'):
            data = copy.deepcopy(self.config)
            data[section]['password'] = 'do-not-accept'
            with self.subTest(section=section), self.assertRaises(cli.ConfigError):
                self.load(data)

    def test_scaling_target_is_bounded_and_backwards_compatible(self):
        legacy = dict(self.config)
        legacy.pop('app_requests_per_target', None)
        self.assertEqual(self.load(legacy)['app_requests_per_target'], 600)
        for value in (60, 6000):
            self.assertEqual(self.load(dict(legacy, app_requests_per_target=value))['app_requests_per_target'], value)
        for value in (0, 59, 6001, True, 120.5, '600'):
            with self.subTest(value=value), self.assertRaises(cli.ConfigError):
                self.load(dict(legacy, app_requests_per_target=value))
        for field, value in [('image', 'repo:latest'), ('release', 'main'), ('sha256', 'bad'), ('key', '../escape')]:
            data = copy.deepcopy(self.config)
            data['artifact'][field] = value
            with self.subTest(field=field), self.assertRaises(cli.ConfigError):
                self.load(data)

    def test_duplicate_nested_yaml_key(self):
        self.path.write_text('artifact:\n  image: first\n  image: second\n')
        with self.assertRaises(cli.ConfigError):
            cli.load_config(self.path)

    def test_cloudfront_is_explicit_temporary_mode(self):
        temporary = dict(self.config, frontend='cloudfront', domain='', certificate_arn='', hosted_zone_id='', wwwroot='auto')
        self.assertEqual(self.load(temporary)['frontend'], 'cloudfront')
        with self.assertRaises(cli.ConfigError):
            self.load(dict(temporary, wwwroot='http://example.com'))
        with self.assertRaises(cli.ConfigError):
            self.load(dict(self.config, frontend='other'))

    def test_state_isolated_by_preset_account_and_environment(self):
        small = dict(self.config, size='small')
        self.assertNotEqual(cli.workspace(self.config), cli.workspace(small))
        self.assertNotEqual(cli.workspace(self.config), cli.workspace(dict(self.config, account_id='222222222222')))
        self.assertNotEqual(cli.workspace(self.config), cli.workspace(dict(self.config, environment='staging')))

    def test_s3_backend_has_lock_and_account_isolation(self):
        with patch.object(cli, 'ROOT', self.root), patch.object(cli, 'tf') as tf:
            cli.init(self.config)
        args = tf.call_args.args
        self.assertIn('-backend-config=use_lockfile=true', args)
        self.assertIn('-backend-config=encrypt=true', args)
        self.assertIn('-backend-config=key=111111111111/moodle-lab/dev/medium/terraform.tfstate', args)
        self.assertFalse(any('path=' in str(arg) for arg in args))

    def test_fingerprint_includes_nested_runtime_and_userdata_template(self):
        with patch.object(cli, 'ROOT', self.root):
            (self.root / 'infra/medium').mkdir(parents=True)
            (self.root / 'scripts/medium').mkdir(parents=True)
            original = cli.fingerprint(self.config)
            (self.root / 'scripts/medium/bootstrap.sh').write_text('first')
            changed = cli.fingerprint(self.config)
            self.assertNotEqual(original, changed)
            (self.root / 'infra/medium/user-data.sh.tftpl').write_text('second')
            self.assertNotEqual(changed, cli.fingerprint(self.config))

    def test_backend_change_requires_explicit_migration(self):
        with patch.object(cli, 'ROOT', self.root), patch.object(cli, 'tf') as tf:
            cli.init(self.config)
            changed = copy.deepcopy(self.config)
            changed['backend']['bucket'] = 'new-state-bucket'
            with self.assertRaisesRegex(cli.ConfigError, 'Backend changed'):
                cli.init(changed)
            self.assertEqual(tf.call_count, 1)

    def test_preflight_wrong_account_stops_before_other_aws_calls(self):
        with patch.object(cli.shutil, 'which', return_value='tool'), patch.object(cli, 'aws', return_value={'Account': '222222222222'}) as aws:
            with self.assertRaisesRegex(cli.ConfigError, 'account_id'):
                cli.preflight(self.config)
            self.assertEqual(aws.call_count, 1)

    def test_missing_tools_prevent_aws_calls(self):
        with patch.object(cli.shutil, 'which', return_value=None), patch.object(cli, 'aws') as aws:
            with self.assertRaisesRegex(cli.ConfigError, 'Missing tools'):
                cli.preflight(self.config)
            aws.assert_not_called()

    def test_failed_replan_invalidates_previous_manifest(self):
        with patch.object(cli, 'ROOT', self.root), patch.object(cli, 'preflight', return_value={'Account': self.config['account_id'], 'Arn': 'arn'}), patch.object(cli, 'init'), patch.object(cli, 'tf', side_effect=RuntimeError('plan failed')):
            cli.render(self.config)
            manifest = cli.workspace(self.config) / 'apply.json'
            manifest.write_text('{}')
            with self.assertRaises(RuntimeError):
                cli.plan(self.config)
            self.assertFalse(manifest.exists())

    def test_bundle_is_deterministic(self):
        first, second = self.root / 'first.tar.gz', self.root / 'second.tar.gz'
        self.assertEqual(build_bundle(first), build_bundle(second))
        self.assertEqual(first.read_bytes(), second.read_bytes())
        self.assertEqual(build_bundle(first), hashlib.sha256(first.read_bytes()).hexdigest())


if __name__ == '__main__':
    unittest.main()
