"""Failure guards for cluster workers; no database, Docker or AWS access."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

dependency = types.ModuleType('psycopg2')
dependency.sql = Mock()
with patch.dict(sys.modules, {'psycopg2': dependency}):
    spec = importlib.util.spec_from_file_location('medium_operations', Path(__file__).resolve().parents[1] / 'scripts/medium/operations.py')
    operations = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(operations)


class WorkerFailureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.control = patch.object(operations, 'CONTROL', self.root)
        self.control.start()
        self.addCleanup(self.control.stop)
        self.worker = operations.Operations.__new__(operations.Operations)

    def test_timeout_stops_worker_before_allowing_next_operation(self):
        timeout = subprocess.TimeoutExpired(['docker'], 3300)
        removed = subprocess.CompletedProcess([], 0)
        missing = subprocess.CompletedProcess([], 1, '', 'Error: No such container')
        logfile = self.root / 'worker.log'
        with patch.object(operations.subprocess, 'run', side_effect=[timeout, removed, missing]) as run, patch.object(operations, 'Path', side_effect=lambda p: logfile if p == '/var/log/moodle-medium.log' else Path(p)):
            with self.assertRaises(subprocess.TimeoutExpired):
                self.worker.php('/var/www/moodle/admin/cli/upgrade.php', migration=True)
        self.assertFalse((self.root / 'worker-pending.json').exists())
        self.assertEqual(run.call_count, 3)

    def test_uncertain_docker_worker_keeps_recovery_marker(self):
        finished = subprocess.CompletedProcess([], 0)
        unavailable = subprocess.CompletedProcess([], 1, '', 'Cannot connect to Docker daemon')
        logfile = self.root / 'worker.log'
        with patch.object(operations.subprocess, 'run', side_effect=[finished, unavailable, unavailable]), patch.object(operations, 'Path', side_effect=lambda p: logfile if p == '/var/log/moodle-medium.log' else Path(p)):
            with self.assertRaisesRegex(RuntimeError, 'Worker state uncertain'):
                self.worker.php('/var/www/moodle/admin/cli/upgrade.php', migration=True)
        self.assertTrue((self.root / 'worker-pending.json').exists())

    def test_interrupted_migration_cannot_be_retried_automatically(self):
        (self.root / 'migration-pending.json').write_text('{}')
        with patch.object(self.worker, 'configure_roles') as configure:
            with self.assertRaisesRegex(RuntimeError, 'Previous schema job'):
                self.worker.release()
        configure.assert_not_called()


if __name__ == '__main__':
    unittest.main()
