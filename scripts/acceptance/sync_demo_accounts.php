<?php
// Explicit medium-lab operator action; credentials are read from a protected file.
define('CLI_SCRIPT', true);
if (getenv('MOODLE_DEMO_SYNC') !== 'yes') { throw new RuntimeException('Explicit demo sync opt-in required'); }
$deploy = json_decode(file_get_contents('/etc/moodle/deploy.json'), true, 512, JSON_THROW_ON_ERROR);
if (($deploy['role'] ?? '') !== 'runner' || !preg_match('/-(dev|staging)-med$/D', $deploy['name'])) {
    throw new RuntimeException('Use the selected dev/staging medium runner');
}
$pending = json_decode(file_get_contents('/etc/moodle/demo-sync-pending.json'), true, 512, JSON_THROW_ON_ERROR);
if ($pending['site'] !== $deploy['name']) { throw new RuntimeException('Site mismatch'); }
require '/var/www/moodle/config.php';
require_once($CFG->dirroot . '/user/lib.php');
require_once($CFG->libdir . '/enrollib.php');
try {
$admin = get_admin();
if ($admin->username !== 'admin' || $admin->auth !== 'manual' || $pending['users']['admin']['username'] !== 'admin'
        || !validate_internal_user_password($admin, $pending['old_admin_password'])) {
    throw new RuntimeException('Current administrator does not match the expected credential');
}
foreach (['teacher', 'student'] as $role) {
    $candidate = $DB->get_record('user', ['username' => $role, 'mnethostid' => $CFG->mnet_localhost_id]);
    if ($candidate && ($candidate->idnumber !== 'cloud-common-demo-' . $role || $candidate->auth !== 'manual' || is_siteadmin($candidate))) {
        throw new RuntimeException('Existing user is not an owned common demo account');
    }
}
$course = $DB->get_record('course', ['shortname' => 'CLOUD-C01'], '*', MUST_EXIST);
$manual = enrol_get_plugin('manual');
$enrol = $DB->get_record('enrol', ['courseid' => $course->id, 'enrol' => 'manual'], '*', MUST_EXIST);
$transaction = $DB->start_delegated_transaction();
$ids = ['admin' => (int)$admin->id];
foreach (['teacher' => 'editingteacher', 'student' => 'student'] as $name => $rolename) {
    $credential = $pending['users'][$name];
    if ($credential['username'] !== $name || strlen($credential['password']) < 24) {
        throw new RuntimeException('Invalid common demo credential');
    }
    $user = $DB->get_record('user', ['username' => $name, 'mnethostid' => $CFG->mnet_localhost_id]);
    if (!$user) {
        $id = user_create_user((object)['username' => $name, 'password' => $credential['password'], 'auth' => 'manual',
            'firstname' => ucfirst($name), 'lastname' => 'Common Demo', 'idnumber' => 'cloud-common-demo-' . $name,
            'email' => 'common-' . $name . '@example.invalid', 'emailstop' => 1, 'confirmed' => 1,
            'mnethostid' => $CFG->mnet_localhost_id]);
        $user = $DB->get_record('user', ['id' => $id], '*', MUST_EXIST);
    } else {
        if (!update_internal_user_password($user, $credential['password'])) { throw new RuntimeException('Password update failed'); }
    }
    $role = $DB->get_record('role', ['shortname' => $rolename], '*', MUST_EXIST);
    $manual->enrol_user($enrol, $user->id, $role->id);
    unset_user_preference('auth_forcepasswordchange', $user->id);
    $ids[$name] = (int)$user->id;
}
if (!update_internal_user_password($admin, $pending['users']['admin']['password'])) {
    throw new RuntimeException('Admin password update failed');
}
$admin = $DB->get_record('user', ['id' => $admin->id], '*', MUST_EXIST);
if (!validate_internal_user_password($admin, $pending['users']['admin']['password'])
        || validate_internal_user_password($admin, $pending['old_admin_password'])) {
    throw new RuntimeException('Admin rotation verification failed');
}
$transaction->allow_commit();
foreach ($ids as $id) { \core\session\manager::kill_user_sessions($id); }
$context = context_course::instance($course->id);
if (!has_capability('mod/assign:grade', $context, $ids['teacher']) || has_capability('mod/assign:grade', $context, $ids['student'])) {
    throw new RuntimeException('Common demo role boundaries are invalid');
}
echo json_encode(['common_demo_ids' => $ids, 'course_id' => (int)$course->id,
    'admin_old_password_rejected' => true, 'teacher_can_grade' => true, 'student_cannot_grade' => true,
    'existing_sessions_revoked' => true], JSON_THROW_ON_ERROR) . "\n";
} catch (\Throwable $error) {
    $message = $error->getMessage();
    foreach ($pending['users'] as $credential) { $message = str_replace($credential['password'], '[redacted]', $message); }
    $message = str_replace($pending['old_admin_password'], '[redacted]', $message);
    fwrite(STDERR, 'DEMO_SYNC_ERROR ' . json_encode(['type' => get_class($error), 'message' => $message,
        'file' => basename($error->getFile()), 'line' => $error->getLine()], JSON_THROW_ON_ERROR) . "\n");
    throw $error;
}
