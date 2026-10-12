#!/usr/bin/env bash
set -Eeuo pipefail
# Host networking is intentional: Apache binds ONLY 127.0.0.1:8080; no -p mapping.
runtime_image=$(cat /var/lib/moodle-distribution/php-image-id)
exec docker run --rm --init --name moodle-web --network host \
  --security-opt no-new-privileges \
  --log-driver json-file --log-opt max-size=10m --log-opt max-file=3 \
  --mount type=bind,src=/var/www/moodle,dst=/var/www/moodle,readonly \
  --mount type=bind,src=/var/lib/moodledata,dst=/var/lib/moodledata \
  --mount type=bind,src=/var/cache/moodle,dst=/var/cache/moodle \
  "$runtime_image"
