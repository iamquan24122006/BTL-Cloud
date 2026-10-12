#!/usr/bin/env bash
# Ubuntu 26.04 only. Called by cloud-init or manually after deploy.json exists.
set -Eeuo pipefail
umask 027
[[ $EUID -eq 0 ]] || { echo 'Run as root.' >&2; exit 1; }
exec 9>/run/moodle-provision.lock
flock -n 9 || { echo 'Another provision is running.' >&2; exit 1; }
source /etc/os-release
[[ "$ID" == ubuntu && "$VERSION_ID" == 26.04 ]] || { echo 'Ubuntu 26.04 required.' >&2; exit 1; }
if [[ -f /var/lib/moodle-distribution/installed ]]; then
  echo 'Already installed; running health checks. Use the upgrade runbook for changes.'
  exec /opt/moodle-distribution/health.sh
fi
[[ -f /etc/moodle/deploy.json ]] || { echo 'Missing /etc/moodle/deploy.json.' >&2; exit 1; }
/opt/moodle-distribution/setup-host.sh
docker build --tag moodle-php:8.3 /opt/moodle-distribution
install -d -m 0750 /var/lib/moodle-distribution
docker image inspect --format '{{.Id}}' moodle-php:8.3 >/var/lib/moodle-distribution/php-image-id
install -d -m 0755 /var/www /opt/moodle-distribution
install -d -o root -g www-data -m 0750 /etc/moodle
install -d -o www-data -g www-data -m 0770 /var/lib/moodledata /var/cache/moodle

# Generate secrets ON THE INSTANCE. They never enter Terraform or EC2 user-data.
python3 - <<'PY'
import json, os, secrets
from pathlib import Path
settings = json.loads(Path('/etc/moodle/deploy.json').read_text())
assert settings['moodle_version'] == '4.5.15'
assert settings['wwwroot'] == 'http://localhost:8080'
secretfile = Path('/etc/moodle/bootstrap.json')
if not secretfile.exists():
    settings.update(dbpass=secrets.token_hex(32), adminpass=secrets.token_urlsafe(24) + '!aA7')
    fd = os.open(secretfile, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o640)
    with os.fdopen(fd, 'w') as stream:
        json.dump(settings, stream)
    admin = Path('/root/moodle-initial-admin.txt')
    admin.write_text('username: admin\npassword: ' + settings['adminpass'] + '\n')
    admin.chmod(0o600)
PY
chown root:www-data /etc/moodle/bootstrap.json
chmod 0640 /etc/moodle/bootstrap.json

# SQL receives only an internally generated hexadecimal password, via stdin.
systemctl enable --now postgresql
python3 - <<'PY' | runuser -u postgres -- psql -v ON_ERROR_STOP=1 --dbname=postgres
import json, re
from pathlib import Path
p = json.loads(Path('/etc/moodle/bootstrap.json').read_text())['dbpass']
assert re.fullmatch('[a-f0-9]{64}', p)
print("SELECT 'CREATE ROLE moodle LOGIN' WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname='moodle')\\gexec")
print("ALTER ROLE moodle WITH PASSWORD '" + p + "';")
print("SELECT 'CREATE DATABASE moodle OWNER moodle ENCODING ''UTF8'' TEMPLATE template0' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname='moodle')\\gexec")
PY

if [[ ! -d /var/www/moodle ]]; then
  git clone --depth 1 --branch v4.5.15 https://github.com/moodle/moodle.git /var/www/moodle
fi
[[ "$(git -C /var/www/moodle describe --tags --exact-match)" == v4.5.15 ]] || { echo 'Moodle source version mismatch.' >&2; exit 1; }
docker run --rm --network none --entrypoint php \
  --mount type=bind,src=/etc/moodle,dst=/etc/moodle,readonly \
  --mount type=bind,src=/var/www/moodle,dst=/var/www/moodle \
  --mount type=bind,src=/opt/moodle-distribution,dst=/opt/moodle-distribution,readonly \
  moodle-php:8.3 /opt/moodle-distribution/configure.php
chown -R root:www-data /var/www/moodle
find /var/www/moodle -type d -exec chmod 0750 {} +
find /var/www/moodle -type f -exec chmod 0640 {} +

# Idempotent after a completed DB install. Partial migrations deliberately fail,
# so an interrupted install must be investigated, not silently overwritten.
/opt/moodle-distribution/php-cli.sh /opt/moodle-distribution/install-db.php >/var/log/moodle-install.log 2>&1
chmod 0600 /var/log/moodle-install.log

cat >/etc/systemd/system/moodle-web.service <<'UNIT'
[Unit]
Description=Moodle Apache/PHP 8.3 container
After=docker.service postgresql.service
Requires=docker.service
[Service]
Type=simple
ExecStart=/opt/moodle-distribution/moodle-web.sh
ExecStop=-/usr/bin/docker stop --time 120 moodle-web
ExecStopPost=-/usr/bin/docker rm -f moodle-web
TimeoutStopSec=150
Restart=on-failure
RestartSec=5
[Install]
WantedBy=multi-user.target
UNIT
cat >/etc/systemd/system/moodle-cron.service <<'UNIT'
[Unit]
Description=Moodle scheduled tasks
After=docker.service postgresql.service
Requires=docker.service
[Service]
Type=oneshot
Environment=MOODLE_CLI_NAME=moodle-cron
ExecStart=/opt/moodle-distribution/php-cli.sh /var/www/moodle/admin/cli/cron.php
ExecStopPost=-/usr/bin/docker stop --time 120 moodle-cron
ExecStopPost=-/usr/bin/docker rm -f moodle-cron
TimeoutStartSec=infinity
TimeoutStopSec=150
UNIT
cat >/etc/systemd/system/moodle-cron.timer <<'UNIT'
[Unit]
Description=Run Moodle cron once per minute
[Timer]
OnBootSec=60s
OnUnitActiveSec=60s
AccuracySec=1s
[Install]
WantedBy=timers.target
UNIT
cat >/etc/systemd/system/moodle-backup.service <<'UNIT'
[Unit]
Description=Consistent Moodle backup with a short maintenance window
[Service]
Type=oneshot
ExecStart=/opt/moodle-distribution/backup.sh
TimeoutStartSec=2h
UNIT
cat >/etc/systemd/system/moodle-backup.timer <<'UNIT'
[Unit]
Description=Daily Moodle backup at 02:00 UTC
[Timer]
OnCalendar=*-*-* 02:00:00 UTC
Persistent=true
[Install]
WantedBy=timers.target
UNIT
systemctl daemon-reload
systemctl enable --now moodle-web.service moodle-cron.timer
if python3 -c "import json,sys; sys.exit(not bool(json.load(open('/etc/moodle/deploy.json'))['backup_bucket']))"; then
  systemctl enable --now moodle-backup.timer
fi
date -u +%FT%TZ >/var/lib/moodle-distribution/installed
rm -f -- /etc/moodle/bootstrap.json
/opt/moodle-distribution/health.sh
echo 'Moodle ready. Initial administrator credentials: /root/moodle-initial-admin.txt (read via SSM).'
