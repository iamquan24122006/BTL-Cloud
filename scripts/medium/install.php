<?php
// Keep the initial admin password out of the process command line and logs.
$s = json_decode(file_get_contents('/etc/moodle/admin.json'), true, 512, JSON_THROW_ON_ERROR);
$argv = ['/var/www/moodle/admin/cli/install_database.php', '--agree-license',
    '--fullname=Moodle Cloud Medium', '--shortname=CloudMedium', '--adminuser=' . $s['username'],
    '--adminpass=' . $s['password'], '--adminemail=' . $s['email']];
$_SERVER['argv'] = $argv;
$argc = $_SERVER['argc'] = count($argv);
unset($s);
require '/var/www/moodle/admin/cli/install_database.php';
