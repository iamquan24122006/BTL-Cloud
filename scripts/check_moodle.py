"""Install and restore Moodle in isolated local Docker containers, without AWS."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
MOODLE_COMMIT = "215f44380bdc3ccf852a3a22e34f8423ff64033a"  # v4.5.15
POSTGRES = "postgres:16-bookworm@sha256:e8a07d2c7579b038938cdba6c539e580e5001caf9ea203d397b5cc83e76bd938"


class CheckError(RuntimeError):
    pass


class MoodleCheck:
    def __init__(self, image, keep_on_failure=False):
        self.keep_on_failure = keep_on_failure
        self.token = uuid.uuid4().hex[:12]
        self.prefix = "moodle-check-" + self.token
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self.directory = ROOT / ".work/moodle-check" / f"{stamp}-{self.token}"
        self.directory.mkdir(parents=True)
        self.image = image
        self.containers = []
        self.volumes = []
        self.passwords = {key: secrets.token_hex(32) + "!aA7" for key in
                          ("adminpass", "studentpass", "studentbpass", "outsiderpass", "teacherpass")}
        self.private_values = list(self.passwords.values())
        self.report = {
            "started_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "status": "running",
            "scope": "Local Docker Moodle/PostgreSQL integration; excludes EC2, systemd, SSM, S3 and load testing",
            "moodle_commit": MOODLE_COMMIT, "checks": [],
        }

    def command(self, name, args, *, payload=None, env=None, timeout=120, required=True):
        print(f"[{name}]", flush=True)
        item = {"name": name, "log": name + ".log"}
        self.report["checks"].append(item)
        try:
            result = subprocess.run(["docker", *map(str, args)], input=payload,
                                    capture_output=True, text=True, encoding="utf-8", errors="replace",
                                    env=env, timeout=timeout, check=False)
            item["returncode"] = result.returncode
            output = result.stdout + result.stderr
        except (OSError, subprocess.TimeoutExpired) as exc:
            item["error"] = type(exc).__name__
            partial = []
            for stream in (getattr(exc, "stdout", None), getattr(exc, "stderr", None)):
                if stream:
                    partial.append(stream.decode("utf-8", errors="replace") if isinstance(stream, bytes) else stream)
            output = "".join(partial)
            for value in self.private_values:
                output = output.replace(value, "[REDACTED]")
            (self.directory / item["log"]).write_text(output, encoding="utf-8")
            item["timeout_seconds"] = timeout
            raise CheckError(f"{name}: {type(exc).__name__}") from exc
        for value in self.private_values:
            output = output.replace(value, "[REDACTED]")
        (self.directory / item["log"]).write_text(output, encoding="utf-8")
        if required and result.returncode:
            raise CheckError(f"{name} failed; inspect {self.directory / item['log']}")
        return result.stdout.strip()

    def volume(self, suffix):
        name = f"{self.prefix}-{suffix}"
        self.command("volume-" + suffix, ["volume", "create", "--label",
                     f"moodle-distribution.integration={self.token}", name])
        self.volumes.append(name)
        return name

    @staticmethod
    def mount(source, target, readonly=False):
        return ["--mount", f"type=volume,src={source},dst={target}" + (",readonly" if readonly else "")]

    def php(self, phase, name, script, *, root=False, payload=None, timeout=180):
        args = ["run", "--rm", "--interactive", "--platform", "linux/amd64",
                "--network", "container:" + phase["db"], "--security-opt", "no-new-privileges"]
        if not root:
            args += ["--user", "33:33", "--read-only", "--cap-drop", "ALL", "--tmpfs", "/tmp:rw,nosuid,nodev,size=128m"]
        args += self.mount(phase.get("code", self.code), "/var/www/moodle", not root)
        args += self.mount(phase["data"], "/var/lib/moodledata")
        args += self.mount(phase["cache"], "/var/cache/moodle")
        args += self.mount(phase["settings"], "/etc/moodle", not root)
        args += self.mount(self.archive, "/backup")
        args += ["--mount", f"type=bind,src={ROOT / 'scripts'},dst=/opt/moodle-distribution,readonly",
                 "--mount", f"type=bind,src={ROOT / 'tests/integration'},dst=/checks,readonly",
                 "--entrypoint", "php", self.image, *script]
        return self.command(name, args, payload=payload, timeout=timeout)

    def database(self, label):
        phase = {key: self.volume(label + "-" + key) for key in ("data", "cache", "settings", "pgdata")}
        phase["db"] = f"{self.prefix}-{label}-db"
        phase["dbpass"] = secrets.token_hex(32)
        admin = secrets.token_hex(32)
        self.private_values.extend([phase["dbpass"], admin])
        env = os.environ.copy()
        env["POSTGRES_PASSWORD"] = admin
        self.containers.append(phase["db"])
        self.command(label + "-db-start", [
            "run", "--detach", "--platform", "linux/amd64", "--network", "none",
            "--name", phase["db"], "--label", f"moodle-distribution.integration={self.token}",
            "--env", "POSTGRES_PASSWORD", *self.mount(phase["pgdata"], "/var/lib/postgresql/data"),
            *self.mount(self.archive, "/backup"), POSTGRES,
        ], env=env)
        for attempt in range(60):
            self.command(f"{label}-db-ready-{attempt}", ["exec", phase["db"], "pg_isready", "--host", "127.0.0.1",
                         "--username", "postgres"], required=False)
            if self.report["checks"][-1]["returncode"] == 0:
                break
            time.sleep(1)
        else:
            raise CheckError("PostgreSQL did not become ready")
        self.command(label + "-db-create", ["exec", "--interactive", phase["db"], "psql", "-U", "postgres",
                     "--dbname", "postgres", "--set", "ON_ERROR_STOP=1"], payload=(
                         f"CREATE ROLE moodle LOGIN PASSWORD '{phase['dbpass']}';\n"
                         "CREATE DATABASE moodle OWNER moodle ENCODING 'UTF8' TEMPLATE template0;\n"))
        settings = {**self.passwords, "dbpass": phase["dbpass"], "wwwroot": "http://localhost:8080",
                    "moodle_version": "4.5.15"}
        self.php(phase, label + "-settings", ["-r", """
            $data = stream_get_contents(STDIN);
            json_decode($data, true, 512, JSON_THROW_ON_ERROR);
            file_put_contents('/etc/moodle/bootstrap.json', $data);
            chmod('/etc/moodle/bootstrap.json', 0640); chgrp('/etc/moodle/bootstrap.json', 33);
            foreach (['/var/lib/moodledata', '/var/cache/moodle'] as $path) {
                chown($path, 33); chgrp($path, 33); chmod($path, 0770);
            }
        """], root=True, payload=json.dumps(settings))
        return phase

    def configure(self, phase, name):
        self.php(phase, name, ["-r", "require '/opt/moodle-distribution/configure.php'; chgrp('/var/www/moodle/config.php', 33);"], root=True)

    def web(self, phase, label):
        phase["web"] = f"{self.prefix}-{label}-web"
        self.containers.append(phase["web"])
        self.command(label + "-web-start", [
            "run", "--detach", "--platform", "linux/amd64", "--name", phase["web"],
            "--label", f"moodle-distribution.integration={self.token}",
            "--network", "container:" + phase["db"], "--security-opt", "no-new-privileges",
            *self.mount(phase.get("code", self.code), "/var/www/moodle", True),
            *self.mount(phase["data"], "/var/lib/moodledata"),
            *self.mount(phase["cache"], "/var/cache/moodle"), self.image,
        ])

    def cleanup(self):
        for kind, names in (("container", list(reversed(self.containers))), ("volume", list(reversed(self.volumes)))):
            for index, name in enumerate(names):
                try:
                    template = '{{index .Config.Labels "moodle-distribution.integration"}}' if kind == "container" else '{{index .Labels "moodle-distribution.integration"}}'
                    owner = self.command(f"cleanup-{kind}-inspect-{index}", [kind, "inspect", "--format", template, name])
                    if owner != self.token:
                        raise CheckError("Refusing cleanup of a resource not owned by this run: " + name)
                    self.command(f"cleanup-{kind}-{index}", [kind, "rm", *( ["--force"] if kind == "container" else [] ), name])
                except CheckError as exc:
                    self.report.setdefault("cleanup_errors", []).append(str(exc))
                    self.report["status"] = "failed"

    @classmethod
    def cleanup_report(cls, filename):
        file = Path(filename).resolve()
        if not file.is_relative_to((ROOT / ".work/moodle-check").resolve()):
            raise CheckError("Cleanup report must be inside .work/moodle-check")
        report = json.loads(file.read_text(encoding="utf-8"))
        resources = report.get("retained_for_debugging", {})
        token = resources.get("token", "")
        if not re.fullmatch(r"[a-f0-9]{12}", token) or report.get("debug_resources_cleaned"):
            raise CheckError("No retained resources to clean")
        check = cls("moodle-php:lab")
        check.token = token
        check.containers = resources["containers"]
        check.volumes = resources["volumes"]
        if any(not name.startswith(f"moodle-check-{token}-") for name in check.containers + check.volumes):
            raise CheckError("Resource name does not match this run")
        check.cleanup()
        report["debug_resources_cleaned"] = not bool(check.report.get("cleanup_errors"))
        if check.report.get("cleanup_errors"):
            report["debug_cleanup_errors"] = check.report["cleanup_errors"]
        file.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        return 0 if report["debug_resources_cleaned"] else 1

    def cron(self, phase, name):
        output = self.php(phase, name, ["/var/www/moodle/admin/cli/cron.php", "--keep-alive=0"], timeout=300)
        if re.search(r"(?:Scheduled|Adhoc) task failed|Fatal error|Uncaught .*Exception", output, re.IGNORECASE):
            raise CheckError(f"{name} reported a failed task; inspect its log")

    def execute(self):
        try:
            engine = self.command("engine", ["info", "--format", "{{.OSType}}/{{.Architecture}}"])
            if not engine.startswith("linux/"):
                raise CheckError("Linux Docker engine required")
            self.image = self.command("runtime-image", ["image", "inspect", "--format", "{{.Id}}", self.image])
            self.report.update(engine=engine, image_id=self.image, postgres_image=POSTGRES)
            self.command("postgres-pull", ["pull", "--platform", "linux/amd64", POSTGRES], timeout=900)
            self.code = self.volume("code")
            self.archive = self.volume("backup")
            self.command("source", [
                "run", "--rm", "--platform", "linux/amd64", *self.mount(self.code, "/source"),
                "--entrypoint", "sh", self.image, "-ec",
                f"curl --fail --silent --show-error --location --retry 3 --max-time 900 https://codeload.github.com/moodle/moodle/tar.gz/{MOODLE_COMMIT} -o /tmp/moodle.tar.gz\n"
                "sha256sum /tmp/moodle.tar.gz\n"
                "tar -xzf /tmp/moodle.tar.gz --strip-components=1 -C /source\n"
                "chown -R 0:33 /source\nfind /source -type d -exec chmod 0750 {} +\nfind /source -type f -exec chmod 0640 {} +",
            ], timeout=1200)
            dev = self.database("dev")
            self.report["dev_resources"] = {key: value for key, value in dev.items() if key != "dbpass"}
            self.report["code_volume"] = self.code
            self.report["backup_volume"] = self.archive
            self.configure(dev, "dev-configure")
            self.php(dev, "dev-install", ["/opt/moodle-distribution/install-db.php"], timeout=900)
            again = self.php(dev, "dev-install-idempotent", ["/opt/moodle-distribution/install-db.php"])
            if "already installed" not in again:
                raise CheckError("Second installation did not detect the installed database")
            self.report["fixture"] = json.loads(self.php(dev, "dev-fixture", ["/checks/moodle.php", "seed"]))
            self.web(dev, "dev")
            self.report["dev"] = json.loads(self.php(dev, "dev-functional", ["/checks/moodle.php", "verify"]))
            self.cron(dev, "dev-cron")
            self.php(dev, "dev-maintenance", ["/var/www/moodle/admin/cli/maintenance.php", "--enable"])
            self.command("dev-web-stop", ["stop", "--time", "60", dev["web"]])
            self.command("database-backup", ["exec", dev["db"], "sh", "-ec",
                         "pg_dump -U postgres --format=custom --no-owner moodle > /backup/database.dump"])
            self.command("files-backup", [
                "run", "--rm", "--network", "none", *self.mount(dev["data"], "/data", True),
                *self.mount(self.archive, "/backup"), "--entrypoint", "sh", self.image, "-ec",
                "tar -C /data --exclude='./cache' --exclude='./localcache' --exclude='./temp' --exclude='./sessions' -czf /backup/moodledata.tar.gz .\n"
                "cd /backup\nsha256sum database.dump moodledata.tar.gz > SHA256SUMS\nsha256sum -c SHA256SUMS",
            ])
            self.php(dev, "dev-maintenance-off", ["/var/www/moodle/admin/cli/maintenance.php", "--disable"])
            self.command("dev-web-resume", ["start", dev["web"]])
            self.php(dev, "dev-after-backup", ["/checks/moodle.php", "verify"])
            stage = self.database("restore")
            stage["code"] = self.volume("restore-code")
            self.command("restore-code-copy", [
                "run", "--rm", "--network", "none", *self.mount(self.code, "/source", True),
                *self.mount(stage["code"], "/target"), "--entrypoint", "sh", self.image,
                "-ec", "cp -a /source/. /target/",
            ])
            self.report["fresh_database_password"] = stage["dbpass"] != dev["dbpass"]
            self.configure(stage, "restore-configure")
            self.command("database-restore", ["exec", stage["db"], "pg_restore", "-U", "postgres", "--exit-on-error",
                         "--single-transaction", "--no-owner", "--role=moodle", "--dbname=moodle", "/backup/database.dump"], timeout=900)
            self.command("files-restore", [
                "run", "--rm", "--network", "none", *self.mount(stage["data"], "/data"),
                *self.mount(self.archive, "/backup", True), "--entrypoint", "sh", self.image, "-ec",
                "cd /backup\nsha256sum -c SHA256SUMS\ntar --no-same-owner -xzf moodledata.tar.gz -C /data\nchown -R 33:33 /data",
            ])
            self.php(stage, "restore-purge", ["/var/www/moodle/admin/cli/purge_caches.php"])
            self.php(stage, "restore-maintenance-off", ["/var/www/moodle/admin/cli/maintenance.php", "--disable"])
            self.web(stage, "restore")
            self.report["restored"] = json.loads(self.php(stage, "restore-functional", ["/checks/moodle.php", "verify"]))
            if self.report["dev"] != self.report["restored"]:
                raise CheckError("Restored course, users, enrolments or file hash differ")
            self.cron(stage, "restore-cron")
            self.report["post_restore_write"] = json.loads(self.php(stage, "restore-write", ["/checks/moodle.php", "write"]))
            self.report["status"] = "passed"
        except (CheckError, OSError, ValueError, KeyError) as exc:
            self.report.update(status="failed", error=str(exc))
        finally:
            for index, container in enumerate(self.containers):
                try:
                    self.command(f"container-logs-{index}", ["logs", container], required=False)
                except CheckError:
                    pass
            if self.keep_on_failure and self.report["status"] == "failed":
                self.report["retained_for_debugging"] = {
                    "token": self.token, "containers": self.containers, "volumes": self.volumes,
                }
            else:
                self.cleanup()
            if self.report["status"] == "running":
                self.report["status"] = "interrupted"
            self.report["finished_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
            file = self.directory / "report.json"
            file.write_text(json.dumps(self.report, indent=2) + "\n", encoding="utf-8")
            print(f"Moodle integration: {self.report['status']}. Report: {file}", flush=True)
        return 0 if self.report["status"] == "passed" else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default="moodle-php:lab", help="Previously built runtime image")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--keep-on-failure", action="store_true", help="Keep only this run's containers/volumes for diagnosis on failure")
    action.add_argument("--cleanup", metavar="REPORT", help="Clean resources explicitly retained by a failed run")
    args = parser.parse_args()
    if args.cleanup:
        return MoodleCheck.cleanup_report(args.cleanup)
    return MoodleCheck(args.image, args.keep_on_failure).execute()


if __name__ == "__main__":
    raise SystemExit(main())
