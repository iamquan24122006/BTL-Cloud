<?php
// Read-only evidence of actual enrolment and assignment settings, never credentials.
define('CLI_SCRIPT', true);
require '/var/www/moodle/config.php';
$manifest = json_decode(file_get_contents($CFG->dataroot . '/.distribution/fixture.json'), true, 512, JSON_THROW_ON_ERROR);
$assignment = $DB->get_record('assign', ['id' => $manifest['assignment']['id']], '*', MUST_EXIST);
$course = $manifest['courses']['CLOUD-C01'];
$context = context_course::instance($course);
$enrolments = [];
foreach ($manifest['users'] as $key => $entry) {
    $user = $DB->get_record('user', ['id' => $entry['id']], '*', MUST_EXIST);
    $roles = array_values(array_map(fn($role) => $role->shortname, get_user_roles($context, $user->id, false)));
    $enrolments[$key] = ['userid' => (int)$user->id, 'c01_enrolled' => is_enrolled($context, $user, '', true),
        'c01_roles' => $roles, 'local_mnet_host' => (int)$user->mnethostid === (int)$CFG->mnet_localhost_id];
}
$settings = [];
foreach (['duedate', 'cutoffdate', 'allowsubmissionsfromdate', 'submissiondrafts', 'teamsubmission',
          'grade', 'maxattempts', 'attemptreopenmethod', 'blindmarking', 'markingworkflow'] as $key) {
    $settings[$key] = $assignment->$key;
}
$submissions = array_values($DB->get_records('assign_submission', ['assignment' => $assignment->id], 'userid', 'id,userid,status,attemptnumber'));
echo json_encode(['time' => gmdate('c'), 'courseid' => (int)$course, 'enrolments' => $enrolments,
    'assignmentid' => (int)$assignment->id, 'settings' => $settings, 'submissions' => $submissions],
    JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE) . "\n";
