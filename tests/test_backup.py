import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

from scripts.verify_backup import BackupError, PAYLOADS, sha256, verify_backup


class BackupVerificationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        for name in PAYLOADS:
            (self.directory / name).write_bytes(b"fixture\n")
        (self.directory / "database.dump").write_bytes(b"PGDMPfixture")
        (self.directory / "code.txt").write_text("a" * 40 + "\n")
        (self.directory / "runtime-image.txt").write_text("sha256:" + "b" * 64 + "\n")
        self.archive("./filedir/fixture.txt")
        (self.directory / "manifest.json").write_text(json.dumps({
            "format": 2, "moodle_version": "4.5.15", "database": "PostgreSQL 16",
            "files": [*PAYLOADS, "SHA256SUMS"],
        }))
        self.checksums()

    def archive(self, name, kind=tarfile.REGTYPE, linkname=""):
        with tarfile.open(self.directory / "moodledata.tar.gz", "w:gz") as archive:
            member = tarfile.TarInfo(name)
            member.type = kind
            member.linkname = linkname
            member.size = 4 if kind == tarfile.REGTYPE else 0
            archive.addfile(member, io.BytesIO(b"data") if member.size else None)

    def checksums(self):
        (self.directory / "SHA256SUMS").write_text("".join(
            f"{sha256(self.directory / name)}  {name}\n" for name in PAYLOADS))

    def test_complete_backup_is_verified_without_claiming_restore(self):
        report = verify_backup(self.directory, expected_commit="a" * 40)
        self.assertEqual(report["status"], "verified")
        self.assertFalse(report["restore_tested"])

    def test_corrupt_missing_and_incomplete_sets_are_rejected(self):
        (self.directory / "database.dump").write_bytes(b"changed")
        with self.assertRaisesRegex(BackupError, "Checksum"):
            verify_backup(self.directory)
        (self.directory / "database.dump").unlink()
        with self.assertRaisesRegex(BackupError, "Missing"):
            verify_backup(self.directory)

    def test_checksum_paths_and_duplicates_are_rejected(self):
        file = self.directory / "SHA256SUMS"
        valid = file.read_text()
        for extra in (valid.splitlines()[0] + "\n", "a" * 64 + "  ../outside\n"):
            file.write_text(valid + extra)
            with self.assertRaises(BackupError):
                verify_backup(self.directory)

    def test_archive_cannot_escape_target_or_create_links_and_devices(self):
        for name, kind in (("../outside", tarfile.REGTYPE), ("/etc/secret", tarfile.REGTYPE),
                           ("dir\\outside", tarfile.REGTYPE), ("file", tarfile.SYMTYPE),
                           ("file", tarfile.LNKTYPE), ("file", tarfile.CHRTYPE)):
            with self.subTest(name=name, kind=kind):
                self.archive(name, kind, "/etc/passwd")
                self.checksums()
                with self.assertRaisesRegex(BackupError, "Unsafe"):
                    verify_backup(self.directory)

    def test_wrong_code_and_runtime_are_rejected(self):
        with self.assertRaisesRegex(BackupError, "commit differs"):
            verify_backup(self.directory, expected_commit="c" * 40)
        dockerfile = self.directory / "target-Dockerfile"
        dockerfile.write_text("different runtime")
        with self.assertRaisesRegex(BackupError, "Dockerfile differs"):
            verify_backup(self.directory, expected_dockerfile=dockerfile)

    def test_manifest_cannot_omit_a_payload(self):
        path = self.directory / "manifest.json"
        manifest = json.loads(path.read_text())
        manifest["files"].remove("config.php")
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(BackupError, "complete backup set"):
            verify_backup(self.directory)

    def test_wrong_database_format_is_rejected_even_with_valid_checksum(self):
        (self.directory / "database.dump").write_bytes(b"plain SQL")
        self.checksums()
        with self.assertRaisesRegex(BackupError, "custom-format"):
            verify_backup(self.directory)


if __name__ == "__main__":
    unittest.main()
