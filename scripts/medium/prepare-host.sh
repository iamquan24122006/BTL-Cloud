#!/usr/bin/env bash
# Run on a CLEAN Ubuntu 26.04 amd64 builder EC2, then capture a private AMI.
# Supply reviewed, prebuilt efs-utils and CloudWatch agent packages plus SHA256.
# Building those upstream packages is separate from app-node bootstrap.
set -Eeuo pipefail
[[ $EUID == 0 && $# == 4 ]] || { echo 'Usage: sudo prepare-host.sh efs-utils.deb SHA256 cloudwatch-agent.deb SHA256' >&2; exit 2; }
source /etc/os-release
[[ "$ID" == ubuntu && "$VERSION_ID" == 26.04 && "$(uname -m)" == x86_64 ]] || { echo 'Expected Ubuntu 26.04 amd64.' >&2; exit 1; }
printf '%s  %s\n' "$2" "$1" "$4" "$3" | sha256sum -c -
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates curl gnupg docker.io python3 python3-psycopg2 unzip nfs-common
apt-get install -y "$1" "$3"
keyfile=$(mktemp)
trap 'rm -f -- "$keyfile"' EXIT
curl -fsSL --retry 3 https://www.postgresql.org/media/keys/ACCC4CF8.asc -o "$keyfile"
fingerprint=$(gpg --batch --show-keys --with-colons "$keyfile" | awk -F: '$1 == "fpr" {print $10; exit}')
[[ "$fingerprint" == B97B0AFCAA1A47F044F244A07FCC7D46ACCC4CF8 ]]
install -m 0644 "$keyfile" /usr/share/keyrings/moodle-pgdg.asc
cat >/etc/apt/sources.list.d/moodle-pgdg.sources <<'APT'
Types: deb
URIs: https://apt.postgresql.org/pub/repos/apt
Suites: resolute-pgdg
Components: main
Architectures: amd64
Signed-By: /usr/share/keyrings/moodle-pgdg.asc
APT
apt-get update
apt-get install -y postgresql-client-16
if ! command -v aws >/dev/null; then
  echo 'Install a reviewed/pinned AWS CLI v2 package before capturing the AMI.' >&2
  exit 1
fi
command -v mount.efs
python3 -c 'import psycopg2'
/usr/lib/postgresql/16/bin/pg_dump --version
systemctl enable --now docker
if systemctl list-unit-files amazon-ssm-agent.service --no-legend | grep -q amazon-ssm-agent; then
  systemctl enable --now amazon-ssm-agent
else
  systemctl is-active --quiet snap.amazon-ssm-agent.amazon-ssm-agent.service
fi
install -d -m 0755 /var/lib/moodle-distribution
printf 'ubuntu=26.04\nphp=container-8.3\npostgres-client=16\n' >/var/lib/moodle-distribution/medium-ami-baseline
echo 'Builder dependencies installed. Record package versions and AMI ID; remove builder credentials/history before capture.'
