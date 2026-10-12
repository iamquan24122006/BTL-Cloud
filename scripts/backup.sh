#!/usr/bin/env bash
# Single-node only. Never use unchanged on a multi-node deployment.
set -Eeuo pipefail
umask 077
[[ $EUID -eq 0 ]] || { echo 'Run as root.' >&2; exit 1; }
test -f /var/lib/moodle-distribution/installed
exec 9>/run/moodle-backup.lock
flock -n 9 || { echo 'Another backup is running.' >&2; exit 1; }
systemctl is-active --quiet moodle-web.service || { echo 'Moodle web must be running before backup.' >&2; exit 1; }
systemctl is-active --quiet moodle-cron.timer || { echo 'Cron timer must be running before backup.' >&2; exit 1; }
maintenance=$(/opt/moodle-distribution/php-cli.sh -r 'define("CLI_SCRIPT", true); require "/var/www/moodle/config.php"; echo empty($CFG->maintenance_enabled) ? "0" : "1";')
[[ "$maintenance" == 0 || -z "$maintenance" ]] || { echo 'Site is already in maintenance; finish that operation first.' >&2; exit 1; }
destination="/var/backups/moodle/$(date -u +%Y%m%dT%H%M%SZ)"
install -d -m 0700 /var/backups/moodle
mkdir -m 0700 "$destination"
resume() {
  local status=$?
  trap - EXIT
  # Restore availability on success AND error. Flag recovery failures explicitly.
  /opt/moodle-distribution/php-cli.sh /var/www/moodle/admin/cli/maintenance.php --disable || status=1
  systemctl start moodle-web.service || status=1
  systemctl start moodle-cron.timer || status=1
  if (( status != 0 )); then echo 'Backup/recovery failed; inspect services and logs. Do not treat this backup as verified.' >&2; fi
  exit "$status"
}
trap resume EXIT
/opt/moodle-distribution/php-cli.sh /var/www/moodle/admin/cli/maintenance.php --enable
systemctl stop moodle-cron.timer
# Let an existing cron finish rather than killing a file-writing task mid-way.
deadline=$((SECONDS + 900))
while :; do
  # A running Type=oneshot is usually 'activating', not 'active'.
  cron_state=$(systemctl show moodle-cron.service --property=ActiveState --value)
  case "$cron_state" in inactive|failed) break ;; esac
  (( SECONDS < deadline )) || { echo 'Cron did not drain within 15 minutes.' >&2; exit 1; }
  sleep 2
done
systemctl stop moodle-web.service
runuser -u postgres -- /usr/lib/postgresql/16/bin/pg_dump --format=custom --no-owner moodle >"$destination/database.dump"
tar -C /var/lib/moodledata --exclude='./cache' --exclude='./localcache' --exclude='./temp' \
  --exclude='./sessions' -czf "$destination/moodledata.tar.gz" .
cp /var/www/moodle/config.php "$destination/config.php"
git -C /var/www/moodle rev-parse HEAD >"$destination/code.txt"
cp /var/lib/moodle-distribution/php-image-id "$destination/runtime-image.txt"
cp /opt/moodle-distribution/Dockerfile "$destination/runtime-Dockerfile"
(
  cd "$destination"
  sha256sum database.dump moodledata.tar.gz config.php code.txt runtime-image.txt runtime-Dockerfile >SHA256SUMS
)
python3 - "$destination" <<'PY'
import datetime, json, sys
from pathlib import Path
out = Path(sys.argv[1])
deploy = json.loads(Path('/etc/moodle/deploy.json').read_text())
(out / 'manifest.json').write_text(json.dumps({
    'format': 2, 'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'moodle_version': deploy['moodle_version'], 'database': 'PostgreSQL 16',
    'host_os': 'Ubuntu 26.04', 'php': '8.3 (container)',
    'consistency': 'single node, web stopped, cron drained',
    'files': ['database.dump', 'moodledata.tar.gz', 'config.php', 'code.txt',
              'runtime-image.txt', 'runtime-Dockerfile', 'SHA256SUMS'],
    'restore_tested': False
}, indent=2))
PY
# Resume users before the network upload; a second resume in the EXIT trap is safe.
/opt/moodle-distribution/php-cli.sh /var/www/moodle/admin/cli/maintenance.php --disable
systemctl start moodle-web.service moodle-cron.timer
bucket=$(python3 -c "import json; print(json.load(open('/etc/moodle/deploy.json'))['backup_bucket'])")
prefix=$(python3 -c "import json; print(json.load(open('/etc/moodle/deploy.json'))['backup_prefix'])")
region=$(python3 -c "import json; print(json.load(open('/etc/moodle/deploy.json'))['region'])")
if [[ -n "$bucket" ]]; then
  target="s3://$bucket/$prefix/$(basename "$destination")"
  # Manifest is the last object: its presence marks a completed upload set.
  for filename in database.dump moodledata.tar.gz config.php code.txt runtime-image.txt runtime-Dockerfile SHA256SUMS manifest.json; do
    aws --region "$region" s3 cp "$destination/$filename" "$target/$filename" --sse AES256 --only-show-errors
  done
  echo "Backup uploaded: $target ; restore has NOT been tested."
else
  echo "Local backup only: $destination ; lost on EC2 destruction."
fi
echo 'Backup files contain private data. Retention and restore procedure: docs/05-operations.md.'
