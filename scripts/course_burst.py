"""Short authenticated course-read burst for a controlled scaling drill.

This is separate from the standard 60/20/10/10 comparative benchmark. Credentials
stay in a private CSV; the first failed request stops new work for every user.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import datetime as dt
import json
from pathlib import Path
import threading
import time
from urllib.parse import urlsplit

from scripts.acceptance.http_check import Client, Form
from scripts.load_test import percentile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', required=True)
    parser.add_argument('--users-csv', required=True, type=Path)
    parser.add_argument('--course-id', required=True, type=int)
    parser.add_argument('--course-marker', required=True)
    parser.add_argument('--users', type=int, default=10)
    parser.add_argument('--seconds', type=int, default=360)
    parser.add_argument('--think-seconds', type=float, default=0.2)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    address = urlsplit(args.url)
    if (address.scheme != 'https' or not address.hostname or address.username or address.password
            or address.path not in ('', '/') or address.query or address.fragment
            or not 1 <= args.users <= 20 or not 30 <= args.seconds <= 600
            or not 0.1 <= args.think_seconds <= 8 or args.course_id < 2):
        parser.error('Use an HTTPS origin, 1-20 users, 30-600 seconds and 0.1-8 seconds think time')
    with args.users_csv.open(encoding='utf-8', newline='') as stream:
        users = list(csv.DictReader(stream))
    if (len(users) < args.users or any(set(u) != {'username', 'password'} or not all(u.values()) for u in users)
            or len({u['username'] for u in users}) != len(users)):
        parser.error('A private CSV with enough unique username/password rows is required')
    stop = threading.Event()
    lock = threading.Lock()
    latencies, errors = [], []
    authenticated = []
    started = time.monotonic()
    deadline = started + args.seconds
    start_utc = dt.datetime.now(dt.timezone.utc).isoformat()

    def worker(index):
        if stop.wait(index * 0.5):
            return
        client = Client(args.url)
        logout = None
        try:
            user = users[index]
            code, body, location = client.login(user['username'], user['password'])
            links = Form(body).links
            logout = next((link for link in links if '/login/logout.php?' in link), None)
            if code != 200 or not logout or '/login/' in location:
                raise RuntimeError('LoginAssertion')
            with lock:
                authenticated.append(index)
            while time.monotonic() < deadline and not stop.is_set():
                begin = time.monotonic()
                code, body, location = client.get('/course/view.php?id=' + str(args.course_id))
                if code != 200 or urlsplit(location).path != '/course/view.php' or args.course_marker.encode() not in body:
                    raise RuntimeError('CourseAssertion')
                with lock:
                    latencies.append((time.monotonic() - begin) * 1000)
                stop.wait(args.think_seconds)
        except Exception as error:
            with lock:
                errors.append(type(error).__name__)
            stop.set()
        finally:
            if logout:
                try:
                    client.get(logout)
                except Exception:
                    with lock:
                        errors.append('LogoutFailure')
                    stop.set()

    with ThreadPoolExecutor(max_workers=args.users) as pool:
        list(pool.map(worker, range(args.users)))
    result = {'started_utc': start_utc, 'finished_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
              'url': args.url, 'course_id': args.course_id, 'requested_seconds': args.seconds,
              'elapsed_seconds': round(time.monotonic() - started, 3), 'users': args.users,
              'authenticated_users': len(authenticated), 'course_samples': len(latencies),
              'course_p95_ms': percentile(latencies, .95), 'error_types': errors,
              'think_seconds': args.think_seconds,
              'scope': 'Controlled course-read burst for scaling; excluded from the comparative benchmark',
              'status': 'passed' if len(authenticated) == args.users and latencies and not errors else 'failed'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
    return result['status'] != 'passed'


if __name__ == '__main__':
    raise SystemExit(main())
