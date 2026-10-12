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
import subprocess
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
INFRA = ROOT / "infra" / "small"
VERSION = "0.1.0"


class ConfigError(ValueError):
    pass


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
    return json.loads(run(["aws", "--region", config["region"], "--no-cli-pager", *args, "--output", "json"], capture=True))


def fingerprint(config):
    digest = hashlib.sha256(json.dumps(config, sort_keys=True).encode())
    files = sorted(INFRA.glob("*.tf")) + sorted((ROOT / "scripts").glob("*"))
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
    variables = render(config)
    identity = aws(config, "sts", "get-caller-identity")
    init(config)
    work = workspace(config)
    mode = "destroy" if destroy else "apply"
    manifest = work / f"{mode}.json"
    # Invalidate a previous approval artifact even if the new plan fails.
    manifest.unlink(missing_ok=True)
    planfile = work / f"{mode}.tfplan"
    args = ["plan", "-input=false", "-lock-timeout=60s", f"-var-file={variables}", f"-out={planfile}"]
    if destroy:
        args.append("-destroy")
    tf(config, *args)
    manifest.write_text(json.dumps({"fingerprint": fingerprint(config), "account": identity["Account"],
                                    "mode": mode, "plan_sha256": hashlib.sha256(planfile.read_bytes()).hexdigest()}, indent=2), encoding="utf-8")
    print(f"Saved {mode} plan for AWS account {identity['Account']}. Review the Terraform output before applying.")


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
    identity = aws(config, "sts", "get-caller-identity")
    if manifest.get("account") != identity["Account"]:
        raise ConfigError("AWS account changed since plan; refusing to apply")
    # Single use even when interrupted or failed: partial apply requires a new plan.
    (work / f"{mode}.json").unlink()
    tf(config, "apply", "-input=false", "-lock-timeout=60s", planfile)
    print("Infrastructure operation finished. Check cloud-init and Moodle health separately.")


def outputs(config):
    return json.loads(tf(config, "output", "-json", capture=True))


def backup(config):
    result = outputs(config)
    if "instance_id" not in result:
        raise ConfigError("No instance in Terraform state; deploy small first")
    instance = result["instance_id"]["value"]
    response = aws(config, "ssm", "send-command", "--instance-ids", instance,
                   "--document-name", "AWS-RunShellScript", "--timeout-seconds", "60",
                   "--parameters", json.dumps({"commands": ["/opt/moodle-distribution/backup.sh"], "executionTimeout": ["3600"]}))
    command = response["Command"]["CommandId"]
    print(f"Backup queued, NOT yet verified. CommandId: {command}; InstanceId: {instance}")
    print(f"Check completion: aws --region {config['region']} ssm get-command-invocation --command-id {command} --instance-id {instance}")
    if not config["backup_bucket"]:
        print("Local backup only: it will be lost when this EC2 volume is destroyed.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(ROOT / "config" / "dev.yaml"))
    parser.add_argument("--version", action="version", version=VERSION)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("doctor", "validate", "render", "init", "status", "backup"):
        sub.add_parser(name)
    sub.add_parser("plan").add_argument("--destroy", action="store_true")
    for name in ("apply", "destroy"):
        action = sub.add_parser(name)
        action.add_argument("--confirm", required=True)
        if name == "destroy":
            action.add_argument("--allow-data-loss", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            missing = [tool for tool in ("terraform", "aws", "session-manager-plugin") if not shutil.which(tool)]
            print("Python + PyYAML: OK")
            print("Missing: " + ", ".join(missing) if missing else "Local tools: OK (AWS permissions not checked)")
            return 1 if missing else 0
        config = load_config(args.config)
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
            backup(config)
    except (ConfigError, OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
