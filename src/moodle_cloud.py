"""CLI for the small, SSM-only Moodle lab. No credentials in YAML or Terraform."""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import shlex
import subprocess
import sys
import time

import yaml

ROOT = Path(__file__).resolve().parents[1]
INFRA = ROOT / "infra" / "small"
VERSION = "0.2.0"


class ConfigError(ValueError):
    pass


class AwsError(ConfigError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


class UniqueLoader(yaml.SafeLoader):
    pass


def unique_mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str) or key in result:
            raise ConfigError("YAML keys must be unique strings")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def load_config(filename):
    try:
        data = yaml.load(Path(filename).read_text(encoding="utf-8"), Loader=UniqueLoader)
    except yaml.YAMLError as exc:
        raise ConfigError("Invalid YAML syntax") from exc
    if not isinstance(data, dict):
        raise ConfigError("Configuration must be a mapping")
    required = {"project", "environment", "region", "size", "instance_type", "volume_gib", "moodle_version", "wwwroot"}
    allowed = required | {"backup_bucket", "tags"}
    if required - data.keys():
        raise ConfigError("Missing keys: " + ", ".join(sorted(required - data.keys())))
    if data.keys() - allowed:
        raise ConfigError("Unknown keys are not accepted (including secrets)")
    if not isinstance(data["project"], str) or not re.fullmatch(r"[a-z][a-z0-9-]{2,23}", data["project"]):
        raise ConfigError("project: 3-24 lowercase letters, digits or hyphens; start with a letter")
    if data["environment"] not in ("dev", "staging"):
        raise ConfigError("This lab supports dev/staging only; production requires the extended architecture")
    if not isinstance(data["region"], str) or not re.fullmatch(r"[a-z]{2}-[a-z]+-\d", data["region"]):
        raise ConfigError("region must be a standard AWS commercial region name")
    if data["size"] != "small":
        raise ConfigError("Only small is implemented; medium/large are specified in docs/02-architecture.md")
    if data["instance_type"] not in ("t3.small", "t3.medium", "t3.large"):
        raise ConfigError("instance_type must be t3.small, t3.medium or t3.large (x86_64)")
    if type(data["volume_gib"]) is not int or not 20 <= data["volume_gib"] <= 200:
        raise ConfigError("volume_gib must be an integer between 20 and 200")
    if data["moodle_version"] != "4.5.15":
        raise ConfigError("This release is pinned to Moodle 4.5.15; upgrade code and compatibility checks together")
    if data["wwwroot"] != "http://localhost:8080":
        raise ConfigError("small uses SSM forwarding and wwwroot http://localhost:8080")
    bucket = data.setdefault("backup_bucket", "")
    if not isinstance(bucket, str) or (bucket and (not re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", bucket) or ".." in bucket)):
        raise ConfigError("backup_bucket must be empty or a valid S3 bucket name")
    try:
        ipaddress.ip_address(bucket)
    except ValueError:
        pass
    else:
        raise ConfigError("backup_bucket cannot be an IP address")
    tags = data.setdefault("tags", {})
    if not isinstance(tags, dict) or len(tags) > 20 or any(
        not isinstance(k, str) or not isinstance(v, str) or not k or len(k) > 128 or len(v) > 256
        or k.lower().startswith("aws:") or any(ord(c) < 32 for c in k + v)
        for k, v in tags.items()
    ):
        raise ConfigError("tags must contain up to 20 text key/value pairs without control characters")
    return data


def workspace(config):
    return ROOT / ".work" / f"{config['project']}-{config['environment']}"


def run(args, *, env=None, capture=False):
    # Argument arrays only: no shell interpolation from YAML.
    result = subprocess.run([str(a) for a in args], env=env, check=True, text=True,
                            encoding="utf-8", capture_output=capture)
    return result.stdout.strip() if capture else ""


def tf(config, *args, capture=False):
    env = os.environ.copy()
    env["TF_DATA_DIR"] = str(workspace(config) / "terraform-data")
    return run(["terraform", f"-chdir={INFRA}", *args], env=env, capture=capture)


def aws(config, *args):
    # Match run()'s UTF-8 decoder, including Unicode SSM/build output on Windows.
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["AWS_CLI_FILE_ENCODING"] = "UTF-8"
    try:
        output = run(["aws", "--region", config["region"], "--no-cli-pager", *args, "--output", "json"], env=env, capture=True)
        # Successful operations such as EC2 reboot and IAM delete have no body.
        # Do not report a parse failure that could prompt repeating a mutation.
        return json.loads(output) if output else {}
    except subprocess.CalledProcessError as exc:
        error = exc.stderr or "AWS CLI failed"
        match = re.search(r"An error occurred \(([^)]+)\)", error)
        raise AwsError(match[1] if match else "CLIError", error.strip()) from exc


def fingerprint(config):
    digest = hashlib.sha256(json.dumps(config, sort_keys=True).encode())
    files = sorted(INFRA.glob("*.tf")) + sorted((ROOT / "scripts").glob("*"))
    files += sorted((ROOT / "src").glob("*.py"))
    lockfile = INFRA / ".terraform.lock.hcl"
    if lockfile.exists():
        files.append(lockfile)
    for file in files:
        if file.is_file():
            digest.update(file.relative_to(ROOT).as_posix().encode())
            digest.update(file.read_bytes())
    return digest.hexdigest()


def render(config):
    work = workspace(config)
    work.mkdir(parents=True, exist_ok=True)
    file = work / "config.tfvars.json"
    file.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return file


def init(config):
    render(config)
    tf(config, "init", "-input=false", "-reconfigure", f"-backend-config=path={workspace(config) / 'terraform.tfstate'}")


def plan(config, destroy=False):
    work = workspace(config)
    work.mkdir(parents=True, exist_ok=True)
    mode = "destroy" if destroy else "apply"
    manifest = work / f"{mode}.json"
    # Even a failed identity check or init invalidates the previous plan approval.
    manifest.unlink(missing_ok=True)
    variables = render(config)
    identity = aws(config, "sts", "get-caller-identity")
    init(config)
    planfile = work / f"{mode}.tfplan"
    args = ["plan", "-input=false", "-lock-timeout=60s", f"-var-file={variables}", f"-out={planfile}"]
    if destroy:
        args.append("-destroy")
    tf(config, *args)
    review = summarize_plan(json.loads(tf(config, "show", "-json", planfile, capture=True)))
    (work / f"{mode}-review.json").write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")
    manifest.write_text(json.dumps({"fingerprint": fingerprint(config), "account": identity["Account"],
                                    "mode": mode, "review": review,
                                    "plan_sha256": hashlib.sha256(planfile.read_bytes()).hexdigest()}, indent=2), encoding="utf-8")
    print(json.dumps(review, indent=2))
    print(f"Saved {mode} plan for AWS account {identity['Account']}. Review the Terraform output before applying.")


def summarize_plan(payload):
    result = {"create": 0, "update": 0, "delete": 0, "replace": 0, "data_loss_risk": False, "resources": []}
    for resource in payload.get("resource_changes", []):
        if resource.get("mode") != "managed":
            continue
        actions = resource["change"]["actions"]
        if actions == ["no-op"]:
            continue
        for action in ("create", "update", "delete"):
            result[action] += int(action in actions)
        result["replace"] += int("create" in actions and "delete" in actions)
        if resource["type"] == "aws_instance" and "delete" in actions:
            result["data_loss_risk"] = True
        result["resources"].append({"address": resource["address"], "actions": actions})
    return result


def apply(config, confirmation, destroy=False, allow_data_loss=False):
    expected = f"{config['project']}-{config['environment']}"
    if confirmation != expected:
        raise ConfigError(f"Explicit confirmation required: --confirm {expected}")
    if destroy and not allow_data_loss:
        raise ConfigError("destroy removes EC2, database and local backups; restore-test an S3 backup first, then use --allow-data-loss")
    mode = "destroy" if destroy else "apply"
    work = workspace(config)
    try:
        manifest = json.loads((work / f"{mode}.json").read_text(encoding="utf-8"))
        planfile = work / f"{mode}.tfplan"
        plan_hash = hashlib.sha256(planfile.read_bytes()).hexdigest()
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise ConfigError(f"Run plan{' --destroy' if destroy else ''} first") from exc
    if manifest.get("mode") != mode or manifest.get("fingerprint") != fingerprint(config) or manifest.get("plan_sha256") != plan_hash:
        raise ConfigError("Configuration, source or saved plan changed; generate and review a new plan")
    if manifest.get("review", {}).get("data_loss_risk") and not allow_data_loss:
        raise ConfigError("Plan deletes/replaces the small EC2 and its database/files; verify an external backup, then use --allow-data-loss")
    identity = aws(config, "sts", "get-caller-identity")
    if manifest.get("account") != identity["Account"]:
        raise ConfigError("AWS account changed since plan; refusing to apply")
    # Single use even when interrupted or failed: partial apply requires a new plan.
    (work / f"{mode}.json").unlink()
    tf(config, "apply", "-input=false", "-lock-timeout=60s", planfile)
    print("Infrastructure operation finished. Check cloud-init and Moodle health separately.")


def outputs(config):
    return json.loads(tf(config, "output", "-json", capture=True))


def instance_id(config):
    result = outputs(config)
    if "instance_id" not in result:
        raise ConfigError("No instance in Terraform state; deploy small first")
    return result["instance_id"]["value"]


def wait_command(config, command, instance, timeout=3900, interval=5):
    deadline = time.monotonic() + timeout
    while True:
        try:
            invocation = aws(config, "ssm", "get-command-invocation", "--command-id", command,
                             "--instance-id", instance)
        except AwsError as exc:
            if exc.code != "InvocationDoesNotExist":
                raise
            invocation = {"Status": "Pending"}
        status = invocation["Status"]
        if status == "Success":
            if invocation.get("ResponseCode") != 0:
                raise ConfigError("SSM returned Success without a zero response code")
            print(invocation.get("StandardOutputContent", ""))
            return invocation
        if status not in ("Pending", "InProgress", "Delayed", "Cancelling"):
            raise ConfigError(f"SSM command {command} ended with {status}; "
                              + invocation.get("StandardErrorContent", ""))
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ConfigError(f"Timed out waiting for {command}; the remote operation may still be running. Check command-status before retrying.")
        time.sleep(min(interval, remaining))


def remote(config, script, *, wait=False, timeout=3900):
    instance = instance_id(config)
    response = aws(config, "ssm", "send-command", "--instance-ids", instance,
                   "--document-name", "AWS-RunShellScript", "--timeout-seconds", "60",
                   "--parameters", json.dumps({"commands": ["set -eu\n" + script], "executionTimeout": ["3600"]}))
    command = response["Command"]["CommandId"]
    print(f"Operation queued, NOT yet verified. CommandId: {command}; InstanceId: {instance}")
    print(f"Check completion: aws --region {config['region']} ssm get-command-invocation --command-id {command} --instance-id {instance}")
    if wait:
        wait_command(config, command, instance, timeout=timeout)
        print("Remote command completed with exit code 0. Application acceptance is separate.")


def backup(config, wait=False, timeout=3900):
    remote(config, "/opt/moodle-distribution/backup.sh\n/opt/moodle-distribution/health.sh", wait=wait, timeout=timeout)
    if not config["backup_bucket"]:
        print("Local backup only: it will be lost when this EC2 volume is destroyed.")


def preflight(config, expected_account):
    if not re.fullmatch(r"\d{12}", expected_account):
        raise ConfigError("expected-account must contain 12 digits")
    missing = [name for name in ("terraform", "aws", "session-manager-plugin") if not shutil.which(name)]
    if missing:
        raise ConfigError("Missing tools: " + ", ".join(missing))
    identity = aws(config, "sts", "get-caller-identity")
    if identity["Account"] != expected_account:
        raise ConfigError("AWS account does not match --expected-account")
    print(json.dumps({"account": identity["Account"], "arn": identity["Arn"], "region": config["region"],
                      "workspace": str(workspace(config)), "permissions": "not verified; no resources created"}, indent=2))


def restore(config, uri, confirmation, allow_data_loss=False, wait=False, timeout=3900):
    expected = f"{config['project']}-{config['environment']}"
    if config['environment'] != 'staging' or confirmation != expected or not allow_data_loss:
        raise ConfigError("Restore requires staging, its exact --confirm value and --allow-data-loss")
    pattern = (r"s3://" + re.escape(config['backup_bucket']) + "/" + re.escape(config['project'])
               + r"-(?:dev|staging)/\d{8}T\d{6}Z")
    if not config['backup_bucket'] or not re.fullmatch(pattern, uri):
        raise ConfigError("backup-uri must identify one timestamped set in this project's configured S3 bucket")
    script = ("umask 077\n"
              "destination=$(mktemp -d /var/backups/moodle-restore.XXXXXXXX)\n"
              f"uri={shlex.quote(uri)}\n"
              "for name in database.dump moodledata.tar.gz config.php code.txt runtime-image.txt runtime-Dockerfile SHA256SUMS manifest.json; do\n"
              f"  aws --region {config['region']} s3 cp \"$uri/$name\" \"$destination/$name\" --only-show-errors\n"
              "done\n"
              f"/opt/moodle-distribution/restore.sh \"$destination\" --confirm {shlex.quote(expected)}")
    remote(config, script, wait=wait, timeout=timeout)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(ROOT / "config" / "sydney.yaml"))
    parser.add_argument("--version", action="version", version=VERSION)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("doctor", "validate", "render", "init", "status"):
        sub.add_parser(name)
    sub.add_parser("preflight").add_argument("--expected-account", required=True)
    for name in ("backup", "health"):
        action = sub.add_parser(name)
        action.add_argument("--wait", action="store_true")
        action.add_argument("--timeout", type=int, default=3900)
    action = sub.add_parser("command-status")
    action.add_argument("--command-id", required=True)
    action.add_argument("--wait", action="store_true")
    action.add_argument("--timeout", type=int, default=3900)
    action = sub.add_parser("restore")
    action.add_argument("--backup-uri", required=True)
    action.add_argument("--confirm", required=True)
    action.add_argument("--allow-data-loss", action="store_true")
    action.add_argument("--wait", action="store_true")
    action.add_argument("--timeout", type=int, default=3900)
    sub.add_parser("plan").add_argument("--destroy", action="store_true")
    for name in ("apply", "destroy"):
        action = sub.add_parser(name)
        action.add_argument("--confirm", required=True)
        action.add_argument("--allow-data-loss", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            missing = [tool for tool in ("terraform", "aws", "session-manager-plugin") if not shutil.which(tool)]
            print("Python + PyYAML: OK")
            print("Missing: " + ", ".join(missing) if missing else "Local tools: OK (AWS permissions not checked)")
            return 1 if missing else 0
        config = load_config(args.config)
        if hasattr(args, "timeout") and args.timeout <= 0:
            raise ConfigError("timeout must be positive")
        if args.command == "validate":
            print("Configuration: OK. Target small/dev or small/staging; no AWS request made.")
        elif args.command == "render":
            print(render(config))
        elif args.command == "init":
            init(config)
        elif args.command == "plan":
            plan(config, args.destroy)
        elif args.command in ("apply", "destroy"):
            apply(config, args.confirm, args.command == "destroy", getattr(args, "allow_data_loss", False))
        elif args.command == "status":
            print(json.dumps(outputs(config), indent=2))
            print("These are infrastructure outputs, not Moodle readiness or service health.")
        elif args.command == "backup":
            backup(config, args.wait, args.timeout)
        elif args.command == "health":
            remote(config, "cloud-init status --wait\n/opt/moodle-distribution/health.sh", wait=args.wait, timeout=args.timeout)
        elif args.command == "command-status":
            if not re.fullmatch(r"[a-fA-F0-9]{8}(?:-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12}", args.command_id):
                raise ConfigError("command-id must be an SSM command UUID")
            instance = instance_id(config)
            if args.wait:
                wait_command(config, args.command_id, instance, args.timeout)
            else:
                result = aws(config, "ssm", "get-command-invocation", "--command-id", args.command_id, "--instance-id", instance)
                print(json.dumps(result, indent=2))
                if result["Status"] != "Success" or result.get("ResponseCode") != 0:
                    return 1
        elif args.command == "preflight":
            preflight(config, args.expected_account)
        elif args.command == "restore":
            restore(config, args.backup_uri, args.confirm, args.allow_data_loss, args.wait, args.timeout)
    except (ConfigError, OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
