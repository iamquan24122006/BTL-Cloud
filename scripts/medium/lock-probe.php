<?php
define('CLI_SCRIPT', true);
require '/var/www/moodle/config.php';
$factory = \core\lock\lock_config::get_lock_factory('medium_acceptance');
$lock = $factory->get_lock('shared-probe', 0);
if (!$lock) { echo "BUSY\n"; exit(3); }
echo "ACQUIRED\n";
sleep(20);
$lock->release();
