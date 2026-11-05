import unittest
import csv
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from scripts.load_test import FormParser, percentile, summarize
from scripts.summarize_jmeter import main as summarize_jmeter


class LoadReportTests(unittest.TestCase):
    def test_assertion_failures_are_counted_separately_from_latency(self):
        rows = [{"transaction": "course", "ok": True, "elapsed_ms": 20},
                {"transaction": "course", "ok": False, "elapsed_ms": 1000}]
        result = summarize(rows, 10)["transactions"]["course"]
        self.assertEqual(result["errors"], 1)
        self.assertEqual(result["error_percent"], 50)
        self.assertEqual(result["p95_ms_success"], 20)

    def test_nearest_rank_percentile_handles_small_and_empty_samples(self):
        self.assertIsNone(percentile([], .95))
        self.assertEqual(percentile([1, 2, 3], .95), 3)

    def test_tokens_and_html_escaped_logout_links_are_parsed(self):
        parser = FormParser()
        parser.feed('<input name="logintoken" value="fixture"><a href="/login/logout.php?a=1&amp;sesskey=token">Logout</a>')
        self.assertEqual(parser.token, "fixture")
        self.assertEqual(parser.logout, "/login/logout.php?a=1&sesskey=token")

    def test_jmeter_small_summary_rejects_short_and_underpopulated_run(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "run.jtl"
            output = Path(directory) / "summary.json"
            with source.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=("timeStamp", "elapsed", "label", "success", "threadName"))
                writer.writeheader()
                for label in ("Course", "Download", "Assignment view", "Logout", "Login"):
                    writer.writerow({"timeStamp": 1000, "elapsed": 1000, "label": label,
                                     "success": "true", "threadName": "student-1"})
            with patch("sys.argv", ["summarize_jmeter", str(source), "--output", str(output),
                                     "--workload", "small", "--expected-users", "2",
                                     "--minimum-seconds", "140"]):
                self.assertEqual(summarize_jmeter(), 1)
            result = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["observed_users"], 1)

    def test_jmeter_small_summary_passes_complete_run_and_separates_ramp(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "run.jtl"
            output = Path(directory) / "summary.json"
            rows = []
            for name in ("student-1", "student-2"):
                for label, stamp in (("Course", 1000), ("Download", 1100),
                                     ("Assignment view", 1200), ("Logout", 1300), ("Login", 1400),
                                     ("Course", 31000)):
                    rows.append({"timeStamp": stamp, "elapsed": 1000, "label": label,
                                 "success": "true", "threadName": name})
            with source.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=("timeStamp", "elapsed", "label", "success", "threadName"))
                writer.writeheader()
                writer.writerows(rows)
            with patch("sys.argv", ["summarize_jmeter", str(source), "--output", str(output),
                                     "--workload", "small", "--expected-users", "2",
                                     "--minimum-seconds", "31", "--ramp-seconds", "30"]):
                self.assertEqual(summarize_jmeter(), 0)
            result = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "passed")
            self.assertEqual(result["steady"]["transactions"]["Course"]["samples"], 2)


if __name__ == "__main__":
    unittest.main()
