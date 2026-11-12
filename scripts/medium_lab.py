"""Prepare and plan dedicated N2 lab prerequisites. Never reads/prints secret values.

The support root owns buckets/ECR/secret metadata; the builder root is temporary.
Use saved plans and an exact account confirmation for apply. No existing small
resources are imported, modified, or destroyed by this tool.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import uuid
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / '.work/medium-live'


def command(args, *, env=None, capture=False):
    result = subprocess.run([str(a) for a in args], env=env, check=True, text=True,
                            encoding='utf-8', capture_output=capture)
    return result.stdout.strip() if capture else ''


def aws(region, *args):
    return json.loads(command(['aws', '--region', region, '--no-cli-pager', *args, '--output', 'json'], capture=True))


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def sha(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def source_hash(root):
    value = hashlib.sha256()
    for path in sorted((ROOT / 'infra' / root).glob('*.tf')) + [ROOT / 'scripts/medium/bake-host.sh', Path(__file__)]:
        value.update(path.relative_to(ROOT).as_posix().encode())
        value.update(path.read_bytes())
    lock = ROOT / 'infra' / root / '.terraform.lock.hcl'
    if lock.exists():
        value.update(lock.read_bytes())
    value.update((WORK / root / 'config.tfvars.json').read_bytes())
    return value.hexdigest()


def terraform(root, *args, capture=False):
    work = WORK / root
    work.mkdir(parents=True, exist_ok=True)
    cache = ROOT / '.work/terraform-plugin-cache'
    cache.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env['TF_DATA_DIR'] = str(work / 'terraform-data')
    env['TF_PLUGIN_CACHE_DIR'] = str(cache)
    return command(['terraform', '-chdir=' + str(ROOT / 'infra' / root), *args], env=env, capture=capture)


def prepare(args):
    identity = aws(args.region, 'sts', 'get-caller-identity')
    if identity['Account'] != args.account:
        raise ValueError('AWS account differs from --account')
    pins = WORK / 'dependencies'
    pins.mkdir(parents=True, exist_ok=True)
    urls = {
        'awscli.zip': f'https://awscli.amazonaws.com/awscli-exe-linux-x86_64-{args.awscli_version}.zip',
        'cloudwatch.deb': 'https://amazoncloudwatch-agent.s3.amazonaws.com/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb',
    }
    checksums = {}
    for name, url in urls.items():
        path = pins / name
        if not path.exists():
            print('Downloading official dependency: ' + name, flush=True)
            temporary = path.with_suffix('.partial')
            with urlopen(url, timeout=90) as response, temporary.open('wb') as output:
                while block := response.read(1024 * 1024):
                    output.write(block)
            temporary.replace(path)
        checksums[name] = sha(path)
    print('Resolving pinned EFS source and Canonical AMI', flush=True)
    refs = command(['git', 'ls-remote', 'https://github.com/aws/efs-utils.git', 'refs/tags/' + args.efs_version,
                    'refs/tags/' + args.efs_version + '^{}'], capture=True).splitlines()
    if not refs:
        raise ValueError('EFS tag does not exist')
    efs_commit = refs[-1].split()[0]
    efs_repo = 'https://amazon-efs-utils.aws.com/repo/deb/ubuntu/26.04/'
    with urlopen(efs_repo + 'dists/26.04/main/binary-amd64/Packages', timeout=30) as response:
        package_text = response.read().decode()
    candidates = []
    for block in package_text.strip().split('\n\n'):
        fields = dict(line.split(': ', 1) for line in block.splitlines() if ': ' in line and not line.startswith(' '))
        if fields.get('Package') == 'amazon-efs-utils' and fields.get('Version') == args.efs_version.removeprefix('v') + '-1':
            candidates.append(fields)
    if len(candidates) != 1:
        raise ValueError('Pinned official EFS Ubuntu package is unavailable')
    efs = candidates[0]
    images = aws(args.region, 'ec2', 'describe-images', '--owners', '099720109477', '--filters',
                 'Name=name,Values=ubuntu/images/hvm-ssd-gp3/ubuntu-resolute-26.04-amd64-server-*', 'Name=state,Values=available')['Images']
    base_ami = max(images, key=lambda i: i['CreationDate'])['ImageId']
    shared = {'region': args.region, 'account_id': args.account, 'project': args.project, 'environment': 'dev'}
    save(WORK / 'medium_support/config.tfvars.json', shared)
    builder = dict(shared, base_ami=base_ami, instance_type=args.builder_instance_type, bake={
        'awscli_version': args.awscli_version, 'awscli_sha256': checksums['awscli.zip'],
        'cloudwatch_url': urls['cloudwatch.deb'], 'cloudwatch_sha256': checksums['cloudwatch.deb'],
        'efs_version': args.efs_version, 'efs_commit': efs_commit,
        'efs_deb_url': efs_repo + efs['Filename'], 'efs_deb_sha256': efs['SHA256'],
    })
    save(WORK / 'medium_builder/config.tfvars.json', builder)
    save(WORK / 'identity.json', {'account': args.account, 'region': args.region, 'arn': identity['Arn']})
    print('Prepared pinned dependency hashes and separate support/builder tfvars. No AWS mutation.')


def plan(args):
    identity = aws(args.region, 'sts', 'get-caller-identity')
    if identity['Account'] != args.account:
        raise ValueError('AWS account differs from --account')
    for root in ('medium_support', 'medium_builder'):
        work = WORK / root
        (work / 'apply.json').unlink(missing_ok=True)
        terraform(root, 'init', '-input=false', '-reconfigure', '-backend-config=path=' + str(work / 'terraform.tfstate'))
        terraform(root, 'plan', '-input=false', '-lock-timeout=60s', '-var-file=' + str(work / 'config.tfvars.json'), '-out=' + str(work / 'apply.tfplan'))
        details = json.loads(terraform(root, 'show', '-json', work / 'apply.tfplan', capture=True))
        counts = {a: sum(a in c['change']['actions'] for c in details.get('resource_changes', [])) for a in ('create', 'update', 'delete')}
        save(work / 'apply.json', {'account': args.account, 'plan_sha256': sha(work / 'apply.tfplan'), 'source_sha256': source_hash(root), 'summary': counts})
        print(root + ' saved plan: ' + json.dumps(counts), flush=True)


def apply(args):
    if args.confirm != args.account:
        raise ValueError('Exact account confirmation required')
    if aws(args.region, 'sts', 'get-caller-identity')['Account'] != args.account:
        raise ValueError('AWS account changed')
    # Verify BOTH plans before the first mutation.
    snapshots = {}
    for root in ('medium_support', 'medium_builder'):
        work = WORK / root
        manifest = json.loads((work / 'apply.json').read_text())
        payload = (work / 'apply.tfplan').read_bytes()
        if manifest['account'] != args.account or manifest['source_sha256'] != source_hash(root) or manifest['plan_sha256'] != hashlib.sha256(payload).hexdigest():
            raise ValueError('Prerequisite plan/source/account changed; re-plan')
        snapshots[root] = payload
    for root in ('medium_support', 'medium_builder'):
        work = WORK / root
        (work / 'apply.json').unlink()
        consumed = work / ('consumed-' + uuid.uuid4().hex + '.tfplan')
        consumed.write_bytes(snapshots[root])
        terraform(root, 'apply', '-input=false', '-lock-timeout=60s', consumed)
        save(work / 'outputs.json', json.loads(terraform(root, 'output', '-json', capture=True)))
        print(root + ' applied. Builder bootstrap and AMI capture still require verification.', flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'plan', 'apply'])
    parser.add_argument('--account', required=True)
    parser.add_argument('--region', default='ap-southeast-1')
    parser.add_argument('--project', default='moodle-n2')
    parser.add_argument('--awscli-version', default='2.38.5')
    parser.add_argument('--efs-version', default='v3.3.4')
    parser.add_argument('--builder-instance-type', choices=['t3.small', 't3.medium'], default='t3.medium',
                        help='Use t3.small when the account Free plan does not allow t3.medium')
    parser.add_argument('--confirm')
    args = parser.parse_args(argv)
    {'prepare': prepare, 'plan': plan, 'apply': apply}[args.action](args)


if __name__ == '__main__':
    main()
