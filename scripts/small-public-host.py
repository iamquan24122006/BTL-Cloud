"""Run as root through SSM. Origin credential is fetched on EC2, never in SSM parameters."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

url, region, secret_arn = sys.argv[1:]
if not re.fullmatch(r'https://[a-z0-9]+\.cloudfront\.net', url):
    raise SystemExit('Expected a CloudFront HTTPS URL')
subprocess.run(['apt-get', 'update', '-qq'], check=True, stdout=subprocess.DEVNULL)
subprocess.run(['apt-get', 'install', '-y', '-qq', 'nginx'], check=True, stdout=subprocess.DEVNULL,
               env={**os.environ, 'DEBIAN_FRONTEND': 'noninteractive'})
token = subprocess.check_output(['aws','--region',region,'secretsmanager','get-secret-value',
    '--secret-id',secret_arn,'--query','SecretString','--output','text'], text=True).strip()
if not re.fullmatch('[a-f0-9]{64}', token):
    raise SystemExit('Invalid origin credential')
backup = Path('/var/lib/moodle-distribution/public-backup')
backup.mkdir(mode=0o700, exist_ok=True)
for name, source in [('config.php','/var/www/moodle/config.php'),('deploy.json','/etc/moodle/deploy.json'),
                      ('bootstrap.json','/etc/moodle/bootstrap.json')]:
    if name=='bootstrap.json' and not Path(source).exists():
        continue  # Initial credentials may have been securely removed after installation.
    if not (backup/name).exists():
        shutil.copyfile(source, backup/name)
        (backup/name).chmod(0o600)
host = url.removeprefix('https://')
nginx = '''server {
    listen 8081;
    server_name HOST;
    if ($http_x_moodle_origin != "TOKEN") { return 403; }
    if ($host != "HOST") { return 403; }
    client_max_body_size 64m;
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host HOST;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_read_timeout 60s;
        proxy_buffering off;
    }
}
'''.replace('HOST', host).replace('TOKEN', token)
destination = Path('/etc/nginx/conf.d/moodle-public.conf')
destination.write_text(nginx)
destination.chmod(0o600)
subprocess.run(['nginx','-t'],check=True)
config = Path('/var/www/moodle/config.php')
content = config.read_text()
content = re.sub(r'// BEGIN SMALL PUBLIC\n.*?// END SMALL PUBLIC\n','',content, flags=re.S)
needle = "require_once(__DIR__ . '/lib/setup.php');"
if content.count(needle)!=1:
    raise SystemExit('Unrecognized Moodle config; refusing to rewrite')
block = "// BEGIN SMALL PUBLIC\n$CFG->wwwroot = '"+url+"';\n$CFG->sslproxy = true;\n$CFG->reverseproxy = false;\n$CFG->cookiesecure = true;\n// END SMALL PUBLIC\n"
config.write_text(content.replace(needle,block+needle))
os.chown(config,0,33)
config.chmod(0o640)
for filename in ('deploy.json','bootstrap.json'):
    path=Path('/etc/moodle')/filename
    if filename=='bootstrap.json' and not path.exists():
        continue
    settings=json.loads(path.read_text())
    settings['wwwroot']=url
    path.write_text(json.dumps(settings))
    path.chmod(0o640 if filename=='bootstrap.json' else 0o600)
    if filename=='bootstrap.json': os.chown(path,0,33)
subprocess.run(['systemctl','enable','--now','nginx'],check=True,stdout=subprocess.DEVNULL)
subprocess.run(['systemctl','reload','nginx'],check=True)
subprocess.run(['/opt/moodle-distribution/php-cli.sh','/var/www/moodle/admin/cli/purge_caches.php'],check=True)
print('Small HTTPS origin configured: '+url)
