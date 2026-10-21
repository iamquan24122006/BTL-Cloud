"""Build and smoke-test PHP/Apache locally. Does not deploy AWS or install Moodle."""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
EXTENSIONS = ["curl", "dom", "gd", "intl", "mbstring", "pgsql", "pdo_pgsql",
              "soap", "sodium", "xml", "zip", "bcmath", "Zend OPcache"]
PHP_METADATA = r'''
$extensions = [];
foreach (''' + json.dumps(EXTENSIONS) + r''' as $extension) {
    $extensions[$extension] = extension_loaded($extension);
}
echo json_encode([
    'php' => PHP_VERSION, 'max_input_vars' => (int)ini_get('max_input_vars'),
    'extensions' => $extensions
], JSON_THROW_ON_ERROR);
'''
PHP_HTTP_PROBE = r'''
$deadline = time() + 45;
do {
    $curl = curl_init('http://127.0.0.1:8080/index.php');
    curl_setopt_array($curl, [CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 2]);
    $body = curl_exec($curl);
    $status = curl_getinfo($curl, CURLINFO_RESPONSE_CODE);
    curl_close($curl);
    if ($status === 200 && $body !== false) { break; }
    usleep(500000);
} while (time() < $deadline);
if ($status !== 200 || $body === false) {
    fwrite(STDERR, "Apache did not become ready.\n"); exit(1);
}
$web = json_decode($body, true, 512, JSON_THROW_ON_ERROR);
$blocked = [];
foreach (['/config.php', '/.git/config'] as $path) {
    $curl = curl_init('http://127.0.0.1:8080' . $path);
    curl_setopt_array($curl, [CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 5]);
    $body = curl_exec($curl);
    $status = curl_getinfo($curl, CURLINFO_RESPONSE_CODE);
    curl_close($curl);
    if (!in_array($status, [403, 404], true) || str_contains((string)$body, 'PRIVATE_FIXTURE')) {
        fwrite(STDERR, "Protected file was not blocked: $path\n"); exit(1);
    }
    $blocked[$path] = $status;
}
if (is_writable('/var/www/moodle/index.php')) {
    fwrite(STDERR, "Application code is writable.\n"); exit(1);
}
echo json_encode(['web' => $web, 'blocked' => $blocked, 'code_readonly' => true], JSON_THROW_ON_ERROR);
'''


class RuntimeCheckError(RuntimeError):
    pass


def utc_now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def validate_metadata(metadata):
    if not metadata.get("php", "").startswith("8.3."):
        raise RuntimeCheckError("Expected PHP 8.3.x")
    if metadata.get("max_input_vars", 0) < 5000:
        raise RuntimeCheckError("max_input_vars must be at least 5000")
    missing = [name for name in EXTENSIONS if metadata.get("extensions", {}).get(name) is not True]
    if missing:
        raise RuntimeCheckError("Missing PHP extensions: " + ", ".join(missing))


class RuntimeCheck:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.container = "moodle-runtime-check-" + uuid.uuid4().hex[:16]
        self.container_attempted = False
        self.report = {
            "started_utc": utc_now(), "status": "running", "checks": [],
            "scope": "PHP/Apache fixture only; excludes Moodle install, DB, systemd, AWS and restore",
        }

    def command(self, name, args, timeout=120, required=True):
        print(f"[{name}]", flush=True)
        logfile = self.directory / (name + ".log")
        check = {"name": name, "log": logfile.name}
        self.report["checks"].append(check)
        try:
            with logfile.open("w", encoding="utf-8") as output:
                result = subprocess.run(["docker", *args], stdout=output, stderr=subprocess.STDOUT,
                                        timeout=timeout, check=False)
            check["returncode"] = result.returncode
            if required and result.returncode != 0:
                raise RuntimeCheckError(f"{name} failed; inspect {logfile}")
            return logfile.read_text(encoding="utf-8", errors="replace").strip()
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            check["error"] = type(exc).__name__
            raise RuntimeCheckError(f"{name}: Docker missing or timed out; inspect {logfile}") from exc

    def execute(self, image, skip_build=False):
        try:
            engine = self.command("engine", ["info", "--format", "{{.OSType}}/{{.Architecture}}"], timeout=30)
            self.report["engine"] = engine
            if not engine.startswith("linux/"):
                raise RuntimeCheckError("A running Linux Docker engine is required")
            if not skip_build:
                self.command("build", ["build", "--platform", "linux/amd64", "--progress=plain",
                                       "--tag", image, str(ROOT / "scripts")], timeout=1800)
            image_id = self.command("image", ["image", "inspect", "--format", "{{.Id}}", image])
            self.report["image_id"] = image_id
            scripts_mount = f"type=bind,src={ROOT / 'scripts'},dst=/scripts,readonly"
            for filename in ("configure.php", "install-db.php"):
                self.command("lint-" + filename.replace(".", "-"), [
                    "run", "--rm", "--platform", "linux/amd64", "--network", "none",
                    "--mount", scripts_mount, "--entrypoint", "php", image_id, "-l", "/scripts/" + filename,
                ])
            cli = json.loads(self.command("php-cli", [
                "run", "--rm", "--platform", "linux/amd64", "--network", "none", "--user", "33:33",
                "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                "--entrypoint", "php", image_id, "-r", PHP_METADATA,
            ]))
            validate_metadata(cli)
            self.report["cli"] = cli
            self.command("apache-config", ["run", "--rm", "--platform", "linux/amd64", "--network", "none",
                                          "--entrypoint", "apache2ctl", image_id, "configtest"])

            fixture = self.directory / "webroot"
            fixture.mkdir(mode=0o755)
            (fixture / ".git").mkdir(mode=0o755)
            (fixture / "index.php").write_text("<?php\n" + PHP_METADATA, encoding="utf-8")
            (fixture / "config.php").write_text("<?php echo 'PRIVATE_FIXTURE';\n", encoding="utf-8")
            (fixture / ".git/config").write_text("PRIVATE_FIXTURE\n", encoding="utf-8")
            for file in fixture.rglob("*"):
                if file.is_file():
                    file.chmod(0o644)
            self.container_attempted = True
            # No published port, no host network, no app data or credentials.
            self.command("web-start", [
                "run", "--detach", "--name", self.container, "--platform", "linux/amd64",
                "--label", "moodle-distribution.purpose=runtime-check", "--network", "none",
                "--security-opt", "no-new-privileges", "--mount",
                f"type=bind,src={fixture.resolve()},dst=/var/www/moodle,readonly", image_id,
            ])
            http = json.loads(self.command("web-probe", [
                "exec", "--user", "33:33", self.container, "php", "-r", PHP_HTTP_PROBE,
            ]))
            validate_metadata(http["web"])
            if http["web"] != cli:
                raise RuntimeCheckError("Web and CLI PHP settings/extensions differ")
            self.report["http"] = http
            self.report["status"] = "passed"
        except (RuntimeCheckError, OSError, ValueError, KeyError) as exc:
            self.report["status"] = "failed"
            self.report["error"] = str(exc)
        finally:
            if self.container_attempted:
                # Only this run's exact, randomly named fixture container is removed.
                for name, args in (("web-logs", ["logs", self.container]),
                                   ("cleanup", ["rm", "--force", self.container])):
                    try:
                        self.command(name, args, timeout=30, required=True)
                    except RuntimeCheckError as exc:
                        self.report.setdefault("cleanup_errors", []).append(str(exc))
                        self.report["status"] = "failed"
            if self.report["status"] == "running":
                self.report["status"] = "interrupted"
            self.report["finished_utc"] = utc_now()
            report_path = self.directory / "report.json"
            report_path.write_text(json.dumps(self.report, indent=2) + "\n", encoding="utf-8")
            print(f"Runtime check: {self.report['status']}. Report: {report_path}", flush=True)
        return 0 if self.report["status"] == "passed" else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default="moodle-php:lab")
    parser.add_argument("--skip-build", action="store_true", help="Test an image already built locally")
    args = parser.parse_args(argv)
    run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    return RuntimeCheck(ROOT / ".work" / "runtime-check" / run_id).execute(args.image, args.skip_build)


if __name__ == "__main__":
    sys.exit(main())
