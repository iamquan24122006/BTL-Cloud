#!/usr/bin/env python3
"""Fetch runtime secrets without printing them or accepting secret argv values."""
import json
import os
from pathlib import Path
import subprocess

directory = Path('/etc/moodle')
deploy = json.loads((directory / 'deploy.json').read_text())


def secret(arn, version=None):
    args = ['aws', '--region', deploy['region'], '--no-cli-pager', 'secretsmanager', 'get-secret-value', '--secret-id', arn, '--output', 'json']
    if version:
        args += ['--version-id', version]
    result = json.loads(subprocess.check_output(args, text=True))
    return json.loads(result['SecretString'])


def save(name, value, group=33):
    path = directory / name
    temporary = directory / (name + '.new')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o640)
    os.fchown(fd, 0, group)
    with os.fdopen(fd, 'w') as stream:
        json.dump(value, stream)
    temporary.replace(path)


runtime = secret(deploy['secrets']['runtime_arn'])
if runtime.get('username') != 'moodle_runtime' or not isinstance(runtime.get('password'), str) or len(runtime['password']) < 24:
    raise ValueError('runtime secret requires username=moodle_runtime and a password of at least 24 characters')
redis = secret(deploy['secrets']['redis_arn'], deploy['secrets']['redis_version'])
token = redis.get('token', '')
if not isinstance(token, str) or not 16 <= len(token) <= 128 or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!&#$^<>-' for c in token):
    raise ValueError('redis token must meet ElastiCache AUTH token constraints')
save('runtime.json', {'database': runtime, 'redis': redis})
if deploy['role'] == 'runner':
    migration = secret(deploy['secrets']['migration_arn'])
    if migration.get('username') != 'moodle_migration' or len(migration.get('password', '')) < 24:
        raise ValueError('migration secret requires username=moodle_migration and a password of at least 24 characters')
    save('migration.json', migration)
    save('master.json', secret(deploy['master_secret_arn']), 0)
