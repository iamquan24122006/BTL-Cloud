import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src import moodle_cloud as cli


class OperationTests(unittest.TestCase):
    def setUp(self):
        self.config = cli.load_config(cli.ROOT / "config/sydney.yaml")

    def test_successful_empty_aws_response_does_not_fail_or_repeat_mutation(self):
        with patch.object(cli, "run", return_value="") as runner:
            self.assertEqual(cli.aws(self.config, "ec2", "reboot-instances", "--instance-ids", "i-fixture"), {})
        runner.assert_called_once()

    def test_nonempty_invalid_aws_json_is_still_rejected(self):
        with patch.object(cli, "run", return_value="invalid response") as runner:
            with self.assertRaises(json.JSONDecodeError):
                cli.aws(self.config, "ec2", "describe-instances")
        runner.assert_called_once()

    def test_ssm_eventual_consistency_and_pending_status_are_retried(self):
        with patch.object(cli, "aws", side_effect=[cli.AwsError("InvocationDoesNotExist", "not ready"),
                {"Status": "InProgress"}, {"Status": "Success", "ResponseCode": 0}]) as api, \
                patch.object(cli.time, "sleep"):
            result = cli.wait_command(self.config, "command", "instance")
        self.assertEqual(api.call_count, 3)
        self.assertEqual(result["ResponseCode"], 0)

    def test_ssm_permission_errors_are_not_retried(self):
        with patch.object(cli, "aws", side_effect=cli.AwsError("AccessDeniedException", "denied")) as api:
            with self.assertRaises(cli.AwsError):
                cli.wait_command(self.config, "command", "instance")
        self.assertEqual(api.call_count, 1)

    def test_ssm_terminal_failures_and_false_success_are_rejected(self):
        for response in ({"Status": "Failed"}, {"Status": "TimedOut"},
                         {"Status": "Cancelled"}, {"Status": "Success", "ResponseCode": -1}):
            with self.subTest(response=response), patch.object(cli, "aws", return_value=response):
                with self.assertRaises(cli.ConfigError):
                    cli.wait_command(self.config, "command", "instance")

    def test_ssm_timeout_does_not_submit_a_second_operation(self):
        with patch.object(cli, "aws", return_value={"Status": "InProgress"}) as api, \
                patch.object(cli.time, "monotonic", side_effect=[0, 2]):
            with self.assertRaisesRegex(cli.ConfigError, "may still be running"):
                cli.wait_command(self.config, "command", "instance", timeout=1)
        self.assertEqual(api.call_count, 1)

    def test_backup_waits_for_result_and_checks_health_in_same_shell(self):
        with patch.object(cli, "outputs", return_value={"instance_id": {"value": "i-fixture"}}), \
                patch.object(cli, "aws", return_value={"Command": {"CommandId": "fixture"}}) as api, \
                patch.object(cli, "wait_command") as wait:
            cli.backup(self.config, wait=True)
        parameters = json.loads(api.call_args.args[-1])
        self.assertTrue(parameters["commands"][0].startswith("set -eu\n"))
        self.assertIn("health.sh", parameters["commands"][0])
        wait.assert_called_once()

    def test_preflight_rejects_wrong_account_before_mutation(self):
        with patch.object(cli.shutil, "which", return_value="tool"), \
                patch.object(cli, "aws", return_value={"Account": "111111111111"}) as api:
            with self.assertRaisesRegex(cli.ConfigError, "does not match"):
                cli.preflight(self.config, "222222222222")
        self.assertEqual(api.call_args.args[1:], ("sts", "get-caller-identity"))

    def test_plan_review_detects_root_volume_data_loss_and_ignores_data_reads(self):
        result = cli.summarize_plan({"resource_changes": [
            {"mode": "managed", "type": "aws_instance", "address": "aws_instance.moodle",
             "change": {"actions": ["delete", "create"]}},
            {"mode": "data", "type": "aws_ami", "address": "data.aws_ami.ubuntu",
             "change": {"actions": ["read"]}},
        ]})
        self.assertEqual([result[k] for k in ("create", "update", "delete", "replace")], [1, 0, 1, 1])
        self.assertTrue(result["data_loss_risk"])

    def test_failed_plan_authentication_invalidates_old_approval(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(cli, "ROOT", Path(directory)), \
                patch.object(cli, "aws", side_effect=cli.AwsError("ExpiredToken", "expired")):
            cli.render(self.config)
            manifest = cli.workspace(self.config) / "apply.json"
            manifest.write_text("old approval")
            with self.assertRaises(cli.AwsError):
                cli.plan(self.config)
            self.assertFalse(manifest.exists())

    def test_restore_rejects_dev_and_unconfirmed_data_loss_before_aws(self):
        with patch.object(cli, "remote") as remote:
            with self.assertRaises(cli.ConfigError):
                cli.restore(self.config, "s3://example/set", "moodle-sydney-dev", True)
            stage = dict(self.config, environment="staging")
            with self.assertRaises(cli.ConfigError):
                cli.restore(stage, "s3://example/set", "moodle-sydney-staging")
        remote.assert_not_called()

    def test_restore_downloads_exact_set_without_interpolating_arbitrary_paths(self):
        stage = dict(self.config, environment="staging")
        uri = f"s3://{stage['backup_bucket']}/moodle-sydney-dev/20261105T000000Z"
        with patch.object(cli, "remote") as remote:
            cli.restore(stage, uri, "moodle-sydney-staging", True, True)
            self.assertIn("manifest.json", remote.call_args.args[1])
            self.assertTrue(remote.call_args.kwargs["wait"])
            remote.reset_mock()
            for invalid in (uri + ";id", uri + "/..", "s3://another-bucket/moodle-sydney-dev/20261105T000000Z"):
                with self.assertRaises(cli.ConfigError):
                    cli.restore(stage, invalid, "moodle-sydney-staging", True)
            remote.assert_not_called()


if __name__ == "__main__":
    unittest.main()
