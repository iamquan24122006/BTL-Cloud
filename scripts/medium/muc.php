<?php
define('CLI_SCRIPT', true);
require '/var/www/moodle/config.php';
$d = json_decode(file_get_contents('/etc/moodle/deploy.json'), true, 512, JSON_THROW_ON_ERROR);
$r = json_decode(file_get_contents('/etc/moodle/runtime.json'), true, 512, JSON_THROW_ON_ERROR);
$writer = \core_cache\config_writer::instance();
$stores = $writer->get_all_stores();
$configuration = [
    'server' => $d['cache_host'] . ':6379', 'prefix' => $d['name'] . ':muc:',
    'password' => $r['redis']['token'], 'encryption' => 1, 'clustermode' => 0,
    'cafile' => '/etc/ssl/certs/ca-certificates.crt', 'serializer' => 1,
    'compressor' => 0, 'connectiontimeout' => 2,
];
if (isset($stores['mediumredis'])) {
    $writer->edit_store_instance('mediumredis', 'redis', $configuration);
} else {
    $writer->add_store_instance('mediumredis', 'redis', $configuration);
}
$writer->set_mode_mappings([
    \core_cache\store::MODE_APPLICATION => ['mediumredis'],
    \core_cache\store::MODE_SESSION => ['default_session'],
    \core_cache\store::MODE_REQUEST => ['default_request'],
]);
echo "MUC application mapping configured; session cache uses the shared session handler.\n";
