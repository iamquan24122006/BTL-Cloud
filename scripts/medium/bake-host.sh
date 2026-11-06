#!/usr/bin/env bash
# One-time image builder using official, checksum-pinned Ubuntu packages.
set -Eeuo pipefail
umask 027
source /etc/os-release
[[ "$ID" == ubuntu && "$VERSION_ID" == 26.04 && "$(uname -m)" == x86_64 ]]
export DEBIAN_FRONTEND=noninteractive
cd /opt/moodle-builder
readarray -t pin < <(python3 -c 'import json; d=json.load(open("bake.json")); print("\n".join(d[k] for k in ["awscli_version","awscli_sha256","cloudwatch_url","cloudwatch_sha256","efs_version","efs_commit","efs_deb_url","efs_deb_sha256"]))')
apt-get update
apt-get install -y ca-certificates curl gnupg docker.io python3 python3-psycopg2 unzip nfs-common
curl -fsSL --retry 3 "https://awscli.amazonaws.com/awscli-exe-linux-x86_64-${pin[0]}.zip" -o awscli.zip
printf '%s  awscli.zip\n' "${pin[1]}" | sha256sum -c -
unzip -q awscli.zip
./aws/install
curl -fsSL --retry 3 "${pin[2]}" -o cloudwatch.deb
printf '%s  cloudwatch.deb\n' "${pin[3]}" | sha256sum -c -
apt-get install -y /opt/moodle-builder/cloudwatch.deb
curl -fsSL --retry 3 "${pin[6]}" -o efs.deb
printf '%s  efs.deb\n' "${pin[7]}" | sha256sum -c -
[[ "$(dpkg-deb -f efs.deb Version)" == "${pin[4]#v}-1" ]]
apt-get install -y /opt/moodle-builder/efs.deb
curl -fsSL --retry 3 https://www.postgresql.org/media/keys/ACCC4CF8.asc -o pgdg.asc
[[ "$(gpg --batch --show-keys --with-colons pgdg.asc | awk -F: '$1=="fpr" {print $10;exit}')" == B97B0AFCAA1A47F044F244A07FCC7D46ACCC4CF8 ]]
install -m 0644 pgdg.asc /usr/share/keyrings/moodle-pgdg.asc
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
systemctl enable --now docker
command -v mount.efs
aws --version
python3 -c 'import psycopg2'
/usr/lib/postgresql/16/bin/pg_dump --version
install -d -m 0755 /var/lib/moodle-distribution
dpkg-query -W docker.io python3 python3-psycopg2 postgresql-client-16 amazon-efs-utils amazon-cloudwatch-agent \
  >/var/lib/moodle-distribution/medium-package-versions.txt
cp bake.json /var/lib/moodle-distribution/medium-build-pins.json
touch /var/lib/moodle-distribution/medium-ami-ready
echo 'MEDIUM_AMI_BUILD_COMPLETE'
