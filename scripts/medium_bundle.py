"""Package the medium host scripts deterministically; optionally build its immutable image.

This command never uploads or deploys. Publish the resulting files to versioned private
S3/ECR storage, record the returned ECR digest, and update the medium YAML explicitly.
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]


def build_bundle(destination):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('wb') as output:
        with gzip.GzipFile(filename='', mode='wb', fileobj=output, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode='w') as archive:
                for path in sorted((ROOT / 'scripts/medium').iterdir()):
                    if not path.is_file() or path.suffix not in ('.sh', '.py', '.php', '.conf'):
                        continue
                    content = path.read_bytes().replace(b'\r\n', b'\n')
                    info = tarfile.TarInfo(path.name)
                    info.size = len(content)
                    info.mode = 0o750 if path.suffix in ('.sh', '.py') else 0o640
                    info.uid = info.gid = info.mtime = 0
                    archive.addfile(info, io.BytesIO(content))
    checksum = hashlib.sha256(destination.read_bytes()).hexdigest()
    destination.with_suffix(destination.suffix + '.sha256').write_text(checksum + '  ' + destination.name + '\n')
    return checksum


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / '.work/medium-artifact/medium.tar.gz')
    parser.add_argument('--build', action='store_true')
    parser.add_argument('--tag', default='moodle-medium:build')
    parser.add_argument('--moodle-commit', help='Verified upstream commit for tag v4.5.15 (40 hex digits)')
    parser.add_argument('--base-runtime', help='Optional verified Moodle runtime in private ECR, pinned by digest')
    args = parser.parse_args(argv)
    checksum = build_bundle(args.output)
    print(json.dumps({'bundle': str(args.output), 'sha256': checksum}, indent=2))
    if args.build:
        if not args.moodle_commit or not re.fullmatch('[a-f0-9]{40}', args.moodle_commit):
            parser.error('--build requires --moodle-commit (verified v4.5.15 upstream commit)')
        if subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=normal'], cwd=ROOT, text=True).strip():
            parser.error('Commit the reviewed source before building a release; dirty/untracked inputs are not publishable')
        revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        buildfile = ROOT / 'scripts/medium/Dockerfile'
        extra = []
        if args.base_runtime:
            if not re.fullmatch(r'\d{12}\.dkr\.ecr\.[a-z0-9-]+\.amazonaws\.com/[a-z0-9/_-]+@sha256:[a-f0-9]{64}', args.base_runtime):
                parser.error('--base-runtime must be an immutable private ECR URI')
            buildfile = ROOT / 'scripts/medium/Dockerfile.release'
            extra = ['--build-arg', 'BASE_RUNTIME=' + args.base_runtime]
        subprocess.run(['docker', 'build', '--platform', 'linux/amd64', '--file', str(buildfile),
                        '--build-arg', 'RELEASE_COMMIT=' + revision, '--build-arg', 'MOODLE_COMMIT=' + args.moodle_commit,
                        *extra, '--tag', args.tag, str(ROOT)], check=True)
        print('Built source release ' + revision + '. Push once; deploy only its returned @sha256 digest.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
