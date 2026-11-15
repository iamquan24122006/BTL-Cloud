# Small load measurement

Generate plans with `python -m scripts.make_small_workload`. The logical workload is 60% course, 20% file download, 10% assignment view and 10% logout/login cycle, with 3–8 seconds think time. Auth cycles generate several HTTP samples. Virtual users have independent accounts/cookies; connections are fresh, HTTP retries disabled. Submission writes and browser layout are checked separately.

## Private fixture

SSM measurements include laptop and tunnel behavior. Keep their results separate from the private VPC experiment.

`infra/` provisions a dedicated `t3.small` generator, encrypted 20 GiB volume, SSM role, generator SG without ingress, and a temporary SG attachment on the selected staging ENI. The bridge SG permits only TCP 8081 from the generator SG. The existing staging SG remains unchanged. [AWS documents SG references as private-IP communication between associated interfaces.](https://docs.aws.amazon.com/vpc/latest/userguide/security-group-rules.html)

Supply region, expected account, AMI, staging subnet/ENI, the exact private users CSV ARN and a unique results-prefix ARN in a private variable file. Keep this fixture in separate Terraform state. Review the plan before apply. Its role can read the CSV and its own run prefix, and write only its run prefix; no backup deletion or bucket listing is granted. Mock-provider tests do not call AWS.

## Preserve the lab URL

For Moodle's `http://localhost:8080` wwwroot, use `scripts/tcp_bridge.py` on the two hosts:

- Staging binds its private IP:8081 and forwards to 127.0.0.1:8080, allowing only the generator's private IP.
- Generator binds 127.0.0.1:8080 and forwards to the staging private IP:8081, allowing only 127.0.0.1.

Run the relays as unprivileged systemd services with `--lifetime 10000` and `RuntimeMaxSec=10800s`. They reject unlisted peers, bound connection counts/time and do not log HTTP payloads. Tests verify half-close response delivery and peer rejection.

Install Java 21 and JMeter 5.6.3 on the dedicated generator. Verify the archive against the [Apache SHA-512 file](https://archive.apache.org/dist/jmeter/binaries/apache-jmeter-5.6.3.tgz.sha512). Record Java version and source hashes. Download the synthetic CSV directly from private S3 using the role, store mode 0600, and pass only its path to JMeter.

## Runner and evidence

Prepare `/opt/moodle-load` with `apache-jmeter-5.6.3/`, the repo's scripts package, `tests/load/moodle-small.jmx`, `manifest.json`, `config.properties`, and `private/users.csv`. Properties select localhost:8080, the fixture course/file/assignment and CSV path. Disable response bodies, sampler data, headers and URL output.

Run `bash scripts/run_small_matrix.sh /opt/moodle-load <private-s3-run-prefix> <region>` as root. It runs a 2-user smoke and three repetitions each at 10/25/50 users, checks duration, user count and business assertions, records generator vmstat and uploads JTLs/summaries to a new private subdirectory per attempt. Uploads use individual copies, matching the prefix-only IAM policy. JMeter/console logs remain private on the generator. Failed runs stop escalation.

Summary `passed` refers to assertions, users and duration; assess research latency/error thresholds separately. Record target OS/DB metrics, generator metrics and CPU credits before/after. Note dataset, code and cache conditions.

The two-user smoke uses `-Jsmoke=true` to cycle course, download, assignment view and auth in order. This prevents a short random run from missing an entire branch. Summarize it with `--smoke`; exclude it from the 60/20/10/10 workload comparisons. Measurements at 10/25/50 users keep random selection (`-Jsmoke=false`). Summary `failure_reasons` distinguishes missing transactions from HTTP/assertion failures, duration and user-count failures.

## Cleanup

Download evidence, stop the staging relay, and verify Moodle health/acceptance. Review and apply a destroy plan for only the fixture state. Confirm the original staging SG set is restored and generator/role/profile/fixture SGs are gone. Keep user CSV, raw logs, state and plans out of Git.
