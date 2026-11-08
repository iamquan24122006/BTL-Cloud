"""Small authenticated read workload; keep user CSV and raw results private."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import datetime as dt
import hashlib
from html.parser import HTMLParser
from http.cookiejar import CookieJar
import json
from pathlib import Path
import random
import re
import threading
import time
from urllib.parse import urlencode, urljoin, urlparse
from urllib.request import build_opener, HTTPCookieProcessor, Request


class FormParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.token = None
        self.logout = None

    def handle_starttag(self, tag, attributes):
        attributes = dict(attributes)
        if tag == "input" and attributes.get("name") == "logintoken":
            self.token = attributes.get("value")
        if tag == "a" and "/login/logout.php" in attributes.get("href", "") and "sesskey=" in attributes["href"]:
            self.logout = attributes["href"]


def percentile(values, proportion):
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, min(len(ordered) - 1, int(len(ordered) * proportion + 0.999999) - 1))]


def summarize(rows, elapsed):
    summary = {"samples": len(rows), "elapsed_seconds": round(elapsed, 3), "transactions": {}}
    for name in sorted({row["transaction"] for row in rows}):
        samples = [row for row in rows if row["transaction"] == name]
        successes = [row["elapsed_ms"] for row in samples if row["ok"]]
        errors = sum(not row["ok"] for row in samples)
        summary["transactions"][name] = {
            "samples": len(samples), "errors": errors, "error_percent": round(errors * 100 / len(samples), 3),
            "p50_ms_success": percentile(successes, .5), "p95_ms_success": percentile(successes, .95),
            "p99_ms_success": percentile(successes, .99), "throughput_per_second": round(len(samples) / max(elapsed, .001), 3),
        }
    return summary


def execute(args):
    users = list(csv.DictReader(Path(args.users).open(encoding="utf-8", newline="")))
    if (not users or any(set(user) != {"username", "password"} or not all(user.values()) for user in users)
            or len({user['username'] for user in users}) != len(users)):
        raise ValueError("users CSV needs unique username,password rows")
    if args.concurrency > len(users):
        raise ValueError("Each virtual user must have a separate account")
    base = args.url.rstrip("/") + "/"
    if not re.fullmatch(r"https?://[^/]+/?", base):
        raise ValueError("url must be an HTTP(S) site origin")
    if urlparse(base).username or urlparse(base).password:
        raise ValueError("Do not put credentials in the URL")
    if not args.file_path.startswith("/") or args.file_path.startswith("//"):
        raise ValueError("file-path must be relative to the selected site origin")
    if not re.fullmatch(r"[a-f0-9]{64}", args.file_sha256):
        raise ValueError("file-sha256 must be a SHA-256 hex digest")
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    rows = []
    lock = threading.Lock()
    started = time.monotonic()
    deadline = started + args.duration

    def worker(index, user):
        time.sleep(index * args.ramp / max(args.concurrency - 1, 1))
        opener = build_opener(HTTPCookieProcessor(CookieJar()))
        opener.addheaders = [("User-Agent", "MoodleCloudLabLoad/0.2")]
        logout = None

        def request(transaction, path, fields=None, predicate=None):
            nonlocal logout
            stamp = dt.datetime.now(dt.timezone.utc).isoformat()
            begin = time.monotonic()
            ok, error, body = False, "", b""
            try:
                url = urljoin(base, path)
                if urlparse(url).netloc != urlparse(base).netloc:
                    raise ValueError("Cross-origin request refused")
                req = Request(url, data=urlencode(fields).encode() if fields is not None else None)
                with opener.open(req, timeout=45) as response:
                    body = response.read()
                    final = response.url
                    ok = response.status == 200 and (predicate(body, final) if predicate else True)
                    parser = FormParser()
                    if "text/html" in response.headers.get("Content-Type", ""):
                        parser.feed(body.decode("utf-8", errors="replace"))
                        logout = parser.logout or logout
                if not ok:
                    error = "business_assertion_failed"
            except Exception as exc:
                # Never persist a response body, cookie, password or exception text.
                error = type(exc).__name__
            row = {"utc": stamp, "virtual_user": index, "transaction": transaction,
                   "elapsed_ms": round((time.monotonic() - begin) * 1000, 3), "ok": ok, "error": error}
            with lock:
                rows.append(row)
            return body, ok

        body, ok = request("login_form", "login/index.php")
        parser = FormParser()
        parser.feed(body.decode("utf-8", errors="replace"))
        if not ok or not parser.token:
            return
        _, ok = request("login", "login/index.php", {**user, "logintoken": parser.token},
                        lambda body, url: "/login/" not in url and b"loginerrors" not in body)
        if not ok:
            return
        course = f"course/view.php?id={args.course_id}"
        while time.monotonic() < deadline:
            if random.random() < .25:
                request("download", args.file_path, predicate=lambda body, url: hashlib.sha256(body).hexdigest() == args.file_sha256)
            else:
                request("course", course, predicate=lambda body, url: "/course/view.php" in url
                        and args.course_marker.encode() in body and b'"usernavigation"' in body)
            time.sleep(random.uniform(args.think_min, args.think_max))
        if logout:
            request("logout", logout)
            request("private_file_after_logout", args.file_path,
                    predicate=lambda body, url: hashlib.sha256(body).hexdigest() != args.file_sha256)

    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        list(pool.map(lambda pair: worker(*pair), enumerate(users[:args.concurrency])))
    elapsed = time.monotonic() - started
    with (output / "samples.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["utc", "virtual_user", "transaction", "elapsed_ms", "ok", "error"])
        writer.writeheader()
        writer.writerows(rows)
    report = summarize(rows, elapsed)
    report.update(scope="Authenticated read-only protocol workload, 75% course / 25% download; excludes submission writes and browser rendering",
                  concurrency=args.concurrency, requested_seconds=args.duration, ramp_seconds=args.ramp,
                  think_seconds=[args.think_min, args.think_max], source_origin=base)
    required = {"course", "download"}
    report["status"] = "passed" if required <= report['transactions'].keys() and all(row['ok'] for row in rows) else "failed"
    (output / "summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "passed" else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--users", required=True, help="Private CSV with unique username,password columns")
    parser.add_argument("--course-id", type=int, required=True)
    parser.add_argument("--course-marker", required=True)
    parser.add_argument("--file-path", required=True)
    parser.add_argument("--file-sha256", required=True)
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--duration", type=int, default=120)
    parser.add_argument("--ramp", type=int, default=10)
    parser.add_argument("--think-min", type=float, default=3)
    parser.add_argument("--think-max", type=float, default=8)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    if not (1 <= args.concurrency <= 200 and args.duration > 0 and 0 <= args.ramp < args.duration
            and 0 <= args.think_min <= args.think_max):
        parser.error("Invalid concurrency, duration, ramp or think times")
    try:
        return execute(args)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
