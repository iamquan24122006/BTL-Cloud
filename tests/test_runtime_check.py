import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.check_runtime import EXTENSIONS, RuntimeCheck, RuntimeCheckError, validate_metadata


def metadata():
    return {"php": "8.3.0", "max_input_vars": 5000,
            "extensions": {name: True for name in EXTENSIONS}}


class RuntimeCheckTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.check = RuntimeCheck(Path(temporary.name) / "run")

    def fake_docker(self, name, args, **kwargs):
        if name == "engine":
            return "linux/x86_64"
        if name == "image":
            return "sha256:" + "a" * 64
        if name == "php-cli":
            return json.dumps(metadata())
        if name == "web-probe":
            return json.dumps({"web": metadata(), "blocked": {"/config.php": 403, "/.git/config": 403},
                               "code_readonly": True})
        return ""

    def test_engine_failure_cannot_report_success_or_start_build(self):
        with patch.object(self.check, "command", side_effect=RuntimeCheckError("engine unavailable")) as command:
            self.assertEqual(self.check.execute("example:local"), 1)
        self.assertEqual(command.call_count, 1)
        report = json.loads((self.check.directory / "report.json").read_text())
        self.assertEqual(report["status"], "failed")
        self.assertNotIn("image_id", report)

    def test_web_cli_drift_fails_and_removes_only_owned_container(self):
        def fake(name, args, **kwargs):
            if name == "web-probe":
                web = metadata()
                web["max_input_vars"] = 6000
                return json.dumps({"web": web})
            return self.fake_docker(name, args, **kwargs)

        with patch.object(self.check, "command", side_effect=fake) as command:
            self.assertEqual(self.check.execute("example:local", skip_build=True), 1)
        self.assertIn("differ", self.check.report["error"])
        command.assert_any_call("cleanup", ["rm", "--force", self.check.container], timeout=30, required=True)
        self.assertFalse(any(call.args[0] == "build" for call in command.call_args_list))

    def test_failed_cleanup_prevents_success_report(self):
        def fake(name, args, **kwargs):
            if name == "cleanup":
                raise RuntimeCheckError("container still exists")
            return self.fake_docker(name, args, **kwargs)

        with patch.object(self.check, "command", side_effect=fake):
            self.assertEqual(self.check.execute("example:local", skip_build=True), 1)
        self.assertEqual(self.check.report["status"], "failed")
        self.assertTrue(self.check.report["cleanup_errors"])

    def test_wrong_php_and_missing_extensions_are_rejected(self):
        wrong_php = metadata()
        wrong_php["php"] = "8.5.0"
        missing_extension = metadata()
        missing_extension["extensions"]["pdo_pgsql"] = False
        low_limit = metadata()
        low_limit["max_input_vars"] = 1000
        for value in (wrong_php, missing_extension, low_limit):
            with self.subTest(value=value), self.assertRaises(RuntimeCheckError):
                validate_metadata(value)


if __name__ == "__main__":
    unittest.main()
