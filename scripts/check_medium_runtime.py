"""Local medium integration: real Moodle/PHP, TLS PostgreSQL, TLS Redis, two app containers.

Uses isolated Docker networks/volumes and disposable credentials. Excludes AWS,
EFS semantics, ASG, systemd, S3, IAM and cloud restore acceptance.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
import datetime as dt
import json
from pathlib import Path
import subprocess
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]


class Check:
    def __init__(self, image, output):
        self.image = image
        self.output = output
        self.output.mkdir(parents=True, exist_ok=True)
        self.prefix = 'moodle-n2-' + uuid.uuid4().hex[:10]
        self.network = self.prefix + '-net'
        self.containers = []
        self.volumes = []
        self.steps = []
        self.password = uuid.uuid4().hex + uuid.uuid4().hex
        self.report = {'scope': __doc__, 'started': dt.datetime.now(dt.timezone.utc).isoformat(), 'status': 'running', 'steps': self.steps}

    def docker(self, label, *args, input=None, timeout=180):
        print('[' + label + ']', flush=True)
        result = subprocess.run(['docker', *map(str, args)], input=input, text=True, encoding='utf-8',
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
        text = result.stdout.replace(self.password, '[TEST-PASSWORD]')
        (self.output / (label + '.log')).write_text(text, encoding='utf-8')
        self.steps.append({'step': label, 'returncode': result.returncode})
        if result.returncode:
            raise RuntimeError(label + ' failed; inspect its log')
        return text.strip()

    def volume(self, name):
        value = self.prefix + '-' + name
        self.docker('volume-' + name, 'volume', 'create', value)
        self.volumes.append(value)
        return value

    def mount(self, volume, target, readonly=False):
        return ['--mount', 'type=volume,src=' + volume + ',dst=' + target + (',readonly' if readonly else '')]

    def cli(self, label, *args, migration=False, cache=None):
        name = self.prefix + '-cli-' + label
        self.containers.append(name)
        return self.docker(label, 'run', '--rm', '--name', name, '--network', self.network, '--user', '33:33',
                           '--env', 'MOODLE_DB_ROLE=' + ('migration' if migration else 'runtime'),
                           *self.mount(self.config, '/etc/moodle', True), *self.mount(self.data, '/var/lib/moodledata'),
                           *self.mount(cache or self.cache_a, '/var/cache/moodle'),
                           *self.mount(self.tls, '/tls', True),
                           '--mount', 'type=bind,src=' + str(self.private / 'server.crt') + ',dst=/etc/ssl/certs/rds-global.pem,readonly',
                           '--mount', 'type=bind,src=' + str(self.private / 'server.crt') + ',dst=/etc/ssl/certs/ca-certificates.crt,readonly',
                           '--entrypoint', 'php', self.image, *args, timeout=900)

    def start(self, label, alias, image, args, mounts=(), env=()):
        name = self.prefix + '-' + alias
        self.containers.append(name)
        self.docker(label, 'run', '--detach', '--name', name, '--network', self.network, '--network-alias', alias,
                    *[x for value in env for x in ('--env', value)], *mounts, image, *args)
        return name

    def execute(self):
        self.report['image_id'] = self.docker('image', 'image', 'inspect', '--format', '{{.Id}}', self.image)
        self.docker('network', 'network', 'create', '--internal', self.network)
        self.config, self.data, self.cache_a, self.cache_b, self.tls, dbvolume = [self.volume(n) for n in ('config', 'data', 'cache-a', 'cache-b', 'tls', 'db')]
        self.private = self.output / 'private'
        self.private.mkdir(exist_ok=True)
        runtime = {'database': {'username': 'moodle_runtime', 'password': self.password}, 'redis': {'token': self.password}}
        deploy = {'role': 'runner', 'name': 'medium-local-check', 'db_host': 'db', 'db_name': 'moodle',
                  'wwwroot': 'https://moodle.test', 'session_host': 'session', 'cache_host': 'cache',
                  'artifact': {'release': '0' * 40}}
        for name, data in [('deploy.json', deploy), ('runtime.json', runtime),
                           ('migration.json', {'username': 'moodle_migration', 'password': self.password}),
                           ('admin.json', {'username': 'admin', 'password': self.password + 'Aa1!', 'email': 'admin@example.invalid'})]:
            (self.private / name).write_text(json.dumps(data), encoding='utf-8')
        sql = f"""CREATE ROLE moodle_migration LOGIN PASSWORD '{self.password}';
CREATE ROLE moodle_runtime LOGIN PASSWORD '{self.password}';
ALTER DATABASE moodle OWNER TO moodle_migration;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
ALTER SCHEMA public OWNER TO moodle_migration;
GRANT USAGE ON SCHEMA public TO moodle_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE moodle_migration IN SCHEMA public GRANT SELECT,INSERT,UPDATE,DELETE ON TABLES TO moodle_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE moodle_migration IN SCHEMA public GRANT USAGE,SELECT,UPDATE ON SEQUENCES TO moodle_runtime;
"""
        (self.private / 'init.sql').write_text(sql)
        setup = '''set -eu
cp /input/*.json /etc/moodle/
chown -R 0:33 /etc/moodle; chmod 750 /etc/moodle; chmod 640 /etc/moodle/*
touch /etc/moodle/mount-ok
mkdir -p /var/lib/moodledata/.distribution /var/cache/a /var/cache/b
printf '{"release":"0000000000000000000000000000000000000000"}' >/var/lib/moodledata/.distribution/active.json
chown -R 33:33 /var/lib/moodledata /var/cache/a /var/cache/b
openssl req -x509 -newkey rsa:2048 -nodes -days 1 -keyout /tls/server.key -out /tls/server.crt \
  -subj /CN=db -addext 'subjectAltName=DNS:db,DNS:session,DNS:cache' -addext 'basicConstraints=critical,CA:TRUE'
cp /tls/server.crt /input/server.crt
cp /tls/server.key /tls/redis.key
chown 0:999 /tls/server.key; chmod 640 /tls/server.key; chmod 644 /tls/server.crt /tls/redis.key
'''
        self.docker('setup', 'run', '--rm', *self.mount(self.config, '/etc/moodle'), *self.mount(self.data, '/var/lib/moodledata'),
                    *self.mount(self.cache_a, '/var/cache/a'), *self.mount(self.cache_b, '/var/cache/b'), *self.mount(self.tls, '/tls'),
                    '--mount', 'type=bind,src=' + str(self.private) + ',dst=/input', '--entrypoint', 'sh', self.image, '-c', setup)
        for image in ('postgres:16-bookworm', 'redis:7.2-bookworm'):
            self.docker('pull-' + image.split(':')[0], 'pull', image, timeout=600)
        postgres = self.start('database', 'db', 'postgres:16-bookworm', ['postgres', '-c', 'ssl=on', '-c', 'ssl_cert_file=/tls/server.crt', '-c', 'ssl_key_file=/tls/server.key'],
                              mounts=[*self.mount(self.tls, '/tls', True), *self.mount(dbvolume, '/var/lib/postgresql/data'),
                                      '--mount', 'type=bind,src=' + str(self.private / 'init.sql') + ',dst=/docker-entrypoint-initdb.d/init.sql,readonly'],
                              env=['POSTGRES_DB=moodle', 'POSTGRES_PASSWORD=' + self.password])
        for attempt in range(60):
            result = subprocess.run(['docker', 'exec', postgres, 'pg_isready', '-h', '127.0.0.1', '-U', 'postgres', '-d', 'moodle'], capture_output=True)
            if result.returncode == 0:
                break
            time.sleep(2)
        else:
            raise RuntimeError('PostgreSQL did not start')
        for alias in ('session', 'cache'):
            self.start('redis-' + alias, alias, 'redis:7.2-bookworm',
                       ['redis-server', '--port', '0', '--tls-port', '6379', '--tls-cert-file', '/tls/server.crt', '--tls-key-file', '/tls/redis.key',
                        '--tls-ca-cert-file', '/tls/server.crt', '--tls-auth-clients', 'no', '--requirepass', self.password],
                       mounts=self.mount(self.tls, '/tls', True))
        for filename in sorted((ROOT / 'scripts/medium').glob('*.php')):
            self.docker('lint-' + filename.stem, 'run', '--rm', '--network', 'none', '--entrypoint', 'php', self.image, '-l', '/opt/moodle-medium/' + filename.name)
        self.cli('install', '/opt/moodle-medium/install.php', migration=True)
        self.cli('muc', '/opt/moodle-medium/muc.php', migration=True)
        self.cli('muc-rerun', '/opt/moodle-medium/muc.php', migration=True)
        self.cli('tls-proof', '/opt/moodle-medium/tls-proof.php')
        self.cli('cache-write-a', '-r', 'define("CLI_SCRIPT",true); require "/var/www/moodle/config.php"; cache::make("core","config")->set("medium_probe","shared-value");')
        self.cli('cache-read-b', '-r', 'define("CLI_SCRIPT",true); require "/var/www/moodle/config.php"; if(cache::make("core","config")->get("medium_probe")!=="shared-value"){exit(1);}', cache=self.cache_b)
        self.cli('file-write-a', '-r', 'file_put_contents("/var/lib/moodledata/medium-file-probe", "Vietnamese file fixture: tiếng Việt");')
        self.cli('file-read-b', '-r', 'if(hash_file("sha256","/var/lib/moodledata/medium-file-probe")!==hash("sha256","Vietnamese file fixture: tiếng Việt")){exit(1);}', cache=self.cache_b)
        holder = r'''define('CLI_SCRIPT',true); require '/var/www/moodle/config.php';
$f=\core\lock\lock_config::get_lock_factory('medium_acceptance');$l=$f->get_lock('shared-probe',0);if(!$l){exit(1);}
file_put_contents('/var/lib/moodledata/.distribution/lock-ready','1');sleep(10);$l->release();echo 'ACQUIRED';'''
        contender = r'''define('CLI_SCRIPT',true); require '/var/www/moodle/config.php';
$deadline=time()+10;while(!is_file('/var/lib/moodledata/.distribution/lock-ready') && time()<$deadline){usleep(100000);}
if(!is_file('/var/lib/moodledata/.distribution/lock-ready')){exit(1);}
$f=\core\lock\lock_config::get_lock_factory('medium_acceptance');$l=$f->get_lock('shared-probe',0);if($l){$l->release();exit(1);}echo 'BUSY';'''
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(self.cli, 'lock-holder', '-r', holder)
            second = pool.submit(self.cli, 'lock-contender', '-r', contender, cache=self.cache_b)
            first.result()
            second.result()
        for alias, cache in (('app-a', self.cache_a), ('app-b', self.cache_b)):
            self.start('start-' + alias, alias, self.image, ['apache2-foreground'], mounts=[
                *self.mount(self.config, '/etc/moodle', True), *self.mount(self.data, '/var/lib/moodledata'), *self.mount(cache, '/var/cache/moodle'),
                '--read-only', '--tmpfs', '/tmp:rw', '--tmpfs', '/var/run/apache2:rw', '--tmpfs', '/var/lock/apache2:rw',
                '--mount', 'type=bind,src=' + str(self.private / 'server.crt') + ',dst=/etc/ssl/certs/rds-global.pem,readonly',
                '--mount', 'type=bind,src=' + str(self.private / 'server.crt') + ',dst=/etc/ssl/certs/ca-certificates.crt,readonly'])
        time.sleep(3)
        probe = '''$c=curl_init("http://app-a:8080/_ready.php"); curl_setopt_array($c,[CURLOPT_RETURNTRANSFER=>true,CURLOPT_TIMEOUT=>5]); $b=curl_exec($c); if(curl_getinfo($c,CURLINFO_RESPONSE_CODE)!==200 || trim($b)!=="ok"){fwrite(STDERR,(string)$b);exit(1);}'''
        self.cli('readiness', '-r', probe)
        # Real login form: route the same cookie through A then B, without sticky sessions.
        login = r'''
$s=json_decode(file_get_contents('/etc/moodle/admin.json'),true);
$cookiefile='/var/lib/moodledata/.distribution/test-cookie.json';
$cookies=is_file($cookiefile)?json_decode(file_get_contents($cookiefile),true):[];
function request($host,$path,$post=null) {
    global $cookies;
    $c=curl_init('http://'.$host.':8080'.$path);
    $cookie=implode('; ',array_map(fn($k,$v)=>$k.'='.$v,array_keys($cookies),$cookies));
    curl_setopt_array($c,[CURLOPT_RETURNTRANSFER=>true,CURLOPT_TIMEOUT=>30,CURLOPT_HTTPHEADER=>['Host: moodle.test','X-Forwarded-Proto: https','Cookie: '.$cookie],
        CURLOPT_HEADERFUNCTION=>function($c,$h)use(&$cookies){if(preg_match('/^Set-Cookie:\s*([^=]+)=([^;]*)/i',$h,$m)){$cookies[$m[1]]=$m[2];}return strlen($h);}]);
    if($post!==null){curl_setopt($c,CURLOPT_POSTFIELDS,http_build_query($post));}
    $b=curl_exec($c); $code=curl_getinfo($c,CURLINFO_RESPONSE_CODE); curl_close($c); return [$code,$b];
}
if (!$cookies) {
[$code,$body]=request('app-a','/login/index.php');
if($code!==200 || !preg_match('/name="logintoken" value="([^"]+)"/',$body,$m)){fwrite(STDERR,'Missing login form, HTTP '.$code.' '.substr(strip_tags($body),0,3000));exit(1);}
request('app-a','/login/index.php',['username'=>$s['username'],'password'=>$s['password'],'logintoken'=>$m[1]]);
file_put_contents($cookiefile,json_encode($cookies));
}
foreach(['app-a','app-b'] as $host){[$code,$body]=request($host,'/user/profile.php'); if($code!==200 || !str_contains($body,'Admin User')){fwrite(STDERR,'Session not preserved across '.$host.', HTTP '.$code);exit(1);}}
echo "Login retained across A/B\n";
'''
        self.cli('login-across-nodes', '-r', login)
        self.cli('purge-cache', '/var/www/moodle/admin/cli/purge_caches.php', migration=True)
        self.cli('login-after-purge', '-r', login)
        # Confirm MUC purge has not removed Redis sessions (session key count remains nonzero).
        self.cli('session-after-purge', '-r', '$s=json_decode(file_get_contents("/etc/moodle/runtime.json"),true); $r=new Redis();$r->connect("tls://session",6379,2,null,0,2,["stream"=>["cafile"=>"/etc/ssl/certs/ca-certificates.crt"]]);$r->auth($s["redis"]["token"]);if($r->dbSize()<1){exit(1);}')
        self.docker('stop-session-dependency', 'stop', self.prefix + '-session')
        self.cli('readiness-dependency-failure', '-r', '$c=curl_init("http://app-a:8080/_ready.php");curl_setopt_array($c,[CURLOPT_RETURNTRANSFER=>true,CURLOPT_TIMEOUT=>5]);curl_exec($c);if(curl_getinfo($c,CURLINFO_RESPONSE_CODE)!==503){exit(1);}')
        self.docker('restart-session-dependency', 'start', self.prefix + '-session')
        self.cli('readiness-restored', '-r', probe)
        self.cli('enable-maintenance', '-r', 'touch("/var/lib/moodledata/.distribution/blocked");')
        self.cli('fail-open-gate', '-r', '$c=curl_init("http://app-b:8080/login/index.php");curl_setopt_array($c,[CURLOPT_RETURNTRANSFER=>true,CURLOPT_TIMEOUT=>5]);curl_exec($c);if(curl_getinfo($c,CURLINFO_RESPONSE_CODE)!==503){exit(1);}')
        self.report['status'] = 'passed'

    def cleanup(self):
        for name in self.containers:
            subprocess.run(['docker', 'rm', '--force', name], capture_output=True)
        for name in self.volumes:
            result = subprocess.run(['docker', 'volume', 'rm', name], capture_output=True)
            if result.returncode:
                self.report['status'] = 'failed-cleanup'
        subprocess.run(['docker', 'network', 'rm', self.network], capture_output=True)
        # Test credentials stay local in .work; never put them in the shareable report.
        self.report['finished'] = dt.datetime.now(dt.timezone.utc).isoformat()
        (self.output / 'report.json').write_text(json.dumps(self.report, indent=2), encoding='utf-8')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', default='moodle-medium:n2-check')
    parser.add_argument('--output', type=Path, default=ROOT / '.work/medium-runtime-check')
    args = parser.parse_args(argv)
    check = Check(args.image, args.output)
    try:
        check.execute()
    except Exception as exc:
        check.report['status'] = 'failed'
        check.report['error'] = str(exc)
        print(str(exc), flush=True)
    finally:
        for name in check.containers:
            result = subprocess.run(['docker', 'logs', name], capture_output=True, text=True, encoding='utf-8')
            (check.output / (name + '.log')).write_text((result.stdout + result.stderr).replace(check.password, '[TEST-PASSWORD]'), encoding='utf-8')
        check.cleanup()
    print('Medium runtime: ' + check.report['status'] + '. Report: ' + str(check.output / 'report.json'))
    return 0 if check.report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
