#!/usr/bin/env bash
set -Eeuo pipefail
mountpoint -q /var/lib/moodledata || { echo 'EFS is not mounted.' >&2; exit 1; }
image=$(python3 -c 'import json; print(json.load(open("/etc/moodle/deploy.json"))["artifact"]["image"])')
common=(--rm --init --network host --security-opt no-new-privileges
  --mount type=bind,src=/etc/moodle,dst=/etc/moodle,readonly
  --mount type=bind,src=/var/lib/moodledata,dst=/var/lib/moodledata
  --mount type=bind,src=/var/cache/moodle,dst=/var/cache/moodle
  --tmpfs /tmp:rw,nosuid,nodev,size=256m)
if [[ "${1:-}" == web ]]; then
  exec docker run "${common[@]}" --name moodle-medium-web \
    --read-only --tmpfs /var/run/apache2:rw --tmpfs /var/lock/apache2:rw \
    --log-driver json-file --log-opt max-size=10m --log-opt max-file=3 \
    "$image" apache2-foreground
fi
if [[ -n "${MOODLE_CLI_NAME:-}" ]]; then common+=(--name "$MOODLE_CLI_NAME"); fi
exec docker run "${common[@]}" --user 33:33 --read-only --cap-drop ALL \
  --env "MOODLE_DB_ROLE=${MOODLE_DB_ROLE:-runtime}" --entrypoint php "$image" "$@"
