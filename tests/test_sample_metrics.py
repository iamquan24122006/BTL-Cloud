import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts import sample_metrics as metrics


class MetricSamplingTests(unittest.TestCase):
    def test_cpu_uses_interval_delta_and_db_sample_contains_only_counts(self):
        with patch.object(metrics, 'cpu_ticks', return_value=(1000, 700)), \
                patch.object(metrics.Path, 'read_text', side_effect=[
                    'MemTotal: 2048 kB\nMemAvailable: 1024 kB\nSwapTotal: 512 kB\nSwapFree: 500 kB\n',
                    '0.2 0.3 0.4 1/30 100']), \
                patch.object(metrics.shutil, 'disk_usage', return_value=SimpleNamespace(used=100, free=900)), \
                patch.object(metrics.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout='5|0|1\n')):
            row, ticks = metrics.sample((500, 350))
        self.assertEqual(row['cpu_percent'], 30)
        self.assertEqual(row['swap_used_kib'], 12)
        self.assertEqual(row['db_connections'], 5)
        self.assertEqual(row['adhoc_failures'], 1)
        self.assertEqual(ticks, (1000, 700))

    def test_db_failure_does_not_copy_sensitive_stderr_into_metrics(self):
        with patch.object(metrics, 'cpu_ticks', return_value=(1000, 700)), \
                patch.object(metrics.Path, 'read_text', side_effect=[
                    'MemTotal: 2048 kB\nMemAvailable: 1024 kB\nSwapTotal: 0 kB\nSwapFree: 0 kB\n',
                    '0 0 0 1/30 100']), \
                patch.object(metrics.shutil, 'disk_usage', return_value=SimpleNamespace(used=100, free=900)), \
                patch.object(metrics.subprocess, 'run', return_value=SimpleNamespace(returncode=1, stderr='private connection details')):
            row, _ = metrics.sample((500, 350))
        self.assertTrue(row['db_sample_error'])
        self.assertNotIn('private', json.dumps(row))


if __name__ == '__main__':
    unittest.main()
