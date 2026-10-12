#!/usr/bin/env bash
set -Eeuo pipefail
[[ $EUID -eq 0 ]] || { echo 'Run with sudo.' >&2; exit 1; }
test -f /var/lib/moodle-distribution/installed
source /etc/os-release
[[ "$ID" == ubuntu && "$VERSION_ID" == 26.04 ]]
systemctl is-active --quiet docker
systemctl is-active --quiet moodle-web.service
systemctl is-active --quiet postgresql@16-main
systemctl is-active --quiet moodle-cron.timer
# Type=simple becomes active before Docker has created the web container.
curl --fail --silent --show-error --max-time 30 --retry 20 --retry-connrefused --retry-delay 2 \
  http://localhost:8080/login/index.php >/dev/null
[[ "$(docker inspect --format '{{.State.Running}}' moodle-web)" == true ]]
[[ "$(docker inspect --format '{{.Image}}' moodle-web)" == "$(cat /var/lib/moodle-distribution/php-image-id)" ]]
/opt/moodle-distribution/php-cli.sh -r 'exit(PHP_MAJOR_VERSION === 8 && PHP_MINOR_VERSION === 3 && extension_loaded("sodium") && (int)ini_get("max_input_vars") >= 5000 ? 0 : 1);'
runuser -u www-data -- test -w /var/lib/moodledata
runuser -u www-data -- test -w /var/cache/moodle
if runuser -u www-data -- test -w /var/www/moodle/config.php; then
  echo 'FAIL: application user can write config.php.' >&2
  exit 1
fi
/opt/moodle-distribution/php-cli.sh -r 'define("CLI_SCRIPT", true); require "/var/www/moodle/config.php"; if (!$DB->record_exists("user", ["username" => "admin"]) || (int)$DB->get_field_sql("SHOW server_version_num") < 160000 || (int)$DB->get_field_sql("SHOW server_version_num") >= 170000) { exit(1); } if (!is_writable($CFG->dataroot) || !is_writable($CFG->localcachedir) || is_writable("/var/www/moodle/config.php")) { exit(1); } echo "Database, admin account and container file permissions: OK\n";'
echo 'Basic health: OK. Also verify login, upload, cron completion and restore as documented.'
