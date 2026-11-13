#!/usr/bin/env bash
# Run only on the dedicated private load generator. CSV credentials stay local.
set -Eeuo pipefail
umask 077
[[ $EUID -eq 0 && $# -eq 3 ]] || { echo 'Usage (root): run_small_matrix.sh ROOT PRIVATE_S3_PREFIX REGION' >&2; exit 2; }
root=$(readlink -f -- "$1")
uri=$2
region=$3
[[ $uri =~ ^s3://[a-z0-9.-]+/[A-Za-z0-9/_-]+/?$ ]] || exit 2
[[ $region =~ ^[a-z]{2}-[a-z]+-[0-9]+$ ]] || exit 2
test -f "$root/private/users.csv"
test -f "$root/tests/load/moodle-small.jmx"
exec 9>/run/moodle-load-matrix.lock
flock -n 9 || { echo 'A load matrix is already running' >&2; exit 1; }
cd "$root"
stamp=$(date -u +%Y%m%dT%H%M%SZ)
results="$root/results/matrix-$stamp"
destination="${uri%/}/results/$stamp/"
mkdir -p -m 0700 "$root/results"
mkdir -m 0700 "$results"
monitor=''
final_status=failed

event() {
  python3 - "$results/progress.jsonl" "$1" "$2" <<'PY'
import datetime as dt,json,sys
with open(sys.argv[1], 'a') as stream:
    stream.write(json.dumps({'utc':dt.datetime.now(dt.timezone.utc).isoformat(), 'run':sys.argv[2], 'status':sys.argv[3]})+'\n')
PY
}
upload() {
  while IFS= read -r -d '' file; do
    case "$file" in *-jmeter.log|*-console.log) continue ;; esac
    aws --region "$region" s3 cp "$file" "$destination${file##*/}" --sse AES256 --only-show-errors
  done < <(find "$results" -maxdepth 1 -type f -print0)
}
finish() {
  code=$?
  trap - EXIT
  if [[ -n $monitor ]]; then kill "$monitor" 2>/dev/null || true; wait "$monitor" 2>/dev/null || true; fi
  event matrix "$final_status"
  upload || code=1
  echo "MATRIX $final_status exit=$code"
  exit "$code"
}
trap finish EXIT
java -version >"$results/java-version.txt" 2>&1
cp manifest.json "$results/tooling-manifest.json"
vmstat -w -t 15 >"$results/generator-vmstat.log" &
monitor=$!
event matrix started
# Scheduler duration includes ramp; these values implement the documented windows.
for spec in '2:30:150:1' '10:120:720:1' '10:120:720:2' '10:120:720:3' \
            '25:180:780:1' '25:180:780:2' '25:180:780:3' \
            '50:300:1200:1' '50:300:1200:2' '50:300:1200:3'; do
  IFS=: read -r users ramp duration repeat <<<"$spec"
  name="users-${users}-r${repeat}"
  prefix="$results/$name"
  test ! -e "$prefix.jtl"
  event "$name" started
  echo "START $name $(date -u +%FT%TZ)"
  java_code=0
  timeout --signal=TERM --kill-after=30s "$((duration + 150))s" \
    java -Xms256m -Xmx768m -jar apache-jmeter-5.6.3/bin/ApacheJMeter.jar \
      -n -t tests/load/moodle-small.jmx -q config.properties \
      "-Jusers=$users" "-Jramp=$ramp" "-Jduration=$duration" \
      -Jhttpclient4.retrycount=0 -Jjmeter.save.saveservice.print_field_names=true \
      -l "$prefix.jtl" -j "$prefix-jmeter.log" >"$prefix-console.log" 2>&1 || java_code=$?
  summary_code=0
  python3 -m scripts.summarize_jmeter "$prefix.jtl" --output "$prefix-summary.json" \
    --workload small --expected-users "$users" --minimum-seconds "$((duration - 10))" \
    --ramp-seconds "$ramp" >"$prefix-summary.log" 2>&1 || summary_code=$?
  if [[ $java_code -ne 0 || $summary_code -ne 0 ]]; then
    event "$name" failed
    echo "FAIL $name java=$java_code summary=$summary_code; stopping load escalation"
    exit 1
  fi
  event "$name" passed
  upload
  echo "PASS $name $(date -u +%FT%TZ)"
done
final_status=passed
