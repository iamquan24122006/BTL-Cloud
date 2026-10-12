#!/usr/bin/env bash
# Native dependencies for Ubuntu Server 26.04; PHP is deliberately containerized.
set -Eeuo pipefail
[[ $EUID -eq 0 ]] || { echo 'Run as root.' >&2; exit 1; }
source /etc/os-release
[[ "$ID" == ubuntu && "$VERSION_ID" == 26.04 ]] || { echo 'Ubuntu 26.04 required.' >&2; exit 1; }
[[ "$(dpkg --print-architecture)" == amd64 ]] || { echo 'This lab targets amd64.' >&2; exit 1; }
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y curl ca-certificates gnupg git unzip python3 awscli docker.io docker-buildx

# Trust only the PostgreSQL project's signing key, scoped to this repository.
keyfile=$(mktemp)
trap 'rm -f -- "$keyfile"' EXIT
curl --fail --silent --show-error --location --retry 3 \
  https://www.postgresql.org/media/keys/ACCC4CF8.asc -o "$keyfile"
fingerprint=$(gpg --batch --show-keys --with-colons "$keyfile" | awk -F: '$1 == "fpr" {print $10; exit}')
[[ "$fingerprint" == B97B0AFCAA1A47F044F244A07FCC7D46ACCC4CF8 ]] || { echo 'Unexpected PGDG signing key.' >&2; exit 1; }
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
apt-get install -y postgresql-16 postgresql-client-16
[[ "$(id -u www-data)" == 33 && "$(id -g www-data)" == 33 ]] || { echo 'Expected www-data UID/GID 33:33 for shared bind mounts.' >&2; exit 1; }
systemctl enable --now docker postgresql
docker version
/usr/lib/postgresql/16/bin/psql --version
