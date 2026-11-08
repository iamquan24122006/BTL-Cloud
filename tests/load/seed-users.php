<?php
// Run only on the explicitly selected synthetic staging fixture.
define('CLI_SCRIPT', true);
require '/var/www/moodle/config.php';
require_once($CFG->dirroot . '/user/lib.php');
require_once($CFG->libdir . '/enrollib.php');
// The root caller must check deploy.json before invoking this unprivileged runner.
if (!preg_match('/^[a-z][a-z0-9-]+-staging$/D', $argv[1] ?? '')) {
    throw new RuntimeException('Explicit staging confirmation required');
}
$course = $DB->get_record('course', ['shortname' => 'CLOUD-INTEGRATION'], '*', MUST_EXIST);
$role = $DB->get_record('role', ['shortname' => 'student'], '*', MUST_EXIST);
$enrol = $DB->get_record('enrol', ['courseid' => $course->id, 'enrol' => 'manual'], '*', MUST_EXIST);
$plugin = enrol_get_plugin('manual');
$destination = $CFG->dataroot . '/cloud-load-users.csv';
if (file_exists($destination)) {
    throw new RuntimeException('Load account file exists; reuse it rather than resetting passwords');
}
$out = fopen($destination, 'x');
chmod($destination, 0600);
fputcsv($out, ['username', 'password']);
for ($i = 1; $i <= 50; $i++) {
    $username = sprintf('cloudload%03d', $i);
    if ($DB->record_exists('user', ['username' => $username])) {
        throw new RuntimeException('Unexpected existing load user');
    }
    $password = bin2hex(random_bytes(24)) . '!aA7';
    $id = user_create_user((object)[
        'username' => $username, 'password' => $password, 'auth' => 'manual',
        'firstname' => 'Load', 'lastname' => sprintf('%03d', $i),
        'email' => $username . '@example.invalid', 'confirmed' => 1, 'mnethostid' => $CFG->mnet_localhost_id,
    ]);
    $plugin->enrol_user($enrol, $id, $role->id);
    fputcsv($out, [$username, $password]);
}
fclose($out);
$assignment = $DB->get_record('assign', ['course' => $course->id], '*', MUST_EXIST);
$cm = get_coursemodule_from_instance('assign', $assignment->id, $course->id, false, MUST_EXIST);
echo json_encode(['load_accounts' => 50, 'course_id' => (int)$course->id,
    'assignment_id' => (int)$cm->id, 'assignment_marker' => $assignment->name], JSON_THROW_ON_ERROR) . "\n";
