import copy
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import yaml

from src import moodle_cloud as cli


class ConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.config = cli.load_config(cli.ROOT / "config/dev.yaml")
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "config.yaml"

    def load(self, value):
        self.path.write_text(yaml.safe_dump(value), encoding="utf-8")
        return cli.load_config(self.path)

    def test_default_config(self):
        self.assertEqual(self.load(self.config)["size"], "small")

    def test_required_key(self):
        del self.config["region"]
        with self.assertRaises(cli.ConfigError):
            self.load(self.config)

    def test_invalid_inputs_are_rejected(self):
        cases = [("project", "../outside"), ("project", "test;whoami"),
                 ("environment", "prod"), ("size", "medium"), ("size", "large"),
                 ("instance_type", "t4g.small"), ("region", "us-east-1;cmd"),
                 ("volume_gib", True), ("volume_gib", 19), ("volume_gib", 201),
                 ("volume_gib", 30.5), ("moodle_version", "latest"),
                 ("wwwroot", "http://public.example.com"), ("backup_bucket", "bad/name"),
                 ("backup_bucket", "127.0.0.1"), ("tags", {"aws:reserved": "x"}),
                 ("tags", {"Owner": 3})]
        for key, value in cases:
            with self.subTest(key=key, value=value):
                data = copy.deepcopy(self.config)
                data[key] = value
                with self.assertRaises(cli.ConfigError):
                    self.load(data)

    def test_secrets_and_unknown_keys_rejected(self):
        self.config["db_password"] = "not-a-real-secret"
        with self.assertRaises(cli.ConfigError):
            self.load(self.config)

    def test_duplicate_yaml_keys_rejected(self):
        self.path.write_text("project: first\nproject: second\n", encoding="utf-8")
        with self.assertRaises(cli.ConfigError):
            cli.load_config(self.path)

    def test_non_mapping_yaml_rejected(self):
        for value in ([], "hello", None, 12):
            with self.subTest(value=value), self.assertRaises(cli.ConfigError):
                self.load(value)

    def test_unsafe_yaml_tag_rejected(self):
        self.path.write_text("!!python/object/apply:os.system ['echo unsafe']", encoding="utf-8")
        with self.assertRaises(cli.ConfigError):
            cli.load_config(self.path)


class PlanGuardsTests(unittest.TestCase):
    def setUp(self):
        self.config = cli.load_config(cli.ROOT / "config/dev.yaml")
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "infra/small").mkdir(parents=True)
        (self.root / "scripts").mkdir()
        (self.root / "infra/small/main.tf").write_text("# test fixture", encoding="utf-8")
        self.root_patch = patch.object(cli, "ROOT", self.root)
        self.infra_patch = patch.object(cli, "INFRA", self.root / "infra/small")
        self.root_patch.start()
        self.infra_patch.start()
        self.addCleanup(self.root_patch.stop)
        self.addCleanup(self.infra_patch.stop)
        self.confirm = "moodle-lab-dev"

    def prepare(self, mode="apply"):
        cli.render(self.config)
        work = cli.workspace(self.config)
        payload = b"test-saved-plan"
        (work / f"{mode}.tfplan").write_bytes(payload)
        (work / f"{mode}.json").write_text(json.dumps({
            "fingerprint": cli.fingerprint(self.config), "account": "111111111111", "mode": mode,
            "plan_sha256": hashlib.sha256(payload).hexdigest()
        }), encoding="utf-8")

    def test_environment_state_isolation(self):
        other = dict(self.config, environment="staging")
        self.assertNotEqual(cli.workspace(other), cli.workspace(self.config))

    def test_render_offline(self):
        with patch.object(cli, "run") as command:
            file = cli.render(self.config)
            self.assertEqual(json.loads(file.read_text()), self.config)
            command.assert_not_called()

    def test_apply_needs_confirmation(self):
        with patch.object(cli, "aws") as api, self.assertRaises(cli.ConfigError):
            cli.apply(self.config, "wrong")
        api.assert_not_called()

    def test_apply_needs_saved_plan(self):
        with self.assertRaises(cli.ConfigError):
            cli.apply(self.config, self.confirm)

    def test_apply_rejects_changed_config(self):
        self.prepare()
        self.config["volume_gib"] = 40
        with self.assertRaisesRegex(cli.ConfigError, "changed"):
            cli.apply(self.config, self.confirm)

    def test_apply_rejects_changed_source(self):
        self.prepare()
        (self.root / "scripts/bootstrap.sh").write_text("changed", encoding="utf-8")
        with self.assertRaisesRegex(cli.ConfigError, "changed"):
            cli.apply(self.config, self.confirm)

    def test_apply_rejects_changed_plan(self):
        self.prepare()
        (cli.workspace(self.config) / "apply.tfplan").write_bytes(b"tampered")
        with self.assertRaisesRegex(cli.ConfigError, "changed"):
            cli.apply(self.config, self.confirm)

    def test_apply_rejects_changed_account(self):
        self.prepare()
        with patch.object(cli, "aws", return_value={"Account": "222222222222"}), patch.object(cli, "tf") as tf:
            with self.assertRaisesRegex(cli.ConfigError, "account changed"):
                cli.apply(self.config, self.confirm)
            tf.assert_not_called()

    def test_successful_apply_consumes_manifest(self):
        self.prepare()
        with patch.object(cli, "aws", return_value={"Account": "111111111111"}), patch.object(cli, "tf") as tf:
            cli.apply(self.config, self.confirm)
            self.assertEqual(tf.call_args.args[1], "apply")
        self.assertFalse((cli.workspace(self.config) / "apply.json").exists())

    def test_failed_apply_also_consumes_manifest(self):
        self.prepare()
        with patch.object(cli, "aws", return_value={"Account": "111111111111"}), patch.object(cli, "tf", side_effect=subprocess.CalledProcessError(1, ["terraform"])):
            with self.assertRaises(subprocess.CalledProcessError):
                cli.apply(self.config, self.confirm)
        self.assertFalse((cli.workspace(self.config) / "apply.json").exists())

    def test_apply_uses_verified_bytes_if_original_plan_is_replaced(self):
        self.prepare()
        original = cli.workspace(self.config) / 'apply.tfplan'
        expected = original.read_bytes()

        def terraform(config, *args):
            original.write_bytes(b'a-concurrent-replan')
            self.assertEqual(args[-1].read_bytes(), expected)

        with patch.object(cli, 'aws', return_value={'Account': '111111111111'}), patch.object(cli, 'tf', side_effect=terraform):
            cli.apply(self.config, self.confirm)

    def test_destroy_requires_data_loss_acknowledgement(self):
        self.prepare("destroy")
        with patch.object(cli, "aws") as api, self.assertRaisesRegex(cli.ConfigError, "allow-data-loss"):
            cli.apply(self.config, self.confirm, destroy=True)
        api.assert_not_called()

    def test_destroy_uses_destroy_plan(self):
        self.prepare("destroy")
        with patch.object(cli, "aws", return_value={"Account": "111111111111"}), patch.object(cli, "tf") as tf:
            cli.apply(self.config, self.confirm, destroy=True, allow_data_loss=True)
            self.assertEqual(tf.call_args.args[-1].name, "destroy.tfplan")


if __name__ == "__main__":
    unittest.main()
