"""Collect bounded Linux host/DB samples without query text or credentials."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import shutil
import subprocess
import time


def cpu_ticks():
    ticks = [int(value) for value in Path('/proc/stat').read_text().splitlines()[0].split()[1:9]]
    return sum(ticks), ticks[3] + ticks[4]


def sample(previous):
    total, idle = cpu_ticks()
    oldtotal, oldidle = previous
    memory = {line.split(':')[0]: int(line.split()[1]) for line in Path('/proc/meminfo').read_text().splitlines()}
    disk = shutil.disk_usage('/var/lib/moodledata')
    row = {'utc': dt.datetime.now(dt.timezone.utc).isoformat(),
           'cpu_percent': round(100 * (1 - (idle-oldidle) / max(total-oldtotal, 1)), 3),
           'load_average': [float(value) for value in Path('/proc/loadavg').read_text().split()[:3]],
           'memory_available_kib': memory['MemAvailable'], 'memory_total_kib': memory['MemTotal'],
           'swap_used_kib': memory['SwapTotal']-memory['SwapFree'],
           'disk_used_bytes': disk.used, 'disk_free_bytes': disk.free}
    query = ('SELECT (SELECT count(*) FROM pg_stat_activity WHERE datname=current_database()), '
             '(SELECT count(*) FROM mdl_task_scheduled WHERE faildelay>0 AND disabled=0), '
             '(SELECT count(*) FROM mdl_task_adhoc WHERE faildelay>0);')
    result = subprocess.run(['runuser','-u','postgres','--','psql','-d','moodle','-Atc',query],
                            capture_output=True, text=True, timeout=10)
    if result.returncode == 0:
        values = [int(value) for value in result.stdout.strip().split('|')]
        row.update(zip(('db_connections','scheduled_failures','adhoc_failures'), values))
    else:
        row['db_sample_error'] = True
    return row, (total, idle)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--duration', type=int, required=True)
    parser.add_argument('--interval', type=int, default=15)
    parser.add_argument('--stop-file', type=Path)
    args = parser.parse_args()
    if not 1 <= args.interval <= args.duration <= 14400:
        parser.error('Require 1 <= interval <= duration <= 14400 seconds')
    deadline = time.monotonic() + args.duration
    previous = cpu_ticks()
    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as stream:
        while time.monotonic() < deadline:
            if args.stop_file and args.stop_file.exists():
                break
            time.sleep(min(args.interval, max(0, deadline-time.monotonic())))
            try:
                row, previous = sample(previous)
            except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
                row = {'utc':dt.datetime.now(dt.timezone.utc).isoformat(),'sample_error':type(exc).__name__}
            stream.write(json.dumps(row) + '\n')
            stream.flush()


if __name__ == '__main__':
    main()
