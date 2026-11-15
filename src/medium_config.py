"""Offline schema for the bounded two-AZ medium lab."""
import ipaddress
import re


class ConfigError(ValueError):
    pass


MEDIUM_KEYS = {
    "account_id", "domain", "certificate_arn", "ami_id", "availability_zones",
    "vpc_cidr", "artifact", "backend", "secrets", "db_instance_type", "app_requests_per_target",
    "db_allocated_storage", "db_backup_retention_days", "redis_node_type", "hosted_zone_id", "restore_source_prefix", "frontend", "retain_cloudfront",
}


def matches(value, pattern):
    return isinstance(value, str) and re.fullmatch(pattern, value) is not None


def mapping(data, name, keys):
    value = data.get(name)
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ConfigError(f"{name}: expected exactly {', '.join(sorted(keys))}; secrets/passwords are not accepted")
    return value


def bucket_name(value):
    if not matches(value, r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]") or ".." in value:
        return False
    try:
        ipaddress.ip_address(value)
        return False
    except ValueError:
        return True


def validate_medium(data):
    data.setdefault('frontend', 'acm')
    data.setdefault('db_backup_retention_days', 7)
    data.setdefault('app_requests_per_target', 600)
    data.setdefault('retain_cloudfront', False)
    if type(data['retain_cloudfront']) is not bool or (data['retain_cloudfront'] and data['frontend'] != 'acm'):
        raise ConfigError('retain_cloudfront: boolean; true is only for preserving an existing CloudFront URL during ACM cutover')
    missing = MEDIUM_KEYS - data.keys()
    if missing:
        raise ConfigError("medium missing keys: " + ", ".join(sorted(missing)))
    if not matches(data["account_id"], r"\d{12}"):
        raise ConfigError("account_id: expected 12 digits as a string")
    if data['frontend'] == 'cloudfront':
        if data['domain'] != '' or data['certificate_arn'] != '' or data['hosted_zone_id'] != '' or data['wwwroot'] != 'auto':
            raise ConfigError('cloudfront lab: use empty domain/certificate_arn/hosted_zone_id and wwwroot: auto; MED-02 remains pending')
    elif data['frontend'] == 'acm':
        domain = data["domain"]
        if not matches(domain, r"(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}"):
            raise ConfigError("domain: expected a lowercase DNS hostname")
        if data["wwwroot"] != "https://" + domain:
            raise ConfigError("wwwroot: medium requires https://domain without a trailing slash")
        prefix = f"arn:aws:acm:{data['region']}:{data['account_id']}:certificate/"
        if not matches(data["certificate_arn"], re.escape(prefix) + r"[a-f0-9-]{36}"):
            raise ConfigError("certificate_arn: must belong to the configured account and ALB region")
    else:
        raise ConfigError('frontend: supported values are acm or cloudfront (temporary lab)')
    if not matches(data["ami_id"], r"ami-[a-f0-9]{8}(?:[a-f0-9]{9})?"):
        raise ConfigError("ami_id: pin a prepared Ubuntu 26.04 amd64 AMI ID")
    zones = data["availability_zones"]
    if (not isinstance(zones, list) or len(zones) != 2
            or any(not matches(z, re.escape(data['region']) + r"[a-z]") for z in zones)
            or zones[0] == zones[1]):
        raise ConfigError("availability_zones: two distinct AZs in region are required")
    try:
        network = ipaddress.ip_network(data["vpc_cidr"], strict=True)
        private_ranges = [ipaddress.ip_network(n) for n in ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16')]
        if network.version != 4 or network.prefixlen != 16 or not any(network.subnet_of(n) for n in private_ranges):
            raise ValueError()
    except (ValueError, TypeError):
        raise ConfigError("vpc_cidr: use a private IPv4 /16 network") from None
    artifact = mapping(data, "artifact", {"image", "release", "bucket", "key", "sha256"})
    image_prefix = f"{data['account_id']}.dkr.ecr.{data['region']}.amazonaws.com/"
    if not matches(artifact["image"], re.escape(image_prefix) + r"[a-z0-9][a-z0-9/_-]*@sha256:[a-f0-9]{64}"):
        raise ConfigError("artifact.image: use a private ECR repository pinned by sha256 digest")
    if not matches(artifact["release"], r"[a-f0-9]{40}"):
        raise ConfigError("artifact.release: expected the full source Git commit")
    if not bucket_name(artifact["bucket"]) or not matches(artifact["key"], r"[a-zA-Z0-9][a-zA-Z0-9/_.-]{0,500}") or ".." in artifact["key"]:
        raise ConfigError("artifact: invalid bundle bucket/key")
    if not matches(artifact["sha256"], r"[a-f0-9]{64}"):
        raise ConfigError("artifact.sha256: expected the bundle SHA-256")
    backend = mapping(data, "backend", {"bucket", "region"})
    if not bucket_name(backend["bucket"]) or backend["region"] != data["region"]:
        raise ConfigError("backend: use a valid state bucket in the configured region")
    if not bucket_name(data["backup_bucket"]) or len({backend['bucket'], artifact['bucket'], data['backup_bucket']}) != 3:
        raise ConfigError("medium requires separate nonempty state, artifact and backup buckets")
    if isinstance(data.get('secrets'), dict):
        data['secrets'].setdefault('admin_arn', '')
    secrets = mapping(data, "secrets", {"runtime_arn", "migration_arn", "redis_arn", "redis_version", "admin_arn"})
    secret_prefix = f"arn:aws:secretsmanager:{data['region']}:{data['account_id']}:secret:"
    for key in ("runtime_arn", "migration_arn", "redis_arn"):
        if not matches(secrets[key], re.escape(secret_prefix) + r"[a-zA-Z0-9/_+=.@-]+"):
            raise ConfigError(f"secrets.{key}: expected a Secrets Manager ARN in this account/region")
    if not isinstance(secrets['admin_arn'], str) or (secrets['admin_arn'] and not matches(secrets['admin_arn'], re.escape(secret_prefix) + r"[a-zA-Z0-9/_+=.@-]+")):
        raise ConfigError('secrets.admin_arn: expected empty or a Secrets Manager ARN in this account/region')
    if secrets['runtime_arn'] == secrets['migration_arn']:
        raise ConfigError("secrets: runtime and migration credentials must be separate")
    if not matches(secrets["redis_version"], r"[a-zA-Z0-9-]{32,64}"):
        raise ConfigError("secrets.redis_version: pin the secret version used by ElastiCache")
    if data["db_instance_type"] not in ("db.t3.micro", "db.t3.small", "db.t3.medium", "db.t4g.micro", "db.t4g.small", "db.t4g.medium"):
        raise ConfigError("db_instance_type: unsupported lab instance")
    if type(data["db_allocated_storage"]) is not int or not 20 <= data["db_allocated_storage"] <= 100:
        raise ConfigError("db_allocated_storage: integer from 20 to 100 GiB")
    if type(data['db_backup_retention_days']) is not int or not 1 <= data['db_backup_retention_days'] <= 35:
        raise ConfigError('db_backup_retention_days: integer from 1 to 35; automated backups cannot be disabled')
    if type(data['app_requests_per_target']) is not int or not 60 <= data['app_requests_per_target'] <= 6000:
        raise ConfigError('app_requests_per_target: integer from 60 to 6000 requests per target per minute')
    if data["redis_node_type"] not in ("cache.t3.micro", "cache.t3.small", "cache.t4g.micro", "cache.t4g.small"):
        raise ConfigError("redis_node_type: unsupported lab node")
    if not isinstance(data["hosted_zone_id"], str) or (data["hosted_zone_id"] and not matches(data["hosted_zone_id"], r"Z[A-Z0-9]+")):
        raise ConfigError("hosted_zone_id: empty for external DNS, or a Route 53 zone ID")
    source = data['restore_source_prefix']
    if not isinstance(source, str) or (source and (not matches(source, r'[a-z][a-z0-9-]{2,60}') or source.endswith('-'))):
        raise ConfigError('restore_source_prefix: empty or the source medium site name (project-environment-med)')
    return data
