"""Generate a non-secret transfer bundle. It writes files, but does not install Moodle."""
from base64 import b64encode
import json
from pathlib import Path
import sys
import textwrap

from src.moodle_cloud import ROOT, load_config


def main():
    config = load_config(sys.argv[1] if len(sys.argv) > 1 else ROOT / "config/dev.yaml")
    deploy = {k: config[k] for k in ("moodle_version", "wwwroot", "backup_bucket", "region")}
    deploy["backup_prefix"] = f"{config['project']}-{config['environment']}"
    files = {"/etc/moodle/deploy.json": (json.dumps(deploy).encode(), "0600")}
    for filename in ("bootstrap.sh", "configure.php", "install-db.php", "health.sh", "backup.sh",
                     "setup-host.sh", "php-cli.sh", "moodle-web.sh", "Dockerfile", "moodle.ini", "moodle-apache.conf"):
        files[f"/opt/moodle-distribution/{filename}"] = ((ROOT / "scripts" / filename).read_bytes(), "0750" if filename.endswith(".sh") else "0644")
    lines = ["#!/usr/bin/env bash", "set -Eeuo pipefail", "[[ $EUID -eq 0 ]] || exit 1",
             "install -d -m 0755 /opt/moodle-distribution", "install -d -m 0750 /etc/moodle"]
    for target, (content, mode) in files.items():
        # Short lines avoid terminal paste limits when transferring through SSM.
        lines.extend([f"base64 -d >'{target}' <<'MOODLE_ASSET_BASE64'",
                      *textwrap.wrap(b64encode(content).decode(), width=76),
                      "MOODLE_ASSET_BASE64", f"chmod {mode} '{target}'"])
    lines.append("echo 'Files copied. Review bootstrap.sh and perform the manual lab before automatic installation.'")
    out = ROOT / ".work" / "manual-transfer.sh"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(out)


if __name__ == "__main__":
    main()
