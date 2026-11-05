#!/usr/bin/env bash
# Single-node staging only. Never run unchanged on medium or a live source site.
set -Eeuo pipefail
umask 077
[[ $EUID -eq 0 ]] || { echo 'Run as root.' >&2; exit 1; }
[[ $# -eq 3 && "$2" == --confirm ]] || {
  echo 'Usage: restore.sh /absolute/backup-set --confirm PROJECT-staging' >&2; exit 1;
}
backup=$(realpath -e -- "$1")
[[ "$1" == /* && ! -L "$1" ]] || { echo 'Use an absolute, non-symlink backup directory.' >&2; exit 1; }
test -f /var/lib/moodle-distribution/installed
expected=$(python3 - <<'PY'
import json
from pathlib import Path
d = json.loads(Path('/etc/moodle/deploy.json').read_text())
assert d.get('environment') == 'staging', 'Automated restore is restricted to staging'
assert d['backup_prefix'] == d['project'] + '-staging'
print(d['backup_prefix'])
PY
)
[[ "$3" == "$expected" ]] || { echo 'Target confirmation does not match staging.' >&2; exit 1; }
exec 8>/run/moodle-provision.lock
flock -n 8 || { echo 'Provisioning is running.' >&2; exit 1; }
exec 9>/run/moodle-backup.lock
flock -n 9 || { echo 'Backup or restore is running.' >&2; exit 1; }
commit=$(git -C /var/www/moodle rev-parse HEAD)
python3 /opt/moodle-distribution/verify_backup.py "$backup" \
  --expected-commit "$commit" --expected-dockerfile /opt/moodle-distribution/Dockerfile
/usr/lib/postgresql/16/bin/pg_restore --list "$backup/database.dump" >/dev/null
# A verified set must remain immutable during the operation.
systemctl is-active --quiet moodle-web.service
systemctl is-active --quiet moodle-cron.timer
maintenance=$(/opt/moodle-distribution/php-cli.sh -r 'define("CLI_SCRIPT", true); require "/var/www/moodle/config.php"; echo empty($CFG->maintenance_enabled) ? "0" : "1";')
[[ "$maintenance" == 0 ]] || { echo 'Target is already in maintenance.' >&2; exit 1; }
stamp=$(date -u +%Y%m%dT%H%M%SZ)-$$
rollback="/var/backups/moodle/before-restore-$stamp"
newdata="/var/lib/moodledata.restore-$stamp"
mkdir -m 0700 "$newdata"
tar --no-same-owner --no-same-permissions -xzf "$backup/moodledata.tar.gz" -C "$newdata"
chown -R www-data:www-data "$newdata"
chmod 0770 "$newdata"
install -d -m 0700 "$rollback"
mutated=0
backup_timer=0
systemctl is-active --quiet moodle-backup.timer && backup_timer=1
recover() {
  local status=$?
  trap - EXIT
  if (( status != 0 )); then
    if (( mutated )); then
      printf '%s\n' "$rollback" >/var/lib/moodle-distribution/restore-failed
      systemctl stop moodle-web.service moodle-cron.timer || true
      echo "Restore failed. Web/cron remain stopped. Recovery data: $rollback" >&2
    else
      /opt/moodle-distribution/php-cli.sh /var/www/moodle/admin/cli/maintenance.php --disable || true
      systemctl start moodle-web.service moodle-cron.timer || true
      if (( backup_timer )); then systemctl start moodle-backup.timer || true; fi
    fi
  fi
  exit "$status"
}
trap recover EXIT
systemctl stop moodle-backup.timer moodle-cron.timer
deadline=$((SECONDS + 900))
while :; do
  cron_state=$(systemctl show moodle-cron.service --property=ActiveState --value)
  case "$cron_state" in inactive|failed) break ;; esac
  (( SECONDS < deadline )) || { echo 'Cron did not drain within 15 minutes.' >&2; exit 1; }
  sleep 2
done
/opt/moodle-distribution/php-cli.sh /var/www/moodle/admin/cli/maintenance.php --enable
systemctl stop moodle-web.service
runuser -u postgres -- /usr/lib/postgresql/16/bin/pg_dump --format=custom --no-owner moodle >"$rollback/database.dump"
cp /var/www/moodle/config.php "$rollback/config.php"
mutated=1
runuser -u postgres -- /usr/lib/postgresql/16/bin/dropdb moodle
runuser -u postgres -- /usr/lib/postgresql/16/bin/createdb --owner=moodle --encoding=UTF8 --template=template0 moodle
runuser -u postgres -- /usr/lib/postgresql/16/bin/pg_restore --exit-on-error --single-transaction \
  --no-owner --role=moodle --dbname=moodle <"$backup/database.dump"
mv /var/lib/moodledata "$rollback/moodledata"
mv "$newdata" /var/lib/moodledata
# Target config.php and its fresh DB password deliberately stay in place.
/opt/moodle-distribution/php-cli.sh /var/www/moodle/admin/cli/purge_caches.php
/opt/moodle-distribution/php-cli.sh /var/www/moodle/admin/cli/maintenance.php --disable
systemctl start moodle-web.service moodle-cron.timer
/opt/moodle-distribution/health.sh
rm -f /var/lib/moodle-distribution/restore-failed
echo "Restore completed on $expected. Verify login, course, submissions, grades and file hashes."
echo "Previous target data: $rollback. Backup timer remains stopped pending acceptance."
