#!/usr/bin/env bash
set -Eeuo pipefail
umask 027
source /etc/os-release
[[ "$ID" == ubuntu && "$VERSION_ID" == 26.04 && "$(uname -m)" == x86_64 ]] || { echo 'Expected the Ubuntu 26.04 amd64 baseline.' >&2; exit 1; }
cd /opt/moodle-medium
for command in docker aws mount.efs python3 /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl; do
  command -v "$command" >/dev/null || { echo "Prepared AMI missing: $command" >&2; exit 1; }
done
python3 -c 'import psycopg2'
install -d -m 0750 -o root -g www-data /etc/moodle
chown root:www-data /etc/moodle/deploy.json
chmod 0640 /etc/moodle/deploy.json
readarray -t config < <(python3 -c 'import json; d=json.load(open("/etc/moodle/deploy.json")); print("\n".join([d["region"],d["artifact"]["image"],d["artifact"]["release"],d["efs_id"],d["access_point"],d["role"]]))')
region=${config[0]}; image=${config[1]}; release=${config[2]}; efs=${config[3]}; accesspoint=${config[4]}; role=${config[5]}
aws --region "$region" ecr get-login-password | docker login --username AWS --password-stdin "${image%%/*}"
docker pull "$image"
[[ "$(docker image inspect --format '{{index .Config.Labels "org.opencontainers.image.revision"}}' "$image")" == "$release" ]] || { echo 'Artifact release label mismatch.' >&2; exit 1; }
docker logout "${image%%/*}"
ca_container=$(docker create "$image")
trap 'docker rm "$ca_container" >/dev/null' EXIT
docker cp "$ca_container:/etc/ssl/certs/rds-global.pem" /etc/moodle/rds-global.pem
chmod 0644 /etc/moodle/rds-global.pem
python3 refresh-config.py
if ! mountpoint -q /var/lib/moodledata; then
  install -d -m 000 /var/lib/moodledata
fi
entry="$efs:/ /var/lib/moodledata efs _netdev,tls,iam,accesspoint=$accesspoint,noresvport 0 0"
grep -Fqx "$entry" /etc/fstab || printf '%s\n' "$entry" >>/etc/fstab
mountpoint -q /var/lib/moodledata || mount /var/lib/moodledata
mountpoint -q /var/lib/moodledata
install -d -m 0770 -o 33 -g 33 /var/cache/moodle
mkdir -p /var/lib/moodledata/.distribution
touch /etc/moodle/mount-ok
chmod 0644 /etc/moodle/mount-ok
cat >/etc/systemd/system/moodle-web.service <<'UNIT'
[Unit]
Description=Immutable Moodle medium app
After=docker.service network-online.target
Requires=docker.service
RequiresMountsFor=/var/lib/moodledata
[Service]
ExecStart=/opt/moodle-medium/container.sh web
ExecStop=/usr/bin/docker stop -t 120 moodle-medium-web
Restart=on-failure
RestartSec=10
TimeoutStopSec=150
[Install]
WantedBy=multi-user.target
UNIT
cat >/etc/systemd/system/moodle-cron.service <<'UNIT'
[Unit]
Description=Moodle medium runner cron with cluster operation lock
After=docker.service network-online.target
RequiresMountsFor=/var/lib/moodledata
[Service]
Type=oneshot
ExecStart=/opt/moodle-medium/operation.sh cron
TimeoutStartSec=3500
UNIT
cat >/etc/systemd/system/moodle-cron.timer <<'UNIT'
[Unit]
Description=Moodle medium cron schedule (runner only)
[Timer]
OnBootSec=2min
OnUnitActiveSec=1min
Persistent=true
[Install]
WantedBy=timers.target
UNIT
cat >/etc/systemd/system/moodle-backup.service <<'UNIT'
[Unit]
Description=Consistent Moodle medium backup
RequiresMountsFor=/var/lib/moodledata
[Service]
Type=oneshot
ExecStart=/opt/moodle-medium/operation.sh backup
TimeoutStartSec=7200
UNIT
cat >/etc/systemd/system/moodle-backup.timer <<'UNIT'
[Timer]
OnCalendar=*-*-* 02:00:00 UTC
Persistent=true
[Install]
WantedBy=timers.target
UNIT
python3 /opt/moodle-medium/observability.py
systemctl daemon-reload
if [[ "$role" == runner ]]; then
  systemctl disable --now moodle-web.service
  systemctl enable --now moodle-cron.timer moodle-backup.timer
else
  systemctl disable --now moodle-cron.timer moodle-backup.timer
  systemctl enable --now moodle-web.service
fi
