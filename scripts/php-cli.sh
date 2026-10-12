#!/usr/bin/env bash
# Run Moodle CLI as www-data inside the same PHP image as the web service.
set -Eeuo pipefail
options=(--rm --init --interactive --network host --user 33:33 --read-only
  --cap-drop ALL --security-opt no-new-privileges
  --tmpfs /tmp:rw,nosuid,nodev,size=128m
  --mount type=bind,src=/var/www/moodle,dst=/var/www/moodle,readonly
  --mount type=bind,src=/var/lib/moodledata,dst=/var/lib/moodledata
  --mount type=bind,src=/var/cache/moodle,dst=/var/cache/moodle
  --mount type=bind,src=/etc/moodle,dst=/etc/moodle,readonly
  --mount type=bind,src=/opt/moodle-distribution,dst=/opt/moodle-distribution,readonly
  --workdir /var/www/moodle --entrypoint php)
if [[ -t 0 && -t 1 ]]; then options+=(--tty); fi
if [[ -n "${MOODLE_CLI_NAME:-}" ]]; then options+=(--name "$MOODLE_CLI_NAME"); fi
runtime_image=$(cat /var/lib/moodle-distribution/php-image-id)
exec docker run "${options[@]}" "$runtime_image" "$@"
