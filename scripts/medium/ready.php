<?php
// No bootstrap of Moodle/session, metadata or diagnostics in the response.
ini_set('display_errors', '0');
header('Content-Type: text/plain');
header('Cache-Control: no-store');
try {
    $d = json_decode(file_get_contents('/etc/moodle/deploy.json'), true, 512, JSON_THROW_ON_ERROR);
    $r = json_decode(file_get_contents('/etc/moodle/runtime.json'), true, 512, JSON_THROW_ON_ERROR);
    $db = new PDO('pgsql:host=' . $d['db_host'] . ';dbname=' . $d['db_name'] . ';connect_timeout=2;sslmode=verify-full;sslrootcert=/etc/ssl/certs/rds-global.pem',
        $r['database']['username'], $r['database']['password'], [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
    if (!$db->query("SELECT value FROM mdl_config WHERE name='version'")->fetchColumn()) { throw new RuntimeException(); }
    foreach (['session_host', 'cache_host'] as $host) {
        $redis = new Redis();
        $redis->connect('tls://' . $d[$host], 6379, 1.0, null, 0, 1.0,
            ['stream' => ['verify_peer' => true, 'verify_peer_name' => true, 'cafile' => '/etc/ssl/certs/ca-certificates.crt']]);
        $redis->auth($r['redis']['token']);
        if (!$redis->ping()) { throw new RuntimeException(); }
        $redis->close();
    }
    if (!is_writable('/var/lib/moodledata') || !is_writable('/var/cache/moodle')) { throw new RuntimeException(); }
    echo "ok\n";
} catch (Throwable $e) {
    http_response_code(503);
    echo "unavailable\n";
}
