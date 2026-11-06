<?php
define('CLI_SCRIPT', true);
require '/var/www/moodle/config.php';
$scheduled = $DB->count_records_select('task_scheduled', 'faildelay > 0');
$adhoc = $DB->count_records_select('task_adhoc', 'faildelay > 0');
$overdue = $DB->count_records_select('task_adhoc', 'nextruntime < :cutoff', ['cutoff' => time() - 600]);
echo json_encode(['scheduled_failures' => $scheduled, 'adhoc_failures' => $adhoc, 'adhoc_overdue_10m' => $overdue], JSON_THROW_ON_ERROR) . "\n";
exit(($scheduled || $adhoc || $overdue) ? 1 : 0);
