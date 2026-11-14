import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import course_burst


class CourseBurstTests(unittest.TestCase):
    def test_first_failed_read_stops_new_users_and_does_not_log_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            csv = root / 'users.csv'
            password = 'synthetic-password-must-not-be-published'
            csv.write_text('username,password\na,' + password + '\nb,' + password + '\nc,' + password + '\n', encoding='utf-8')
            report = root / 'result.json'
            logins, requests = [], []

            class FailingClient:
                def __init__(self, url):
                    pass

                def login(self, username, credential):
                    logins.append(username)
                    return 200, b'<a href="https://moodle.example.com/login/logout.php?sesskey=fixture">Logout</a>', 'https://moodle.example.com/user/profile.php'

                def get(self, path):
                    if '/course/view.php' in path:
                        requests.append(path)
                        raise RuntimeError(password)
                    return 200, b'logged out', 'https://moodle.example.com/login/index.php'

            argv = ['burst', '--url', 'https://moodle.example.com', '--users-csv', str(csv), '--course-id', '2',
                    '--course-marker', 'Benchmark', '--users', '3', '--seconds', '30', '--output', str(report)]
            stdout = io.StringIO()
            with patch('sys.argv', argv), patch.object(course_burst, 'Client', FailingClient), patch('sys.stdout', stdout):
                self.assertTrue(course_burst.main())
            result = json.loads(report.read_text(encoding='utf-8'))
            self.assertEqual(result['status'], 'failed')
            self.assertEqual(len(requests), 1)
            self.assertEqual(len(logins), 1)
            self.assertNotIn(password, report.read_text(encoding='utf-8'))
            self.assertNotIn(password, stdout.getvalue())

    def test_credentials_in_target_url_are_rejected_before_opening_csv(self):
        argv = ['burst', '--url', 'https://user:private-value@moodle.example.com', '--users-csv', 'missing.csv',
                '--course-id', '2', '--course-marker', 'Benchmark', '--output', 'unused.json']
        stderr = io.StringIO()
        with patch('sys.argv', argv), patch('sys.stderr', stderr), patch.object(course_burst, 'Client') as client:
            with self.assertRaises(SystemExit) as raised:
                course_burst.main()
        self.assertEqual(raised.exception.code, 2)
        client.assert_not_called()
        self.assertNotIn('private-value', stderr.getvalue())
