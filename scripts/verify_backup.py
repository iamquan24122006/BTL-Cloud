"""Verify a format-2 small backup before changing a database or extracting files."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import tarfile

PAYLOADS = ("database.dump", "moodledata.tar.gz", "config.php", "code.txt",
            "runtime-image.txt", "runtime-Dockerfile")
FILES = (*PAYLOADS, "SHA256SUMS", "manifest.json")


class BackupError(ValueError):
    pass


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_backup(directory, *, expected_commit=None, expected_dockerfile=None):
    directory = Path(directory)
    if directory.is_symlink() or not directory.is_dir():
        raise BackupError("Backup must be a real directory")
    for name in FILES:
        path = directory / name
        if path.is_symlink() or not path.is_file() or path.stat().st_size == 0:
            raise BackupError(f"Missing, empty or linked backup file: {name}")
    try:
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise BackupError("Invalid backup manifest") from exc
    if not isinstance(manifest, dict) or type(manifest.get("format")) is not int or manifest["format"] != 2:
        raise BackupError("Only backup format 2 is supported")
    if manifest.get("moodle_version") != "4.5.15" or manifest.get("database") != "PostgreSQL 16":
        raise BackupError("Backup Moodle/database baseline does not match this release")
    listed = manifest.get("files")
    if (not isinstance(listed, list) or any(not isinstance(name, str) for name in listed)
            or sorted(listed) != sorted((*PAYLOADS, "SHA256SUMS"))):
        raise BackupError("Manifest does not describe exactly one complete backup set")
    hashes = {}
    for line in (directory / "SHA256SUMS").read_text(encoding="ascii").splitlines():
        match = re.fullmatch(r"([a-f0-9]{64}) [ *]([A-Za-z0-9_.-]+)", line)
        if not match or match[2] not in PAYLOADS or match[2] in hashes:
            raise BackupError("Invalid, duplicate or unexpected checksum entry")
        hashes[match[2]] = match[1]
    if set(hashes) != set(PAYLOADS):
        raise BackupError("Checksum list is incomplete")
    for name, expected in hashes.items():
        if sha256(directory / name) != expected:
            raise BackupError(f"Checksum mismatch: {name}")
    with (directory / "database.dump").open("rb") as stream:
        header = stream.read(5)
    if header != b"PGDMP":
        raise BackupError("Database is not a PostgreSQL custom-format dump")
    commit = (directory / "code.txt").read_text(encoding="ascii").strip()
    if not re.fullmatch(r"[a-f0-9]{40}", commit):
        raise BackupError("Invalid Moodle code commit")
    if expected_commit is not None and commit != expected_commit:
        raise BackupError("Backup Moodle commit differs from the target")
    if expected_dockerfile and (directory / "runtime-Dockerfile").read_bytes() != Path(expected_dockerfile).read_bytes():
        raise BackupError("Backup Dockerfile differs from the target runtime")
    image = (directory / "runtime-image.txt").read_text(encoding="ascii").strip()
    if not re.fullmatch(r"sha256:[a-f0-9]{64}", image):
        raise BackupError("Invalid runtime image ID")
    seen = set()
    with tarfile.open(directory / "moodledata.tar.gz", "r:gz") as archive:
        for member in archive:
            path = PurePosixPath(member.name)
            if (path.is_absolute() or ".." in path.parts or "\\" in member.name
                    or ":" in member.name or not (member.isfile() or member.isdir())):
                raise BackupError("Unsafe path or file type in moodledata archive")
            key = path.as_posix()
            if key in seen:
                raise BackupError("Duplicate path in moodledata archive")
            seen.add(key)
        if not seen:
            raise BackupError("Empty moodledata archive")
    return {"status": "verified", "format": 2, "moodle_version": "4.5.15",
            "code_commit": commit, "runtime_image": image, "checksums": hashes,
            "restore_tested": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--expected-commit")
    parser.add_argument("--expected-dockerfile", type=Path)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(verify_backup(args.directory, expected_commit=args.expected_commit,
                                      expected_dockerfile=args.expected_dockerfile), indent=2))
    except (BackupError, OSError, ValueError, tarfile.TarError) as exc:
        print(f"Backup verification failed: {exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
