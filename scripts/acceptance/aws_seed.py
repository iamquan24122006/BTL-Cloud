"""Seed the standard fixture on an active medium runner via SSM, without exporting passwords."""
from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path
import time

from src.moodle_cloud import aws, load_config, outputs


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='Public fixture IDs and file hashes only')
    parser.add_argument('--confirm', required=True, help='project-environment')
    args = parser.parse_args(argv)
    config = load_config(args.config)
    site = config['project'] + '-' + config['environment']
    if config['size'] != 'medium' or args.confirm != site:
        parser.error('Use a medium config and --confirm ' + site)
    if aws(config, 'sts', 'get-caller-identity')['Account'] != config['account_id']:
        raise RuntimeError('AWS account mismatch')
    runner = outputs(config)['runner_id']['value']
    instances = aws(config, 'ec2', 'describe-instances', '--instance-ids', runner)
    instance = instances['Reservations'][0]['Instances'][0]
    tags = {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}
    if tags.get('Name') != site + '-med-runner' or tags.get('Project') != config['project']:
        raise RuntimeError('Runner tags do not match the selected environment')
    code = Path(__file__).with_name('seed_fixture.php').read_text(encoding='utf-8').replace('<?php', '', 1)
    encoded = base64.b64encode(code.encode()).decode()
    script = """#!/bin/bash
set -eu
systemctl stop moodle-cron.timer
trap 'systemctl start moodle-cron.timer' EXIT
deadline=$((SECONDS+900))
while :; do
  state=$(systemctl show moodle-cron.service --property=ActiveState --value)
  case "$state" in inactive|failed) break ;; esac
  test "$SECONDS" -lt "$deadline"
  sleep 2
done
python3 - <<'PY'
import json,sys
from pathlib import Path
sys.path.insert(0,'/opt/moodle-medium')
from operations import Operations
d=json.loads(Path('/etc/moodle/deploy.json').read_text())
control=Path('/var/lib/moodledata/.distribution')
assert not (control/'blocked').exists(), 'Site must be active'
assert json.loads((control/'active.json').read_text())['release']==d['artifact']['release']
op=Operations('release')
try:
    op.php('-r','putenv("MOODLE_FIXTURE=yes");eval(base64_decode("BASE64_SCRIPT"));')
    print('FIXTURE_MANIFEST')
    print((control/'fixture.json').read_text())
    print('END_FIXTURE_MANIFEST')
finally:
    op.connection.close()
PY
""".replace('BASE64_SCRIPT', encoded)
    sent = aws(config, 'ssm', 'send-command', '--instance-ids', runner,
               '--document-name', 'AWS-RunShellScript', '--parameters',
               json.dumps({'commands': [script], 'executionTimeout': ['1800']}))
    command = sent['Command']['CommandId']
    print('Fixture command: ' + command, flush=True)
    deadline = time.monotonic() + 1920
    while time.monotonic() < deadline:
        rows = aws(config, 'ssm', 'list-command-invocations', '--command-id', command,
                   '--instance-id', runner, '--details')['CommandInvocations']
        if rows and rows[0]['Status'] not in ('Pending', 'InProgress', 'Delayed', 'Cancelling'):
            result = aws(config, 'ssm', 'get-command-invocation', '--command-id', command, '--instance-id', runner)
            if result['Status'] != 'Success' or result['ResponseCode'] != 0:
                raise RuntimeError('Fixture failed; inspect private runner operation log: ' + command)
            body = result['StandardOutputContent'].split('FIXTURE_MANIFEST\n', 1)[1].split('\nEND_FIXTURE_MANIFEST', 1)[0]
            fixture = json.loads(body)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(fixture, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
            print('Fixture IDs/hashes saved: ' + str(args.output))
            return 0
        time.sleep(5)
    raise RuntimeError('Command still pending; check SSM before retrying: ' + command)


if __name__ == '__main__':
    raise SystemExit(main())
