"""Summarize JMeter CSV results without copying response bodies or credentials."""
import argparse
import csv
import json
from pathlib import Path

from scripts.load_test import summarize


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workload", choices=("read", "small"), default="read")
    parser.add_argument("--expected-users", type=int)
    parser.add_argument("--minimum-seconds", type=float, default=0)
    parser.add_argument("--ramp-seconds", type=float, default=0)
    args = parser.parse_args(argv)
    with args.input.open(encoding="utf-8-sig", newline="") as stream:
        records = list(csv.DictReader(stream))
    if not records:
        parser.error("No JMeter samples")
    try:
        rows = [{"transaction": row["label"], "elapsed_ms": float(row["elapsed"]),
                 "ok": row["success"].lower() == "true"} for row in records]
        started = min(int(row["timeStamp"]) for row in records)
        finished = max(int(row["timeStamp"]) + int(row["elapsed"]) for row in records)
    except (KeyError, ValueError):
        parser.error("Expected standard JMeter CSV columns: timeStamp,elapsed,label,success")
    elapsed = (finished - started) / 1000
    report = summarize(rows, elapsed)
    users = {row.get('threadName') for row in records if row['label'] == 'Login' and row['success'].lower() == 'true'}
    required = {"Course", "Download"}
    if args.workload == 'small':
        required |= {'Assignment view', 'Logout'}
    complete = (elapsed >= args.minimum_seconds and
                (args.expected_users is None or len(users) == args.expected_users))
    steady = [row for raw, row in zip(records, rows) if int(raw['timeStamp']) >= started + args.ramp_seconds * 1000]
    steady_seconds = max(0, elapsed - args.ramp_seconds)
    report.update(scope=("JMeter small: 60% course / 20% download / 10% assignment view / 10% auth cycle by logical actions; fresh HTTP connections; no submission writes or browser rendering"
                         if args.workload == 'small' else "JMeter authenticated reads, 50% course / 50% download; excludes submission writes and browser rendering"),
                  observed_users=len(users), expected_users=args.expected_users,
                  minimum_seconds=args.minimum_seconds, ramp_seconds=args.ramp_seconds,
                  steady=summarize(steady, steady_seconds),
                  status="passed" if complete and required <= report["transactions"].keys() and all(row['ok'] for row in rows) else "failed",
                  conclusion="Protocol smoke/load observations only; record workload, unique users, ramp, duration, CPU credits and repeats before capacity conclusions")
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
