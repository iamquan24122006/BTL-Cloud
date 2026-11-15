#!/usr/bin/env python3
"""Runner-only operations. Failures deliberately leave the site blocked for inspection."""
from __future__ import annotations
import argparse
from contextlib import contextmanager, ExitStack
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

import psycopg2
from psycopg2 import sql

ETC = Path('/etc/moodle')
DATA = Path('/var/lib/moodledata')
CONTROL = DATA / '.distribution'
BIN = Path('/opt/moodle-medium')
BACKUP_LOCK = Path('/run/moodle-medium-backup.lock')


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    temporary = path.with_suffix('.new')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    os.chmod(temporary, 0o660)
    temporary.replace(path)


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


@contextmanager
def backup_window(timeout=900):
    """Drain cron before taking its DB lock; preserve the timer's previous state.

    The local lock prevents a second backup from restarting cron while the first
    is still draining. The database lock remains the cluster-wide authority.
    This context never clears maintenance or kills a running Moodle task.
    """
    import fcntl  # The runner is Linux; import lazily for offline Windows tests.

    if read(ETC / 'deploy.json')['role'] != 'runner':
        raise RuntimeError('Backup must run on the dedicated runner')

    def state(unit):
        return subprocess.check_output(
            ['systemctl', 'show', unit, '--property=ActiveState', '--value'],
            text=True, timeout=30).strip()

    with BACKUP_LOCK.open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError('Another backup owns the local cron-drain lock') from exc
        timer_state = state('moodle-cron.timer')
        if timer_state not in ('active', 'inactive', 'failed'):
            raise RuntimeError('Cron timer is transitioning; retry after it settles')
        restart_timer = timer_state == 'active'
        try:
            if restart_timer:
                subprocess.run(['systemctl', 'stop', 'moodle-cron.timer'], check=True, timeout=30)
            deadline = time.monotonic() + timeout
            while True:
                cron_state = state('moodle-cron.service')
                if cron_state in ('inactive', 'failed'):
                    break
                if cron_state not in ('active', 'activating', 'deactivating'):
                    raise RuntimeError('Unknown cron state; backup was not started')
                if time.monotonic() >= deadline:
                    raise RuntimeError('Cron did not drain within the backup timeout')
                time.sleep(2)
            yield
        finally:
            if restart_timer:
                subprocess.run(['systemctl', 'start', 'moodle-cron.timer'], check=True, timeout=30)


class Operations:
    def __init__(self, kind):
        self.d = read(ETC / 'deploy.json')
        if self.d['role'] != 'runner':
            raise RuntimeError('Operations must run on the dedicated runner')
        self.runtime = read(ETC / 'runtime.json')['database']
        self.migration = read(ETC / 'migration.json')
        self.master = read(ETC / 'master.json') if kind != 'cron' else None
        self.connection = self.connect(self.runtime if kind == 'cron' else self.master)
        try:
            self.connection.autocommit = True
            with self.connection.cursor() as cursor:
                cursor.execute('SELECT pg_try_advisory_lock(hashtextextended(%s, 0))', (self.d['name'] + ':distribution',))
                if not cursor.fetchone()[0]:
                    raise RuntimeError('Another cron/release/backup/restore owns the cluster operation lock')
            if (CONTROL / 'worker-pending.json').exists():
                raise RuntimeError('A previous worker needs recovery review; do not start another operation')
        except Exception:
            self.connection.close()
            raise
        self.env = os.environ.copy()
        self.env.update(PGHOST=self.d['db_host'], PGDATABASE=self.d['db_name'], PGUSER=self.migration['username'],
                        PGPASSWORD=self.migration['password'], PGSSLMODE='verify-full',
                        PGSSLROOTCERT=str(ETC / 'rds-global.pem'), PGCONNECT_TIMEOUT='5')

    def connect(self, credentials):
        return psycopg2.connect(host=self.d['db_host'], dbname=self.d['db_name'],
                                user=credentials['username'], password=credentials['password'],
                                sslmode='verify-full', sslrootcert=str(ETC / 'rds-global.pem'), connect_timeout=5)

    def aws(self, *args):
        output = subprocess.check_output(['aws', '--region', self.d['region'], '--no-cli-pager', *args, '--output', 'json'], text=True)
        return json.loads(output) if output.strip() else {}

    def log(self, step):
        value = {'time': now(), 'step': step, 'release': self.d['artifact']['release']}
        write(CONTROL / 'operation.json', value)
        with Path('/var/log/moodle-medium.log').open('a') as stream:
            stream.write(json.dumps(value) + '\n')
        print(json.dumps(value), flush=True)

    def metric(self, name):
        self.aws('cloudwatch', 'put-metric-data', '--namespace', 'MoodleMedium', '--metric-data',
                 json.dumps([{'MetricName': name, 'Dimensions': [{'Name': 'Site', 'Value': self.d['name']}], 'Value': 1}]))

    def php(self, *args, migration=False):
        env = os.environ.copy()
        env['MOODLE_DB_ROLE'] = 'migration' if migration else 'runtime'
        name = 'moodle-operation-' + uuid.uuid4().hex
        env['MOODLE_CLI_NAME'] = name
        pending = CONTROL / 'worker-pending.json'
        write(pending, {'container': name, 'step': Path(args[0]).name, 'time': now()})
        try:
            with Path('/var/log/moodle-medium.log').open('a') as stream:
                subprocess.run([str(BIN / 'container.sh'), *args], env=env, check=True, timeout=3300,
                               stdout=stream, stderr=subprocess.STDOUT)
        finally:
            # Killing the Docker client alone does not stop its container. Fence it
            # while still holding the cluster lock; retain the marker if uncertain.
            subprocess.run(['docker', 'rm', '--force', name], capture_output=True, timeout=180)
            result = subprocess.run(['docker', 'container', 'inspect', '--format', '{{.State.Running}}', name],
                                    capture_output=True, text=True, timeout=30)
            missing = result.returncode != 0 and 'No such' in result.stderr
            if missing or (result.returncode == 0 and result.stdout.strip() == 'false'):
                pending.unlink(missing_ok=True)
            else:
                raise RuntimeError('Worker state uncertain; retain maintenance and inspect worker-pending.json')

    def configure_roles(self):
        with self.connection.cursor() as cursor:
            for credential in (self.runtime, self.migration):
                user = credential['username']
                cursor.execute('SELECT 1 FROM pg_roles WHERE rolname=%s', (user,))
                if not cursor.fetchone():
                    cursor.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE').format(
                        sql.Identifier(user), sql.Literal(credential['password'])))
                else:
                    cursor.execute(sql.SQL('ALTER ROLE {} PASSWORD {}').format(sql.Identifier(user), sql.Literal(credential['password'])))
            cursor.execute('REVOKE CREATE ON SCHEMA public FROM PUBLIC')
            cursor.execute('ALTER SCHEMA public OWNER TO moodle_migration')
            cursor.execute('GRANT CONNECT, TEMPORARY ON DATABASE moodle TO moodle_runtime, moodle_migration')
            cursor.execute('GRANT USAGE ON SCHEMA public TO moodle_runtime')

    def grants(self):
        # RDS's managed master is not a true PostgreSQL superuser and cannot
        # change another role's default privileges. Use the schema owner itself.
        owned = self.connect(self.migration)
        try:
            owned.autocommit = True
            with owned.cursor() as cursor:
                cursor.execute("SELECT c.relname,c.relkind FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND left(c.relname,4)='mdl_' AND c.relowner=(SELECT oid FROM pg_roles WHERE rolname=current_user)")
                objects = cursor.fetchall()
                for kinds, privileges, object_type in [
                    ({'r', 'p', 'v', 'm', 'f'}, 'SELECT, INSERT, UPDATE, DELETE', 'TABLE'),
                    # Moodle delete_records() uses TRUNCATE when no filter is supplied.
                    # Keep schema ownership/DDL with the migration role.
                    ({'r', 'p'}, 'TRUNCATE', 'TABLE'),
                    ({'S'}, 'USAGE, SELECT, UPDATE', 'SEQUENCE'),
                ]:
                    names = [sql.Identifier('public', name) for name, kind in objects if kind in kinds]
                    if names:
                        cursor.execute(sql.SQL('GRANT ' + privileges + ' ON ' + object_type + ' {} TO moodle_runtime').format(sql.SQL(',').join(names)))
                cursor.execute('ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE ON TABLES TO moodle_runtime')
                cursor.execute('ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO moodle_runtime')
        finally:
            owned.close()

    def apps(self):
        result = self.aws('ec2', 'describe-instances', '--filters',
                          'Name=tag:Name,Values=' + self.d['name'] + '-app',
                          'Name=instance-state-name,Values=pending,running,stopping,stopped')
        instances = [i for r in result['Reservations'] for i in r['Instances']]
        if any(i['State']['Name'] in ('pending', 'stopping') for i in instances):
            raise RuntimeError('App instance transition in progress: wait for ASG to settle and retry under maintenance')
        return [i['InstanceId'] for i in instances if i['State']['Name'] == 'running']

    def services(self, action):
        instances = self.apps()
        if not instances:
            return
        command = self.aws('ssm', 'send-command', '--instance-ids', *instances, '--document-name', 'AWS-RunShellScript',
                           '--parameters', json.dumps({'commands': [f'systemctl {action} moodle-web.service'], 'executionTimeout': ['180']}))['Command']['CommandId']
        deadline = time.monotonic() + 240
        remaining = set(instances)
        while remaining and time.monotonic() < deadline:
            for instance in list(remaining):
                # list-command-invocations tolerates eventual absence just after send-command.
                result = self.aws('ssm', 'list-command-invocations', '--command-id', command, '--instance-id', instance, '--details')
                invocations = result.get('CommandInvocations', [])
                if not invocations:
                    continue
                state = invocations[0]['Status']
                if state == 'Success':
                    remaining.remove(instance)
                elif state not in ('Pending', 'InProgress', 'Delayed'):
                    raise RuntimeError(f'App {action} failed: command {command}, instance {instance}, status {state}')
            if remaining:
                time.sleep(3)
        if remaining:
            raise RuntimeError(f'App {action} timed out; inspect SSM command {command}')
        if action == 'stop' and set(self.apps()) != set(instances):
            raise RuntimeError('App inventory changed while quiescing; leave maintenance active and retry')

    def block(self):
        (CONTROL / 'blocked').touch()
        os.chmod(CONTROL / 'blocked', 0o660)
        self.log('maintenance-enabled')
        self.services('stop')
        with self.connection.cursor() as cursor:
            cursor.execute('ALTER ROLE moodle_runtime NOLOGIN')
            cursor.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE usename = 'moodle_runtime' AND pid <> pg_backend_pid()")
        self.log('writers-stopped')

    def unblock(self):
        with self.connection.cursor() as cursor:
            cursor.execute('ALTER ROLE moodle_runtime LOGIN')
        self.services('start')
        # All processes start gated; publish after start commands have succeeded.
        (CONTROL / 'blocked').unlink(missing_ok=True)
        self.log('complete-check-health-and-LMS')

    def backup(self):
        # Caller already holds the operation lock and has quiesced every app writer.
        self.log('backup-started')
        stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S')
        with tempfile.TemporaryDirectory(prefix='moodle-backup-') as temp:
            directory = Path(temp)
            subprocess.run(['/usr/lib/postgresql/16/bin/pg_dump', '--format=custom', '--no-owner', '--no-acl', '--file', str(directory / 'database.dump')], env=self.env, check=True)
            subprocess.run(['tar', '--exclude=./.distribution', '--exclude=./muc', '--exclude=./cache', '--exclude=./localcache', '--exclude=./sessions',
                            '-czf', str(directory / 'moodledata.tar.gz'), '-C', str(DATA), '.'], check=True)
            active = read(CONTROL / 'active.json') if (CONTROL / 'active.json').exists() else {'release': None}
            manifest = {'format': 1, 'time': now(), 'source': self.d['name'], 'active': active,
                        'target_artifact': self.d['artifact'], 'wwwroot': self.d['wwwroot'],
                        'db_major': 16, 'moodle_version': '4.5.15', 'configuration': self.d,
                        'files': {n: digest(directory / n) for n in ('database.dump', 'moodledata.tar.gz')}}
            write(directory / 'manifest.json', manifest)
            prefix = f"s3://{self.d['backup_bucket']}/{self.d['name']}/{stamp}"
            # Publish manifest LAST, so incomplete uploads are not valid restore points.
            for name in ('database.dump', 'moodledata.tar.gz', 'manifest.json'):
                subprocess.run(['aws', '--region', self.d['region'], 's3', 'cp', str(directory / name), prefix + '/' + name,
                                '--sse', 'AES256', '--only-show-errors'], check=True)
        self.metric('BackupSuccess')
        self.log('backup-uploaded:' + prefix)
        return prefix

    def release(self):
        if (CONTROL / 'migration-pending.json').exists():
            raise RuntimeError('Previous schema job failed/interrupted; inspect or restore before clearing migration-pending.json')
        active = read(CONTROL / 'active.json') if (CONTROL / 'active.json').exists() else None
        self.configure_roles()
        self.block()
        if active:
            self.backup()
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT to_regclass('public.mdl_config')")
            installed = bool(cursor.fetchone()[0])
            cursor.execute("SELECT count(*) FROM pg_tables WHERE schemaname='public'")
            table_count = cursor.fetchone()[0]
        if not installed and table_count:
            raise RuntimeError('Partial install found; inspect/restore before retrying')
        if installed:
            self.log('upgrade-started')
            write(CONTROL / 'migration-pending.json', {'release': self.d['artifact']['release'], 'step': 'upgrade', 'time': now()})
            self.php('/var/www/moodle/admin/cli/upgrade.php', '--non-interactive', migration=True)
        else:
            if not (ETC / 'admin.json').is_file():
                raise RuntimeError('Create /etc/moodle/admin.json privately (username/password/email), then retry release')
            self.log('install-started')
            write(CONTROL / 'migration-pending.json', {'release': self.d['artifact']['release'], 'step': 'install', 'time': now()})
            self.php('/opt/moodle-medium/install.php', migration=True)
        (CONTROL / 'migration-pending.json').unlink()
        self.grants()
        self.php('/opt/moodle-medium/muc.php', migration=True)
        self.php('/var/www/moodle/admin/cli/purge_caches.php', migration=True)
        self.php('/opt/moodle-medium/tls-proof.php', migration=True)
        write(CONTROL / 'active.json', {'release': self.d['artifact']['release'], 'artifact': self.d['artifact'], 'time': now()})
        self.unblock()

    def restore(self, prefix):
        # Only restore into a NEW empty medium environment. No in-place destructive restore.
        if any(p.name != '.distribution' for p in DATA.iterdir()):
            raise RuntimeError('Restore requires a fresh empty target EFS data directory')
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM pg_tables WHERE schemaname='public'")
            if cursor.fetchone()[0] or (CONTROL / 'active.json').exists():
                raise RuntimeError('Restore requires a fresh empty target database/site')
        allowed_sources = {self.d['name'], self.d.get('restore_source_prefix', '')} - {''}
        if not any(prefix.startswith(f"s3://{self.d['backup_bucket']}/{source}/") for source in allowed_sources) or '..' in prefix:
            raise RuntimeError('Restore prefix must be inside an explicitly allowed site prefix')
        self.configure_roles()
        self.block()
        self.log('restore-started')
        with tempfile.TemporaryDirectory(prefix='moodle-restore-') as temp:
            directory = Path(temp)
            for name in ('manifest.json', 'database.dump', 'moodledata.tar.gz'):
                subprocess.run(['aws', '--region', self.d['region'], 's3', 'cp', prefix.rstrip('/') + '/' + name, str(directory / name), '--only-show-errors'], check=True)
            manifest = read(directory / 'manifest.json')
            source_artifact = manifest['active'].get('artifact')
            if (manifest['format'] != 1 or manifest['db_major'] != 16 or not source_artifact
                    or source_artifact['image'] != self.d['artifact']['image']
                    or source_artifact['release'] != self.d['artifact']['release']):
                raise RuntimeError('Restore must first use the exact source artifact and compatible DB major')
            for name in ('database.dump', 'moodledata.tar.gz'):
                if manifest['files'].get(name) != digest(directory / name):
                    raise RuntimeError('Backup checksum mismatch')
            subprocess.run(['/usr/lib/postgresql/16/bin/pg_restore', '--exit-on-error', '--no-owner', '--no-acl', '--dbname', self.d['db_name'], str(directory / 'database.dump')], env=self.env, check=True)
            # tar cannot overwrite config.php: it is immutable inside the image, never in moodledata.
            import tarfile
            with tarfile.open(directory / 'moodledata.tar.gz', 'r:gz') as archive:
                members = archive.getmembers()
                from pathlib import PurePosixPath
                if any(PurePosixPath(m.name).parts and PurePosixPath(m.name).parts[0] == '.distribution' for m in members):
                    raise RuntimeError('Archive contains protected operation control files')
                archive.extractall(DATA, members=members, filter='data')
            # Rebuild MUC from target secrets/endpoints; never contact the source cache.
            if (DATA / 'muc').exists():
                shutil.rmtree(DATA / 'muc')
            self.grants()
            if manifest['wwwroot'] != self.d['wwwroot']:
                self.php('/var/www/moodle/admin/tool/replace/cli/replace.php', '--search=' + manifest['wwwroot'],
                         '--replace=' + self.d['wwwroot'], '--non-interactive', migration=True)
            self.php('/opt/moodle-medium/muc.php', migration=True)
            self.php('/var/www/moodle/admin/cli/purge_caches.php', migration=True)
            write(CONTROL / 'active.json', {'release': self.d['artifact']['release'], 'artifact': self.d['artifact'], 'restored_from': prefix, 'time': now()})
        # Leave maintenance enabled until operator checks hashes/fixtures on the new target.
        self.log('restore-loaded-maintenance-retained-run-resume-after-review')

    def cron(self):
        if (CONTROL / 'blocked').exists() or not (CONTROL / 'active.json').exists():
            self.log('cron-skipped-site-not-active')
            return
        if read(CONTROL / 'active.json')['release'] != self.d['artifact']['release']:
            raise RuntimeError('Runner artifact is incompatible with active release')
        self.php('/var/www/moodle/admin/cli/cron.php')
        self.php('/opt/moodle-medium/cron-audit.php')
        self.metric('CronSuccess')
        self.log('cron-completed-and-task-audit-clear')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['release', 'backup', 'restore', 'resume', 'cron'])
    parser.add_argument('--prefix')
    parser.add_argument('--confirm', help='resume requires the full site name after recovery review')
    args = parser.parse_args()
    operation = None
    try:
        with ExitStack() as resources:
            if args.operation == 'backup':
                resources.enter_context(backup_window())
            operation = Operations(args.operation)
            # Release the DB lock before allowing the cron timer to fire again.
            resources.callback(operation.connection.close)
            if args.operation == 'release':
                operation.release()
            elif args.operation == 'backup':
                if not (CONTROL / 'active.json').exists() or (CONTROL / 'blocked').exists():
                    raise RuntimeError('Scheduled backup requires an active, unblocked release')
                operation.block()
                operation.backup()
                operation.unblock()
            elif args.operation == 'restore':
                if not args.prefix:
                    parser.error('restore requires --prefix s3://bucket/source/backup-id')
                operation.restore(args.prefix)
            elif args.operation == 'resume':
                if args.confirm != operation.d['name']:
                    raise RuntimeError('resume requires --confirm ' + operation.d['name'] + ' after reviewing restore/recovery')
                if (CONTROL / 'migration-pending.json').exists():
                    raise RuntimeError('Unresolved migration; recover before resuming')
                if read(CONTROL / 'active.json')['release'] != operation.d['artifact']['release']:
                    raise RuntimeError('Active release mismatch; inspect or restore before resuming')
                operation.grants()
                operation.unblock()
            else:
                operation.cron()
    except Exception as exc:
        # Do not print database connection exceptions containing credentials.
        print(f'Operation failed ({type(exc).__name__}); inspect private runner logs/state; maintenance was not cleared automatically.', file=sys.stderr)
        if operation:
            operation.log('failed-needs-intervention:' + type(exc).__name__)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
