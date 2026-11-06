#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
mountpoint -q /var/lib/moodledata || { echo 'EFS is not mounted.' >&2; exit 1; }
exec python3 /opt/moodle-medium/operations.py "$@"
