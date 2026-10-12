<?php
// Invoked as root; no secrets are accepted through argv or printed.
$settings = json_decode(file_get_contents('/etc/moodle/bootstrap.json'), true, 512, JSON_THROW_ON_ERROR);
$values = [
    'dbtype' => 'pgsql', 'dblibrary' => 'native', 'dbhost' => '127.0.0.1',
    'dbname' => 'moodle', 'dbuser' => 'moodle', 'dbpass' => $settings['dbpass'],
    'prefix' => 'mdl_', 'dboptions' => ['dbpersist' => false, 'dbport' => 5432],
    'wwwroot' => $settings['wwwroot'], 'dataroot' => '/var/lib/moodledata',
    'localcachedir' => '/var/cache/moodle', 'admin' => 'admin',
    'directorypermissions' => 02770, 'disableupdateautodeploy' => true,
];
$content = "<?php\nunset(\$CFG);\nglobal \$CFG;\n\$CFG = new stdClass();\n";
foreach ($values as $key => $value) {
    $content .= '$CFG->' . $key . ' = ' . var_export($value, true) . ";\n";
}
$content .= "require_once(__DIR__ . '/lib/setup.php');\n";
if (file_put_contents('/var/www/moodle/config.php', $content, LOCK_EX) === false) {
    throw new RuntimeException('Cannot write config.php');
}
chmod('/var/www/moodle/config.php', 0640);
