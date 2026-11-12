"""Regression checks for the shared small/medium CLI, without AWS calls."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import cloud_acceptance
from src import moodle_cloud as cli


class PresetIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.small = cli.load_config(cli.ROOT / "config/sydney.yaml")
        self.medium = cli.load_config(cli.ROOT / "config/medium.example.yaml")

    def test_default_cli_still_selects_sydney_small(self):
        with patch.object(cli, "outputs", return_value={}) as outputs:
            self.assertEqual(cli.main(["status"]), 0)
        self.assertEqual(outputs.call_args.args[0], self.small)

    def test_small_preflight_requires_an_explicit_account_before_aws(self):
        with patch.object(cli, "aws") as aws:
            self.assertEqual(cli.main(["preflight"]), 2)
        aws.assert_not_called()

    def test_medium_preflight_explicit_account_cannot_override_yaml(self):
        with patch.object(cli, "aws") as aws:
            with self.assertRaisesRegex(cli.ConfigError, "account_id"):
                cli.preflight(self.medium, "222222222222")
        aws.assert_not_called()

    def test_medium_backup_uses_runner_and_waits_for_the_same_command(self):
        with patch.object(cli, "outputs", return_value={"runner_id": {"value": "i-runner"}}), \
                patch.object(cli, "aws", return_value={"Command": {"CommandId": "one-command"}}) as aws, \
                patch.object(cli, "wait_command") as wait:
            cli.backup(self.medium, wait=True, timeout=90)
        args = aws.call_args.args
        self.assertEqual(args[args.index("--instance-ids") + 1], "i-runner")
        self.assertEqual(json.loads(args[-1])["commands"], ["set -eu\n/opt/moodle-medium/operation.sh backup"])
        self.assertEqual(aws.call_count, 1)
        wait.assert_called_once_with(self.medium, "one-command", "i-runner", timeout=90)

    def test_medium_health_uses_the_deployed_https_url(self):
        with patch.object(cli, "outputs", return_value={"url": {"value": "https://moodle.example.com"}}), \
                patch.object(cli, "remote") as remote:
            cli.health(self.medium, wait=True)
        script = remote.call_args.args[1]
        self.assertIn("https://moodle.example.com/_ready.php", script)
        self.assertIn("moodle-cron.timer", script)
        self.assertNotIn("/opt/moodle-distribution", script)
        self.assertTrue(remote.call_args.kwargs["wait"])

    def test_medium_health_rejects_missing_or_non_https_outputs(self):
        for outputs in ({}, {"url": {"value": "http://example.com"}}):
            with self.subTest(outputs=outputs), patch.object(cli, "outputs", return_value=outputs), \
                    patch.object(cli, "remote") as remote:
                with self.assertRaises(cli.ConfigError):
                    cli.health(self.medium)
                remote.assert_not_called()

    def test_medium_restore_only_uses_its_allowed_source_on_staging(self):
        target = copy.deepcopy(self.medium)
        target.update(environment="staging", restore_source_prefix="moodle-source-dev-med")
        uri = f"s3://{target['backup_bucket']}/{target['restore_source_prefix']}/20261109T154309"
        confirmation = f"{target['project']}-staging"
        with patch.object(cli, "remote") as remote:
            cli.restore(target, uri, confirmation, True, True)
            self.assertEqual(remote.call_args.args[1], "/opt/moodle-medium/operation.sh restore --prefix " + uri)
            self.assertTrue(remote.call_args.kwargs["wait"])
            remote.reset_mock()
            for invalid in (uri + ";id", uri + "/..", uri.replace("moodle-source-dev-med", "another-site"),
                            uri.replace(target['backup_bucket'], "another-bucket")):
                with self.subTest(uri=invalid), self.assertRaises(cli.ConfigError):
                    cli.restore(target, invalid, confirmation, True)
            with self.assertRaises(cli.ConfigError):
                cli.restore(self.medium, uri, f"{self.medium['project']}-dev", True)
            remote.assert_not_called()

    def test_small_acceptance_rejects_medium_before_any_aws_call(self):
        with patch.object(cli, "aws") as aws:
            self.assertEqual(cloud_acceptance.main([
                "--config", str(cli.ROOT / "config/medium.example.yaml"),
                "--expected-account", self.medium["account_id"],
                "--confirm", f"{self.medium['project']}-{self.medium['environment']}",
            ]), 2)
            with self.assertRaises(cli.ConfigError):
                cloud_acceptance.command_script(self.medium, seed=True)
        aws.assert_not_called()

    def test_medium_plan_records_data_loss_review_before_apply(self):
        changes = {"resource_changes": [{"mode": "managed", "type": "aws_efs_file_system",
                   "address": "aws_efs_file_system.medium", "change": {"actions": ["delete", "create"]}}]}
        with tempfile.TemporaryDirectory() as directory, patch.object(cli, "ROOT", Path(directory)), \
                patch.object(cli, "preflight", return_value={"Account": self.medium["account_id"]}), \
                patch.object(cli, "init"):
            def terraform(config, *args, **kwargs):
                if args[0] == "plan":
                    (cli.workspace(config) / "apply.tfplan").write_bytes(b"medium-plan")
                elif args[0] == "show":
                    return json.dumps(changes)
            with patch.object(cli, "tf", side_effect=terraform):
                cli.plan(self.medium)
            manifest = json.loads((cli.workspace(self.medium) / "apply.json").read_text())
            self.assertTrue(manifest["review"]["data_loss_risk"])
            with patch.object(cli, "aws") as aws, patch.object(cli, "tf") as tf:
                with self.assertRaisesRegex(cli.ConfigError, "allow-data-loss"):
                    cli.apply(self.medium, f"{self.medium['project']}-{self.medium['environment']}")
                aws.assert_not_called()
                tf.assert_not_called()


if __name__ == "__main__":
    unittest.main()
