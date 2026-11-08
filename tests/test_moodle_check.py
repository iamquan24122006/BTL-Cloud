from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts import check_moodle


class MoodleCheckGuardsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = patch.object(check_moodle, "ROOT", Path(temporary.name))
        root.start()
        self.addCleanup(root.stop)
        self.check = check_moodle.MoodleCheck("example:local")

    def test_non_linux_engine_does_not_create_resources(self):
        with patch.object(self.check, "command", return_value="windows/x86_64") as command:
            self.assertEqual(self.check.execute(), 1)
        self.assertEqual(command.call_count, 1)
        self.assertEqual(self.check.containers, [])
        self.assertEqual(self.check.volumes, [])
        self.assertEqual(self.check.report["status"], "failed")

    def test_cleanup_refuses_a_container_with_a_different_owner(self):
        self.check.containers.append(self.check.prefix + "-web")
        with patch.object(self.check, "command", return_value="another-run") as command:
            self.check.cleanup()
        self.assertEqual(command.call_count, 1)
        self.assertNotIn("rm", command.call_args.args[1])
        self.assertEqual(self.check.report["status"], "failed")
        self.assertTrue(self.check.report["cleanup_errors"])

    def test_private_output_is_redacted_and_input_is_not_in_arguments(self):
        secret = self.check.passwords["adminpass"]
        result = subprocess.CompletedProcess([], 1, "error: " + secret, "stderr: " + secret)
        with patch.object(check_moodle.subprocess, "run", return_value=result) as command:
            with self.assertRaises(check_moodle.CheckError):
                self.check.command("private", ["exec", "fixture", "php"], payload=secret)
        output = (self.check.directory / "private.log").read_text(encoding="utf-8")
        self.assertNotIn(secret, output)
        self.assertIn("[REDACTED]", output)
        self.assertNotIn(secret, command.call_args.args[0])
        self.assertEqual(command.call_args.kwargs["input"], secret)

    def test_task_failure_is_rejected_even_when_cron_exits_zero(self):
        with patch.object(self.check, "php", return_value="Scheduled task failed: sample error"):
            with self.assertRaises(check_moodle.CheckError):
                self.check.cron({}, "cron")

    def test_timeout_keeps_partial_evidence_without_exposing_passwords(self):
        secret = self.check.passwords["adminpass"]
        failure = subprocess.TimeoutExpired(["docker"], 1, output=("partial " + secret).encode())
        with patch.object(check_moodle.subprocess, "run", side_effect=failure):
            with self.assertRaises(check_moodle.CheckError):
                self.check.command("timeout", ["exec", "fixture"], timeout=1)
        output = (self.check.directory / "timeout.log").read_text(encoding="utf-8")
        self.assertIn("partial", output)
        self.assertNotIn(secret, output)

    def test_cleanup_report_outside_private_workspace_is_rejected(self):
        with self.assertRaisesRegex(check_moodle.CheckError, "inside .work/moodle-check"):
            self.check.cleanup_report(self.check.directory.parents[2] / "outside.json")


if __name__ == "__main__":
    unittest.main()
