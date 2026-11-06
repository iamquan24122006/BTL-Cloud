"""Deploy the small/medium Moodle labs using reviewed, single-use Terraform plans."""

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
import uuid

import yaml
from .medium_config import ConfigError, MEDIUM_KEYS, validate_medium

ROOT = Path(__file__).resolve().parents[1]
INFRA = ROOT / "infra" / "small"
VERSION = "0.2.0"


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
    allowed = required | {"backup_bucket", "tags"} | (MEDIUM_KEYS if data.get("size") == "medium" else set())
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
    if data["size"] not in ("small", "medium"):
        raise ConfigError("Only small/medium are implemented; large/production are unsupported")
    if data["instance_type"] not in ("t3.small", "t3.medium", "t3.large"):
        raise ConfigError("instance_type must be t3.small, t3.medium or t3.large (x86_64)")
    if type(data["volume_gib"]) is not int or not 20 <= data["volume_gib"] <= 200:
        raise ConfigError("volume_gib must be an integer between 20 and 200")
    if data["moodle_version"] != "4.5.15":
        raise ConfigError("This release is pinned to Moodle 4.5.15; upgrade code and compatibility checks together")
    if data["size"] == "small" and data["wwwroot"] != "http://localhost:8080":
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
    return validate_medium(data) if data["size"] == "medium" else data


def workspace(config):
    suffix = f"-{config['account_id']}-medium" if config["size"] == "medium" else ""
    return ROOT / ".work" / f"{config['project']}-{config['environment']}{suffix}"


def infra(config):
    return ROOT / "infra" / "medium" if config["size"] == "medium" else INFRA


def run(args, *, env=None, capture=False):
    # Argument arrays only: no shell interpolation from YAML.
    result = subprocess.run([str(a) for a in args], env=env, check=True, text=True,
                            encoding="utf-8", capture_output=capture)
    return result.stdout.strip() if capture else ""


def tf(config, *args, capture=False):
    env = os.environ.copy()
    env["TF_DATA_DIR"] = str(workspace(config) / "terraform-data")
    return run(["terraform", f"-chdir={infra(config)}", *args], env=env, capture=capture)


def aws(config, *args):
    return json.loads(run(["aws", "--region", config["region"], "--no-cli-pager", *args, "--output", "json"], capture=True))


def fingerprint(config):
    digest = hashlib.sha256(json.dumps(config, sort_keys=True).encode())
    files = sorted(infra(config).rglob("*.tf")) + sorted(infra(config).rglob("*.tftpl")) + sorted((ROOT / "scripts").rglob("*")) + sorted((ROOT / "src").glob("*.py"))
    lockfile = infra(config) / ".terraform.lock.hcl"
    if lockfile.exists():
        files.append(lockfile)
    for file in files:
        if file.is_file() and "__pycache__" not in file.parts and ".terraform" not in file.parts:
            digest.update(file.relative_to(ROOT).as_posix().encode())
            digest.update(file.read_bytes())
    return digest.hexdigest()


def render(config):
    work = workspace(config)
    work.mkdir(parents=True, exist_ok=True)
    file = work / "config.tfvars.json"
    values = {k: v for k, v in config.items() if k != "backend"}
    file.write_text(json.dumps(values, indent=2) + "\n", encoding="utf-8")
    return file


def init(config):
    render(config)
    if config["size"] == "medium":
        backend = config["backend"]
        key = f"{config['account_id']}/{config['project']}/{config['environment']}/medium/terraform.tfstate"
        binding = {"bucket": backend['bucket'], "region": backend['region'], "key": key, "account": config['account_id']}
        binding_path = workspace(config) / 'backend.json'
        if binding_path.exists() and json.loads(binding_path.read_text(encoding='utf-8')) != binding:
            raise ConfigError('Backend changed; back up state and follow the explicit migration runbook before reinitializing')
        tf(config, "init", "-input=false", "-reconfigure", f"-backend-config=bucket={backend['bucket']}",
           f"-backend-config=key={key}", f"-backend-config=region={backend['region']}",
           "-backend-config=encrypt=true", "-backend-config=use_lockfile=true",
           f"-backend-config=allowed_account_ids=[\"{config['account_id']}\"]")
        binding_path.write_text(json.dumps(binding, indent=2), encoding='utf-8')
    else:
        tf(config, "init", "-input=false", "-reconfigure", f"-backend-config=path={workspace(config) / 'terraform.tfstate'}")


def preflight(config):
    missing = [tool for tool in ("terraform", "aws") if not shutil.which(tool)]
    if missing:
        raise ConfigError("Missing tools: " + ", ".join(missing))
    identity = aws(config, "sts", "get-caller-identity")
    if config["size"] == "medium":
        if identity["Account"] != config["account_id"]:
            raise ConfigError("AWS account does not match account_id")
        if config.get('frontend', 'acm') == 'acm':
            cert = aws(config, "acm", "describe-certificate", "--certificate-arn", config["certificate_arn"])["Certificate"]
            names = cert.get("SubjectAlternativeNames", [])
            domain = config["domain"]
            if cert["Status"] != "ISSUED" or not any(domain == n or (n.startswith("*.") and domain.split('.', 1)[1] == n[2:]) for n in names):
                raise ConfigError("certificate_arn: certificate is not issued for domain")
        else:
            print('Temporary CloudFront HTTPS lab: MED-02 (HTTPS on ALB with an owned domain) remains pending.')
        ami = aws(config, "ec2", "describe-images", "--image-ids", config["ami_id"])["Images"]
        if len(ami) != 1 or ami[0]["Architecture"] != "x86_64" or ami[0]["State"] != "available":
            raise ConfigError("ami_id: requires an available x86_64 prepared AMI")
        zones = aws(config, "ec2", "describe-availability-zones", "--zone-names", *config["availability_zones"])["AvailabilityZones"]
        if len(zones) != 2 or any(z["State"] != "available" for z in zones):
            raise ConfigError("availability_zones: two available zones required")
        for bucket in (config['backend']['bucket'], config['backup_bucket'], config['artifact']['bucket']):
            versioning = aws(config, "s3api", "get-bucket-versioning", "--bucket", bucket)
            if versioning.get("Status") != "Enabled":
                raise ConfigError(f"S3 bucket {bucket}: versioning must be Enabled")
            aws(config, "s3api", "get-bucket-encryption", "--bucket", bucket)
        aws(config, "s3api", "head-object", "--bucket", config['artifact']['bucket'], "--key", config['artifact']['key'])
    print(f"AWS identity: {identity['Account']} / {identity['Arn']}; region: {config['region']}")
    print("IAM mutation permissions: NOT verified. No resources were created by preflight.")
    return identity


def plan(config, destroy=False):
    variables = render(config)
    work = workspace(config)
    mode = "destroy" if destroy else "apply"
    manifest = work / f"{mode}.json"
    # Invalidate a previous approval artifact even if the new plan fails.
    manifest.unlink(missing_ok=True)
    identity = preflight(config)
    init(config)
    planfile = work / f"{mode}.tfplan"
    args = ["plan", "-input=false", "-lock-timeout=60s", f"-var-file={variables}", f"-out={planfile}"]
    if destroy:
        args.append("-destroy")
    tf(config, *args)
    details = json.loads(tf(config, "show", "-json", planfile, capture=True))
    changes = details.get("resource_changes", [])
    counts = {a: sum(a in c["change"]["actions"] for c in changes) for a in ("create", "update", "delete")}
    counts['replace'] = sum(set(c['change']['actions']) >= {'create', 'delete'} for c in changes)
    manifest.write_text(json.dumps({"fingerprint": fingerprint(config), "account": identity["Account"],
                                    "identity": identity['Arn'], "summary": counts,
                                    "mode": mode, "plan_sha256": hashlib.sha256(planfile.read_bytes()).hexdigest()}, indent=2), encoding="utf-8")
    print("Plan summary: " + json.dumps(counts))
    print("Review data resources (RDS/EFS/Redis), EC2 replacements and recurring ALB/NAT charges before apply.")
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
        plan_bytes = planfile.read_bytes()
        plan_hash = hashlib.sha256(plan_bytes).hexdigest()
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise ConfigError(f"Run plan{' --destroy' if destroy else ''} first") from exc
    if manifest.get("mode") != mode or manifest.get("fingerprint") != fingerprint(config) or manifest.get("plan_sha256") != plan_hash:
        raise ConfigError("Configuration, source or saved plan changed; generate and review a new plan")
    identity = aws(config, "sts", "get-caller-identity")
    if manifest.get("account") != identity["Account"]:
        raise ConfigError("AWS account changed since plan; refusing to apply")
    if config["size"] == "medium" and identity["Account"] != config['account_id']:
        raise ConfigError("AWS account does not match account_id")
    # Atomically claim the manifest so concurrent local invocations cannot reuse it.
    claimed = work / f"{mode}.consumed.json"
    if claimed.exists():
        claimed.unlink()
    # Single use even when interrupted or failed: partial apply requires a new plan.
    (work / f"{mode}.json").rename(claimed)
    # A concurrent re-plan must not replace the file after its hash was checked.
    private_directory = work / 'consumed' / uuid.uuid4().hex
    private_directory.mkdir(parents=True, mode=0o700)
    private_plan = private_directory / f'{mode}.tfplan'
    with private_plan.open('xb') as stream:
        stream.write(plan_bytes)
    tf(config, "apply", "-input=false", "-lock-timeout=60s", private_plan)
    print("Infrastructure operation finished. Check cloud-init and Moodle health separately.")


def outputs(config):
    return json.loads(tf(config, "output", "-json", capture=True))


def backup(config):
    result = outputs(config)
    output_key = "runner_id" if config['size'] == 'medium' else "instance_id"
    if output_key not in result:
        raise ConfigError("No instance in Terraform state; deploy small first")
    instance = result[output_key]["value"]
    script = "/opt/moodle-medium/operation.sh backup" if config['size'] == 'medium' else "/opt/moodle-distribution/backup.sh"
    response = aws(config, "ssm", "send-command", "--instance-ids", instance,
                   "--document-name", "AWS-RunShellScript", "--timeout-seconds", "60",
                   "--parameters", json.dumps({"commands": [script], "executionTimeout": ["3600"]}))
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
    for name in ("doctor", "preflight", "validate", "render", "init", "status", "backup"):
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
            print(f"Configuration: OK. Target {config['size']}/{config['environment']}; no AWS request made.")
        elif args.command == "render":
            print(render(config))
        elif args.command == "init":
            preflight(config)
            init(config)
        elif args.command == "preflight":
            preflight(config)
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
