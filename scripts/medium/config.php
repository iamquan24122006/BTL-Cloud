<?php
unset($CFG);
global $CFG;
$CFG = new stdClass();
$deploy = json_decode(file_get_contents('/etc/moodle/deploy.json'), true, 512, JSON_THROW_ON_ERROR);
$runtime = json_decode(file_get_contents('/etc/moodle/runtime.json'), true, 512, JSON_THROW_ON_ERROR);
$db = $runtime['database'];
if (PHP_SAPI === 'cli' && getenv('MOODLE_DB_ROLE') === 'migration') {
    $db = json_decode(file_get_contents('/etc/moodle/migration.json'), true, 512, JSON_THROW_ON_ERROR);
}
$CFG->dbtype = 'pgsql';
$CFG->dblibrary = 'native';
$CFG->dbhost = $deploy['db_host'];
$CFG->dbname = $deploy['db_name'];
$CFG->dbuser = $db['username'];
$CFG->dbpass = $db['password'];
$CFG->prefix = 'mdl_';
// The native Moodle 4.5 driver reads dboptions['ssl']; libpq reads PGSSLROOTCERT.
putenv('PGSSLROOTCERT=/etc/ssl/certs/rds-global.pem');
putenv('PGCONNECT_TIMEOUT=3');
$CFG->dboptions = ['dbpersist' => false, 'dbport' => 5432, 'ssl' => 'verify-full'];
$CFG->wwwroot = $deploy['wwwroot'];
$CFG->sslproxy = true;
// ALB preserves the public Host. Moodle reverseproxy=true requires an INTERNAL
// Host and would reject this path as reverseproxyabused (lib/setuplib.php).
$CFG->reverseproxy = false;
$CFG->cookiesecure = true;
$CFG->dataroot = '/var/lib/moodledata';
$CFG->localcachedir = '/var/cache/moodle';
$CFG->directorypermissions = 02770;
$CFG->lock_factory = '\core\lock\postgres_lock_factory';
$CFG->session_handler_class = '\core\session\redis';
$CFG->session_redis_host = $deploy['session_host'];
$CFG->session_redis_port = 6379;
$CFG->session_redis_database = 0;
$CFG->session_redis_auth = $runtime['redis']['token'];
$CFG->session_redis_encrypt = ['cafile' => '/etc/ssl/certs/ca-certificates.crt', 'verify_peer' => true, 'verify_peer_name' => true];
$CFG->session_redis_prefix = $deploy['name'] . ':session:';
$CFG->session_redis_connection_timeout = 3;
$CFG->session_redis_acquire_lock_timeout = 30;
$CFG->session_redis_lock_expire = 7200;
$CFG->disableupdateautodeploy = true;
$CFG->disableupdatenotifications = true;
$CFG->preventexecpath = true;
$CFG->maxbytes = 67108864;
$CFG->debugdisplay = false;
require_once('/var/www/moodle/lib/setup.php');
