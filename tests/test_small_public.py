import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import small_public as public
from src import moodle_cloud as cli


class SmallPublicTests(unittest.TestCase):
    def setUp(self):
        self.config=cli.load_config(cli.ROOT/'config/sydney.yaml')
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work=Path(self.temp.name)

    def test_medium_and_wrong_account_stop_before_instance_lookup(self):
        medium={**self.config,'size':'medium'}
        with patch.object(cli,'aws') as aws:
            with self.assertRaises(cli.ConfigError): public.context(medium,'111111111111')
            aws.assert_not_called()
        with patch.object(cli,'aws',return_value={'Account':'111111111111'}),patch.object(cli,'instance_id') as instance:
            with self.assertRaises(cli.ConfigError):public.context(self.config,'222222222222')
            instance.assert_not_called()

    def test_wrong_confirmation_never_applies_or_activates(self):
        with patch.object(public,'context',return_value=('test-dev',self.work,'i-test',{})),patch.object(public,'tf') as tf,patch.object(public,'activate') as activate:
            with self.assertRaises(cli.ConfigError):public.apply(self.config,'111111111111','wrong')
            tf.assert_not_called();activate.assert_not_called()

    def test_wrong_disable_confirmation_never_sends_a_remote_command(self):
        with patch.object(public,'context',return_value=('test-dev',self.work,'i-test',{})),patch.object(cli,'remote') as remote:
            with self.assertRaises(cli.ConfigError):public.disable(self.config,'111111111111','wrong')
            remote.assert_not_called()

    def test_render_preserves_public_origin_group_without_changing_bootstrap_url(self):
        runtime={'url':'https://dexample.cloudfront.net','origin_security_group_id':'sg-0123456789abcdef0'}
        (self.work/'public-runtime.json').write_text(json.dumps(runtime))
        with patch.object(cli,'workspace',return_value=self.work):
            rendered=json.loads(cli.render(self.config).read_text())
        self.assertEqual(rendered['additional_security_group_ids'],['sg-0123456789abcdef0'])
        self.assertEqual(rendered['public_url'],runtime['url'])
        self.assertEqual(rendered['wwwroot'],'http://localhost:8080')

    def test_plan_tampering_rejected_before_mutation(self):
        (self.work/'apply.tfplan').write_bytes(b'changed')
        manifest={'account':'111111111111','instance':'i-test','fingerprint':public.source_hash(self.config),
                  'plan_sha256':hashlib.sha256(b'original').hexdigest()}
        (self.work/'manifest.json').write_text(json.dumps(manifest))
        with patch.object(public,'context',return_value=('test-dev',self.work,'i-test',{})),patch.object(public,'tf') as tf:
            with self.assertRaises(cli.ConfigError):public.apply(self.config,'111111111111','test-dev')
            tf.assert_not_called()
        self.assertTrue((self.work/'manifest.json').exists())

    def test_apply_consumes_manifest_and_uses_verified_plan_snapshot(self):
        payload=b'reviewed-plan'
        (self.work/'apply.tfplan').write_bytes(payload)
        manifest={'account':'111111111111','instance':'i-test','fingerprint':public.source_hash(self.config),
                  'plan_sha256':hashlib.sha256(payload).hexdigest()}
        (self.work/'manifest.json').write_text(json.dumps(manifest))
        with patch.object(public,'context',return_value=('test-dev',self.work,'i-test',{})),patch.object(public,'tf') as tf,patch.object(public,'activate'):
            public.apply(self.config,'111111111111','test-dev')
        self.assertFalse((self.work/'manifest.json').exists())
        saved=tf.call_args.args[-1]
        self.assertNotEqual(saved,self.work/'apply.tfplan')
        self.assertEqual(saved.read_bytes(),payload)
