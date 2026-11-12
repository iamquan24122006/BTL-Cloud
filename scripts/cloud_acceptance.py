"""Run synthetic Moodle acceptance checks through SSM on an explicitly selected lab."""
from __future__ import annotations

import argparse
from base64 import b64encode
import datetime as dt
import json
from pathlib import Path
import re
import shlex
import sys
import uuid

from src import moodle_cloud as cli


def command_script(config, *, seed=False, fixture_uri=None):
    if config["size"] != "small":
        raise cli.ConfigError("cloud_acceptance supports small only; use scripts.acceptance for medium")
    source = b64encode((cli.ROOT / "tests/integration/moodle.php").read_bytes()).decode("ascii")
    commands = ["set -eu", "umask 077", "exec 9>/run/moodle-backup.lock", "flock -n 9",
                "test -f /var/lib/moodle-distribution/installed",
                "mkdir -p /opt/moodle-distribution", ": >/opt/moodle-distribution/acceptance.php.b64"]
    for index in range(0, len(source), 2048):
        commands.append("printf '%s' '" + source[index:index + 2048] + "' >>/opt/moodle-distribution/acceptance.php.b64")
    commands += ["base64 -d /opt/moodle-distribution/acceptance.php.b64 >/opt/moodle-distribution/acceptance.php",
                 "chmod 0644 /opt/moodle-distribution/acceptance.php"]
    if seed:
        # Passwords are generated remotely; neither argv nor SSM parameters contain them.
        commands += ["python3 - <<'PY'",
                     "import json, os, secrets", "from pathlib import Path",
                     "initial = Path('/root/moodle-initial-admin.txt').read_text()",
                     "password = next(line[len('password: '):] for line in initial.splitlines() if line.startswith('password: '))",
                     "settings = {name + 'pass': secrets.token_urlsafe(32) + '!aA7' for name in ('student','studentb','outsider','teacher')}",
                     "settings['adminpass'] = password",
                     "file = Path('/etc/moodle/acceptance.json')",
                     "if not file.exists():",
                     "    fd = os.open(file, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o640)",
                     "    with os.fdopen(fd, 'w') as out: json.dump(settings, out)",
                     "else:",
                     "    assert set(json.loads(file.read_text())) == set(settings), 'Unexpected acceptance settings'",
                     "os.chown(file, 0, 33)", "os.chmod(file, 0o640)", "PY",
                     "/opt/moodle-distribution/php-cli.sh /opt/moodle-distribution/acceptance.php seed"]
        if config["backup_bucket"]:
            uri = f"s3://{config['backup_bucket']}/{config['project']}-{config['environment']}/acceptance-fixture.json"
            commands.append(f"aws --region {config['region']} s3 cp /etc/moodle/acceptance.json {shlex.quote(uri)} --sse AES256 --only-show-errors")
    elif fixture_uri:
        expected = f"s3://{config['backup_bucket']}/{config['project']}-"
        if not fixture_uri.startswith(expected) or not re.fullmatch(r"s3://[a-z0-9.-]+/[a-z0-9-]+/acceptance-fixture\.json", fixture_uri):
            raise cli.ConfigError("fixture-uri must refer to this project's synthetic acceptance settings in its backup bucket")
        commands += [f"aws --region {config['region']} s3 cp {shlex.quote(fixture_uri)} /etc/moodle/acceptance.json --only-show-errors",
                     "chown root:www-data /etc/moodle/acceptance.json", "chmod 0640 /etc/moodle/acceptance.json"]
    commands += ["/opt/moodle-distribution/health.sh",
                 "/opt/moodle-distribution/php-cli.sh /opt/moodle-distribution/acceptance.php verify"]
    return "\n".join(commands)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--expected-account", required=True)
    parser.add_argument("--seed", action="store_true", help="Create synthetic courses/users/submissions on an empty lab")
    parser.add_argument("--confirm", required=True, help="Exact project-environment target")
    parser.add_argument("--fixture-uri", help="Read source synthetic credentials after restore; requires temporary S3 read rights")
    args = parser.parse_args(argv)
    try:
        config = cli.load_config(args.config)
        if config["size"] != "small":
            raise cli.ConfigError("cloud_acceptance supports small only; use scripts.acceptance for medium")
        expected = f"{config['project']}-{config['environment']}"
        if args.confirm != expected:
            raise cli.ConfigError("Target confirmation does not match configuration")
        if args.seed and args.fixture_uri:
            raise cli.ConfigError("Choose seeding or restored fixture settings, not both")
        if not re.fullmatch(r"\d{12}", args.expected_account):
            raise cli.ConfigError("expected-account must contain 12 digits")
        identity = cli.aws(config, "sts", "get-caller-identity")
        if identity["Account"] != args.expected_account:
            raise cli.ConfigError("AWS account does not match expected-account")
        instance = cli.instance_id(config)
        directory = cli.workspace(config) / "acceptance" / (dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8])
        directory.mkdir(parents=True)
        parameters = directory / "parameters.json"
        parameters.write_text(json.dumps({"commands": [command_script(config, seed=args.seed, fixture_uri=args.fixture_uri)],
                                          "executionTimeout": ["900"]}), encoding="utf-8")
        result = cli.aws(config, "ssm", "send-command", "--instance-ids", instance, "--document-name", "AWS-RunShellScript",
                         "--parameters", "file://" + str(parameters))
        command = result["Command"]["CommandId"]
        report = {"account": identity["Account"], "region": config["region"], "instance_id": instance,
                  "command_id": command, "status": "running", "source_fingerprint": cli.fingerprint(config),
                  "scope": "Synthetic courses, files, private submissions, grades, login/logout; no load or browser layout test"}
        (directory / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        try:
            invocation = cli.wait_command(config, command, instance, timeout=960)
            report.update(status="passed", response_code=invocation["ResponseCode"],
                          output=invocation.get("StandardOutputContent", ""))
        except cli.ConfigError as exc:
            report.update(status="failed", error=str(exc))
            try:
                invocation = cli.aws(config, "ssm", "get-command-invocation", "--command-id", command, "--instance-id", instance)
                (directory / "failed-invocation.json").write_text(json.dumps(invocation, indent=2), encoding="utf-8")
            except cli.ConfigError:
                pass
        report["finished_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
        (directory / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Cloud acceptance: {report['status']}. Evidence: {directory}")
        return 0 if report["status"] == "passed" else 1
    except (cli.ConfigError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
