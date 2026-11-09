<?php
// Explicit, runner-only acceptance fixture. No passwords are printed or stored on EFS.
define('CLI_SCRIPT', true);
if (getenv('MOODLE_FIXTURE') !== 'yes') { throw new RuntimeException('Explicit fixture opt-in required'); }
$deploy = json_decode(file_get_contents('/etc/moodle/deploy.json'), true, 512, JSON_THROW_ON_ERROR);
if ($deploy['role'] !== 'runner') { throw new RuntimeException('Use the dedicated runner'); }
$initial = json_decode(file_get_contents('/etc/moodle/admin.json'), true, 512, JSON_THROW_ON_ERROR);
require '/var/www/moodle/config.php';
require_once($CFG->dirroot . '/user/lib.php');
require_once($CFG->dirroot . '/course/lib.php');
require_once($CFG->dirroot . '/course/modlib.php');
require_once($CFG->dirroot . '/lib/resourcelib.php');
require_once($CFG->dirroot . '/mod/assign/locallib.php');
\core\session\manager::set_user(get_admin());
set_config('noemailever', 1);
$manifestpath = $CFG->dataroot . '/.distribution/fixture.json';
if (is_file($manifestpath)) {
    $existing = json_decode(file_get_contents($manifestpath), true, 512, JSON_THROW_ON_ERROR);
    foreach ($existing['users'] as $entry) {
        $user = $DB->get_record('user', ['id' => $entry['id'], 'username' => $entry['username']], '*', MUST_EXIST);
        if ((int)$user->mnethostid === 0) {
            user_update_user((object)['id' => $user->id, 'mnethostid' => $CFG->mnet_localhost_id], false);
        } elseif ((int)$user->mnethostid !== (int)$CFG->mnet_localhost_id) {
            throw new RuntimeException('Fixture user belongs to another MNet host');
        }
    }
    echo file_get_contents($manifestpath); exit(0);
}
$users = [];
foreach (['teacher' => 'Teacher', 'student_a' => 'Student A', 'student_b' => 'Student B', 'student_c' => 'Student C'] as $key => $name) {
    $username = 'cloud_' . $key;
    $user = $DB->get_record('user', ['username' => $username, 'deleted' => 0]);
    if (!$user) {
        $user = (object)['username' => $username, 'auth' => 'manual', 'confirmed' => 1, 'mnethostid' => $CFG->mnet_localhost_id,
            'firstname' => $name, 'lastname' => 'CloudLab', 'email' => $username . '@example.invalid',
            'emailstop' => 1, 'timezone' => 'Asia/Ho_Chi_Minh', 'country' => 'VN',
            'password' => substr(hash_hmac('sha256', $username, $initial['password']), 0, 32) . 'Aa7!'];
        $userid = user_create_user($user, true);
        $user = $DB->get_record('user', ['id' => $userid], '*', MUST_EXIST);
    }
    $users[$key] = $user;
}
unset($initial);
$courses = [];
$manual = enrol_get_plugin('manual');
$teacherrole = $DB->get_record('role', ['shortname' => 'editingteacher'], '*', MUST_EXIST);
$studentrole = $DB->get_record('role', ['shortname' => 'student'], '*', MUST_EXIST);
foreach (['CLOUD-C01', 'CLOUD-C02'] as $shortname) {
    $course = $DB->get_record('course', ['shortname' => $shortname]);
    if (!$course) {
        $course = create_course((object)['shortname' => $shortname, 'fullname' => $shortname . ' — Điện toán đám mây',
            'category' => 1, 'format' => 'topics', 'numsections' => 2, 'visible' => 1,
            'summary' => 'Private acceptance fixture for Moodle Cloud lab.', 'summaryformat' => FORMAT_HTML]);
    }
    $instances = enrol_get_instances($course->id, false);
    $instance = null;
    foreach ($instances as $candidate) {
        if ($candidate->enrol === 'guest') { $DB->set_field('enrol', 'status', ENROL_INSTANCE_DISABLED, ['id' => $candidate->id]); }
        if ($candidate->enrol === 'manual') { $instance = $candidate; }
    }
    if (!$instance) { $instanceid = $manual->add_instance($course); $instance = $DB->get_record('enrol', ['id' => $instanceid], '*', MUST_EXIST); }
    foreach ($shortname === 'CLOUD-C01' ? ['teacher', 'student_a', 'student_b'] : ['student_c'] as $key) {
        $manual->enrol_user($instance, $users[$key]->id, $key === 'teacher' ? $teacherrole->id : $studentrole->id);
    }
    $courses[$shortname] = $course;
}
$course = $courses['CLOUD-C01'];
\core\session\manager::set_user($users['teacher']);
require_capability('moodle/course:manageactivities', context_course::instance($course->id));
$fs = get_file_storage();
$resources = [];
foreach (['Học liệu tiếng Việt.txt' => "CLOUD-C01 private learning material — tiếng Việt\n", 'Dữ liệu nhị phân.bin' => "\x00\x01\x7f\xffCLOUD-BINARY\x00\n"] as $filename => $content) {
    $draft = file_get_unused_draft_itemid();
    $fs->create_file_from_string(['contextid' => context_user::instance($USER->id)->id, 'component' => 'user',
        'filearea' => 'draft', 'itemid' => $draft, 'filepath' => '/', 'filename' => $filename, 'sortorder' => 1], $content);
    $moduleinfo = (object)['modulename' => 'resource', 'module' => $DB->get_field('modules', 'id', ['name' => 'resource']),
        'section' => 0, 'name' => $filename, 'visible' => 1, 'cmidnumber' => '',
        'intro' => 'Private C01 learning material', 'introformat' => FORMAT_HTML, 'showdescription' => 1,
        'display' => RESOURCELIB_DISPLAY_DOWNLOAD, 'files' => $draft, 'showsize' => 1, 'showtype' => 1, 'showdate' => 1];
    $moduleinfo = add_moduleinfo($moduleinfo, $course);
    $contextid = context_module::instance($moduleinfo->coursemodule)->id;
    $resources[] = ['name' => $filename, 'cmid' => $moduleinfo->coursemodule, 'contextid' => $contextid,
        'sha256' => hash('sha256', $content), 'size' => strlen($content),
        'path' => '/pluginfile.php/' . $contextid . '/mod_resource/content/1/' . rawurlencode($filename)];
}
$moduleinfo = (object)['modulename' => 'assign', 'module' => $DB->get_field('modules', 'id', ['name' => 'assign']),
    'section' => 1, 'name' => 'Nộp bài triển khai Moodle Cloud', 'visible' => 1, 'cmidnumber' => '',
    'intro' => 'Submit one private file. Teacher grades each student separately.', 'introformat' => FORMAT_HTML,
    'submissiondrafts' => 1, 'requiresubmissionstatement' => 0, 'sendnotifications' => 0, 'sendlatenotifications' => 0,
    'sendstudentnotifications' => 0, 'duedate' => time() + 604800, 'cutoffdate' => 0, 'gradingduedate' => 0,
    'allowsubmissionsfromdate' => 0, 'grade' => 100, 'teamsubmission' => 0, 'requireallteammemberssubmit' => 0,
    'blindmarking' => 0, 'markingworkflow' => 0, 'markingallocation' => 0, 'alwaysshowdescription' => 1,
    'attemptreopenmethod' => ASSIGN_ATTEMPT_REOPEN_METHOD_NONE, 'maxattempts' => 1,
    'assignsubmission_file_enabled' => 1, 'assignsubmission_file_maxfiles' => 1,
    'assignsubmission_file_maxsizebytes' => 67108864, 'assignsubmission_file_filetypes' => '',
    'assignsubmission_onlinetext_enabled' => 0, 'assignfeedback_comments_enabled' => 1,
    'assignfeedback_file_enabled' => 0, 'assignfeedback_editpdf_enabled' => 0];
$moduleinfo = add_moduleinfo($moduleinfo, $course);
$cm = get_coursemodule_from_id('assign', $moduleinfo->coursemodule, $course->id, false, MUST_EXIST);
$context = context_module::instance($cm->id);
$assignment = new assign($context, $cm, $course);
$submissions = [];
foreach (['student_a', 'student_b'] as $key) {
    \core\session\manager::set_user($users[$key]);
    require_capability('mod/assign:submit', $context);
    if (has_capability('mod/assign:grade', $context)) { throw new RuntimeException('Student has grading capability'); }
    $filename = 'Bài nộp ' . strtoupper(substr($key, -1)) . '.txt';
    $content = 'PRIVATE-' . strtoupper($key) . '-SUBMISSION — Moodle Cloud lab.';
    $draft = file_get_unused_draft_itemid();
    $fs->create_file_from_string(['contextid' => context_user::instance($USER->id)->id, 'component' => 'user',
        'filearea' => 'draft', 'itemid' => $draft, 'filepath' => '/', 'filename' => $filename], $content);
    $notices = [];
    $data = (object)['files_filemanager' => $draft, 'submissionstatement' => 1];
    if (!$assignment->save_submission($data, $notices) || !$assignment->submit_for_grading($data, $notices)) {
        throw new RuntimeException('Submission failed: ' . implode('; ', $notices));
    }
    $submission = $assignment->get_user_submission($USER->id, false);
    $submissions[$key] = ['id' => $submission->id, 'userid' => $USER->id, 'sha256' => hash('sha256', $content),
        'path' => '/pluginfile.php/' . $context->id . '/assignsubmission_file/submission_files/' . $submission->id . '/' . rawurlencode($filename)];
}
\core\session\manager::set_user($users['teacher']);
foreach (['student_a' => 93, 'student_b' => 85] as $key => $score) {
    $data = (object)['grade' => (string)$score, 'attemptnumber' => 0, 'addattempt' => 0,
        'assignfeedbackcomments_editor' => ['text' => 'FEEDBACK-' . strtoupper($key) . '-OK', 'format' => FORMAT_HTML, 'itemid' => 0]];
    if (!$assignment->save_grade($users[$key]->id, $data)) { throw new RuntimeException('Grade not saved'); }
    $submissions[$key]['grade'] = $score;
}
$result = ['seeded_at' => gmdate('c'), 'courses' => array_map(fn($c) => (int)$c->id, $courses),
    'users' => array_map(fn($u) => ['id' => (int)$u->id, 'username' => $u->username], $users),
    'resources' => $resources, 'assignment' => ['id' => $moduleinfo->instance, 'cmid' => $cm->id, 'contextid' => $context->id],
    'submissions' => $submissions];
file_put_contents($manifestpath, json_encode($result, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE) . "\n");
chmod($manifestpath, 0660);
echo json_encode($result, JSON_UNESCAPED_UNICODE) . "\n";
