<?php
// Password is passed to Moodle internally, never through the OS command line.
$settings = json_decode(file_get_contents('/etc/moodle/bootstrap.json'), true, 512, JSON_THROW_ON_ERROR);
$connection = new PDO('pgsql:host=127.0.0.1;dbname=moodle', 'moodle', $settings['dbpass'], [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
$table = $connection->query("SELECT to_regclass('public.mdl_config')")->fetchColumn();
if ($table) {
    $version = $connection->query("SELECT value FROM mdl_config WHERE name='version'")->fetchColumn();
    if ($version) {
        echo "Database is already installed.\n";
        exit(0);
    }
    throw new RuntimeException('Incomplete database installation: inspect and recover before retrying.');
}
unset($connection);
$argv = [
    '/var/www/moodle/admin/cli/install_database.php', '--agree-license',
    '--fullname=Moodle Cloud Lab', '--shortname=CloudLab', '--adminuser=admin',
    '--adminpass=' . $settings['adminpass'], '--adminemail=admin@example.invalid',
];
$_SERVER['argv'] = $argv;
$_SERVER['argc'] = count($argv);
$argc = count($argv);
unset($settings);
require '/var/www/moodle/admin/cli/install_database.php';
