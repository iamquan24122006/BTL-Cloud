"""Exercise a seeded Moodle site over its real HTTPS endpoint. Never logs credentials/cookies."""
from __future__ import annotations
import argparse
import hashlib
import hmac
import html
from html.parser import HTMLParser
import http.cookiejar
import json
from pathlib import Path
import time
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import build_opener, HTTPCookieProcessor, Request


class Form(HTMLParser):
    def __init__(self, body):
        super().__init__()
        self.inputs = {}
        self.links = []
        self.feed(body.decode('utf-8', errors='replace'))

    def handle_starttag(self, tag, attrs):
        value = dict(attrs)
        if tag == 'input' and value.get('name'):
            self.inputs[value['name']] = value.get('value', '')
        if tag == 'a' and value.get('href'):
            self.links.append(value['href'])


class Client:
    def __init__(self, url):
        self.url = url.rstrip('/')
        self.cookies = http.cookiejar.CookieJar()
        self.opener = build_opener(HTTPCookieProcessor(self.cookies))

    def get(self, path, data=None):
        url = path if path.startswith('https://') else self.url + path
        request = Request(url, data=urlencode(data).encode() if data is not None else None,
                          headers={'User-Agent': 'MoodleCloud-N2-Acceptance/1.0'})
        try:
            with self.opener.open(request, timeout=60) as response:
                return response.status, response.read(), response.url
        except HTTPError as exc:
            return exc.code, exc.read(), exc.url

    def login(self, username, password):
        status, body, _ = self.get('/login/index.php')
        token = Form(body).inputs.get('logintoken')
        if status != 200 or not token:
            raise RuntimeError('Login form is unavailable')
        self.get('/login/index.php', {'username': username, 'password': password, 'logintoken': token})
        return self.get('/user/profile.php')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', required=True)
    parser.add_argument('--fixture', type=Path, required=True)
    parser.add_argument('--admin-credentials', type=Path, required=True)
    parser.add_argument('--fixture-credentials', type=Path,
                        help='Private {users: {role: {username, password}}} file; use after rotating the initial admin password')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    if urlsplit(args.url).scheme != 'https':
        parser.error('Real endpoint acceptance requires HTTPS')
    fixture = json.loads(args.fixture.read_text(encoding='utf-8'))
    admin = json.loads(args.admin_credentials.read_text(encoding='utf-8'))
    fixture_credentials = (json.loads(args.fixture_credentials.read_text(encoding='utf-8'))['users']
                           if args.fixture_credentials else None)
    checks = []
    report = {'url': args.url, 'started_unix': time.time(), 'scope': 'Real HTTPS, seeded roles/files/assignment; separate ASG/restore evidence required', 'checks': checks}

    def check(name, condition):
        checks.append({'name': name, 'passed': bool(condition)})
        print(name + ': ' + ('PASS' if condition else 'FAIL'), flush=True)
        if not condition:
            raise RuntimeError(name)

    def hash_response(client, path):
        status, body, _ = client.get(path)
        return status, hashlib.sha256(body).hexdigest()

    try:
        administrator = Client(args.url)
        status, body, location = administrator.login(admin['username'], admin['password'])
        check('login-admin', status == 200 and '/login/index.php' not in location
              and any('/login/logout.php?' in link for link in Form(body).links))
        status, body, _ = administrator.get('/admin/search.php')
        check('admin-site-settings', status == 200 and b'Site administration' in body
              and 'query' in Form(body).inputs)
        clients = {}
        for key, user in fixture['users'].items():
            client = Client(args.url)
            if fixture_credentials is not None:
                credential = fixture_credentials[key]
                if credential['username'] != user['username']:
                    raise RuntimeError('Fixture credential username does not match fixture')
                password = credential['password']
            else:
                # Backwards compatibility for the initial deterministic seed only.
                password = hmac.new(admin['password'].encode(), user['username'].encode(), hashlib.sha256).hexdigest()[:32] + 'Aa7!'
            status, body, location = client.login(user['username'], password)
            check('login-' + key, status == 200 and '/login/index.php' not in location and b'CloudLab' in body)
            clients[key] = client
        bad = Client(args.url)
        status, body, location = bad.login(fixture['users']['student_a']['username'], 'intentionally-wrong-fixture-password')
        check('wrong-password-rejected', '/login/index.php' in location)
        guest = Client(args.url)
        for number, resource in enumerate(fixture['resources']):
            for key in ('teacher', 'student_a', 'student_b'):
                status, result = hash_response(clients[key], resource['path'])
                check(f'file-{number}-{key}-sha256', status == 200 and result == resource['sha256'])
            check(f'file-{number}-guest-denied', hash_response(guest, resource['path'])[1] != resource['sha256'])
            check(f'file-{number}-unenrolled-denied', hash_response(clients['student_c'], resource['path'])[1] != resource['sha256'])
        assignment = fixture['assignment']
        for key, submission in fixture['submissions'].items():
            for viewer in (key, 'teacher'):
                status, result = hash_response(clients[viewer], submission['path'])
                check(f'submission-{key}-{viewer}-sha256', status == 200 and result == submission['sha256'])
            other = 'student_b' if key == 'student_a' else 'student_a'
            check('submission-' + key + '-peer-denied', hash_response(clients[other], submission['path'])[1] != submission['sha256'])
            status, body, _ = clients[key].get('/mod/assign/view.php?id=' + str(assignment['cmid']))
            check('grade-feedback-' + key, status == 200 and ('FEEDBACK-' + key.upper() + '-OK').encode() in body)
            check('grade-value-' + key, (str(submission['grade']) + '.00').encode() in body)
            check('private-peer-feedback-' + key, ('FEEDBACK-' + other.upper() + '-OK').encode() not in body)
        course = fixture['courses']['CLOUD-C01']
        status, body, _ = clients['teacher'].get('/course/edit.php?id=' + str(course))
        check('teacher-course-settings', status == 200 and b'id_fullname' in body)
        status, body, _ = clients['student_a'].get('/course/edit.php?id=' + str(course))
        check('student-course-edit-denied', b'id_fullname' not in body)
        status, body, _ = clients['student_a'].get('/admin/search.php')
        check('student-admin-denied', status in (400, 403, 404) or b'not have permission' in body or b'nopermissions' in body)
        # Repeated private-file requests use one cookie and can be correlated with
        # internal per-instance access logs to establish distribution across nodes.
        for n in range(12):
            check('shared-session-file-' + str(n), hash_response(clients['student_a'], fixture['resources'][0]['path'])[1] == fixture['resources'][0]['sha256'])
        status, body, _ = clients['student_a'].get('/user/profile.php')
        logout = next((u for u in Form(body).links if '/login/logout.php?' in u), None)
        check('logout-link', logout is not None)
        old_cookie = '; '.join(c.name + '=' + c.value for c in clients['student_a'].cookies)
        clients['student_a'].get(logout)
        check('logout-private-file-denied', hash_response(clients['student_a'], fixture['resources'][0]['path'])[1] != fixture['resources'][0]['sha256'])
        replay = Request(args.url.rstrip('/') + fixture['resources'][0]['path'], headers={'Cookie': old_cookie})
        try:
            with build_opener().open(replay, timeout=60) as response:
                replay_hash = hashlib.sha256(response.read()).hexdigest()
        except HTTPError:
            replay_hash = None
        check('logged-out-cookie-invalid', replay_hash != fixture['resources'][0]['sha256'])
        report['status'] = 'passed'
    except Exception as exc:
        report['status'] = 'failed'
        report['error'] = type(exc).__name__ + ': ' + str(exc)
        print('Acceptance failed: ' + str(exc))
    finally:
        report['finished_unix'] = time.time()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return 0 if report.get('status') == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
