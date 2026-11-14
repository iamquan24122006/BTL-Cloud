"""Return the small lab to its original SSM URL, preserving current DB credentials."""
import json
import os
from pathlib import Path
import re
import subprocess

config=Path('/var/www/moodle/config.php')
content=config.read_text()
if '// BEGIN SMALL PUBLIC' not in content:
    raise SystemExit('No public override found; refusing an unrelated config rewrite')
content=re.sub(r'// BEGIN SMALL PUBLIC\n.*?// END SMALL PUBLIC\n','',content,flags=re.S)
config.write_text(content)
config.chmod(0o640)
os.chown(config,0,33)
for name in ('deploy.json','bootstrap.json'):
    path=Path('/etc/moodle')/name
    if not path.exists(): continue
    settings=json.loads(path.read_text())
    settings['wwwroot']='http://localhost:8080'
    path.write_text(json.dumps(settings))
    path.chmod(0o640 if name=='bootstrap.json' else 0o600)
    if name=='bootstrap.json': os.chown(path,0,33)
proxy=Path('/etc/nginx/conf.d/moodle-public.conf')
if proxy.exists():
    proxy.rename('/var/lib/moodle-distribution/public-backup/nginx-public.disabled')
subprocess.run(['nginx','-t'],check=True)
subprocess.run(['systemctl','reload','nginx'],check=True)
subprocess.run(['/opt/moodle-distribution/php-cli.sh','/var/www/moodle/admin/cli/purge_caches.php'],check=True)
subprocess.run(['/opt/moodle-distribution/health.sh'],check=True)
print('Returned to SSM localhost URL; frontend AWS resources remain for reviewed cleanup.')
