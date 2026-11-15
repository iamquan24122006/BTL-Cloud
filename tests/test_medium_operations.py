"""Failure guards for cluster workers; no database, Docker or AWS access."""
import importlib.util
from contextlib import contextmanager
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch, call

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


class BackupWindowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.fcntl = types.SimpleNamespace(LOCK_EX=2, LOCK_NB=4, flock=Mock())
        patches = [patch.dict(sys.modules, {'fcntl': self.fcntl}),
                   patch.object(operations, 'BACKUP_LOCK', self.root / 'backup.lock'),
                   patch.object(operations, 'CONTROL', self.root),
                   patch.object(operations, 'read', return_value={'role': 'runner'}),
                   patch.object(operations.time, 'sleep')]
        for replacement in patches:
            replacement.start()
            self.addCleanup(replacement.stop)

    def test_backup_waits_for_activating_cron_and_restores_timer(self):
        with patch.object(operations.subprocess, 'check_output', side_effect=['active', 'activating', 'active', 'inactive']), patch.object(operations.subprocess, 'run') as run:
            with operations.backup_window():
                self.assertEqual(operations.time.sleep.call_count, 2)
                self.assertEqual(run.call_args_list, [call(['systemctl', 'stop', 'moodle-cron.timer'], check=True, timeout=30)])
            self.assertEqual(run.call_args_list[-1], call(['systemctl', 'start', 'moodle-cron.timer'], check=True, timeout=30))

    def test_failure_keeps_maintenance_and_restores_timer(self):
        marker = self.root / 'blocked'
        with patch.object(operations.subprocess, 'check_output', side_effect=['active', 'inactive']), patch.object(operations.subprocess, 'run') as run:
            with self.assertRaisesRegex(RuntimeError, 'upload failed'):
                with operations.backup_window():
                    marker.touch()
                    raise RuntimeError('upload failed')
            self.assertTrue(marker.exists())
            self.assertEqual(run.call_args_list[-1], call(['systemctl', 'start', 'moodle-cron.timer'], check=True, timeout=30))

    def test_drain_timeout_does_not_enter_backup_or_kill_cron(self):
        with patch.object(operations.subprocess, 'check_output', side_effect=['active', 'activating']), patch.object(operations.subprocess, 'run') as run:
            with self.assertRaisesRegex(RuntimeError, 'did not drain'):
                with operations.backup_window(timeout=0):
                    self.fail('Backup must not start before cron finishes')
            self.assertEqual([c.args[0] for c in run.call_args_list], [
                ['systemctl', 'stop', 'moodle-cron.timer'], ['systemctl', 'start', 'moodle-cron.timer']])

    def test_previously_disabled_timer_stays_disabled(self):
        with patch.object(operations.subprocess, 'check_output', side_effect=['inactive', 'failed']), patch.object(operations.subprocess, 'run') as run:
            with operations.backup_window():
                pass
            run.assert_not_called()

    def test_concurrent_backup_does_not_touch_timer(self):
        self.fcntl.flock.side_effect = BlockingIOError()
        with patch.object(operations.subprocess, 'check_output') as state, patch.object(operations.subprocess, 'run') as run:
            with self.assertRaisesRegex(RuntimeError, 'local cron-drain lock'):
                with operations.backup_window():
                    self.fail('Second backup must not start')
            state.assert_not_called()
            run.assert_not_called()

    def test_app_node_rejected_before_host_changes(self):
        with patch.object(operations, 'read', return_value={'role': 'app'}), patch.object(operations.subprocess, 'run') as run:
            with self.assertRaisesRegex(RuntimeError, 'dedicated runner'):
                with operations.backup_window():
                    self.fail('App node must not perform backup')
            self.fcntl.flock.assert_not_called()
            run.assert_not_called()

    def test_database_lock_released_before_timer_resumes_on_upload_failure(self):
        (self.root / 'active.json').write_text('{}')
        events = []
        worker = Mock()
        worker.backup.side_effect = RuntimeError('upload failed')
        worker.connection.close.side_effect = lambda: events.append('database-closed')

        @contextmanager
        def window():
            events.append('cron-drained')
            try:
                yield
            finally:
                events.append('timer-restored')

        with patch.object(operations, 'backup_window', window), patch.object(operations, 'Operations', return_value=worker), patch.object(sys, 'argv', ['operations.py', 'backup']):
            self.assertEqual(operations.main(), 1)
        worker.unblock.assert_not_called()
        worker.block.assert_called_once()
        worker.connection.close.assert_called_once()
        self.assertEqual(events, ['cron-drained', 'database-closed', 'timer-restored'])


if __name__ == '__main__':
    unittest.main()
