<?php
define('CLI_SCRIPT', true);
require '/var/www/moodle/config.php';
$row = $DB->get_record_sql('SELECT ssl, version, cipher FROM pg_stat_ssl WHERE pid = pg_backend_pid()');
if (!$row || !$row->ssl || $CFG->dboptions['ssl'] !== 'verify-full') { exit(1); }
echo json_encode(['driver' => $CFG->dbtype, 'sslmode' => $CFG->dboptions['ssl'], 'tls' => $row], JSON_THROW_ON_ERROR) . "\n";
