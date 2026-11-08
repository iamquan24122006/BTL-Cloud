<?php
// Synthetic integration data only. Cloud seeding requires an explicitly selected empty lab.
define('CLI_SCRIPT', true);
require '/var/www/moodle/config.php';
require_once($CFG->dirroot . '/course/lib.php');
require_once($CFG->dirroot . '/course/modlib.php');
require_once($CFG->dirroot . '/user/lib.php');
require_once($CFG->libdir . '/enrollib.php');
require_once($CFG->libdir . '/filelib.php');
require_once($CFG->dirroot . '/mod/assign/locallib.php');

function ensure_check($condition, $message) {
    if (!$condition) {
        throw new RuntimeException($message);
    }
}

$settingspath = file_exists('/etc/moodle/acceptance.json') ? '/etc/moodle/acceptance.json' : '/etc/moodle/bootstrap.json';
$settings = json_decode(file_get_contents($settingspath), true, 512, JSON_THROW_ON_ERROR);
$mode = $argv[1] ?? '';
$payload = "Moodle Cloud integration fixture\nUTF-8: học tập trên cloud\n";
$admin = get_admin();
\core\session\manager::set_user($admin);

if ($mode === 'seed') {
    ensure_check($DB->count_records('course') === 1, 'Seed requires an empty lab with only the site course');
    // Finish the initial site profile without invoking the interactive admin wizard.
    $admin->firstname = 'Cloud';
    $admin->lastname = 'Administrator';
    $admin->city = 'Lab';
    $admin->country = 'VN';
    user_update_user($admin, false, false);
    set_config('registerauth', '');
    set_config('noemailever', 1);
    set_config('updateautocheck', 0);
    set_config('enablecompletion', 0);
    $category = $DB->get_record('course_categories', ['parent' => 0], '*', MUST_EXIST);
    $course = create_course((object)[
        'fullname' => 'Cloud Integration Lab', 'shortname' => 'CLOUD-INTEGRATION',
        'category' => $category->id, 'format' => 'topics', 'visible' => 1,
        'enablecompletion' => 0, 'numsections' => 1,
    ]);
    $manual = enrol_get_plugin('manual');
    $instances = enrol_get_instances($course->id, false);
    $instance = null;
    foreach ($instances as $candidate) {
        if ($candidate->enrol === 'manual') { $instance = $candidate; break; }
    }
    if (!$instance) {
        $id = $manual->add_instance($course);
        $instance = $DB->get_record('enrol', ['id' => $id], '*', MUST_EXIST);
    }
    $ids = [];
    foreach (['student' => 'student', 'studentb' => 'student', 'outsider' => 'student',
              'teacher' => 'editingteacher'] as $username => $rolename) {
        $ids[$username] = user_create_user((object)[
            'username' => $username, 'password' => $settings[$username . 'pass'], 'auth' => 'manual',
            'confirmed' => 1, 'mnethostid' => $CFG->mnet_localhost_id,
            'firstname' => ucfirst($username), 'lastname' => 'Fixture',
            'email' => $username . '@example.invalid', 'city' => 'Lab', 'country' => 'VN',
        ]);
        $role = $DB->get_record('role', ['shortname' => $rolename], '*', MUST_EXIST);
        if ($username !== 'outsider') {
            $manual->enrol_user($instance, $ids[$username], $role->id);
        }
    }
    $fs = get_file_storage();
    $draftid = file_get_unused_draft_itemid();
    $fs->create_file_from_string([
        'contextid' => context_user::instance($admin->id)->id, 'component' => 'user',
        'filearea' => 'draft', 'itemid' => $draftid, 'filepath' => '/', 'filename' => 'fixture.txt',
    ], $payload);
    $module = $DB->get_record('modules', ['name' => 'resource'], '*', MUST_EXIST);
    $resource = add_moduleinfo((object)[
        'module' => $module->id, 'modulename' => 'resource', 'name' => 'Fixture download',
        'intro' => '', 'introformat' => FORMAT_HTML, 'section' => 0, 'visible' => 1,
        'visibleoncoursepage' => 1, 'showdescription' => 0, 'files' => $draftid,
        'display' => 0, 'printintro' => 1, 'completion' => 0,
    ], $course);
    $othercourse = create_course((object)[
        'fullname' => 'Other Private Course', 'shortname' => 'CLOUD-OTHER',
        'category' => $category->id, 'format' => 'topics', 'visible' => 1,
    ]);
    $otherinstance = $DB->get_record('enrol', ['courseid' => $othercourse->id, 'enrol' => 'manual']);
    if (!$otherinstance) {
        $otherenrol = $manual->add_instance($othercourse);
        $otherinstance = $DB->get_record('enrol', ['id' => $otherenrol], '*', MUST_EXIST);
    }
    $studentrole = $DB->get_record('role', ['shortname' => 'student'], '*', MUST_EXIST);
    $manual->enrol_user($otherinstance, $ids['outsider'], $studentrole->id);
    $module = $DB->get_record('modules', ['name' => 'assign'], '*', MUST_EXIST);
    $assignment = add_moduleinfo((object)[
        'module' => $module->id, 'modulename' => 'assign', 'name' => 'Cloud Recovery Assignment',
        'intro' => 'Submit your private lab report.', 'introformat' => FORMAT_HTML,
        'section' => 0, 'visible' => 1, 'visibleoncoursepage' => 1, 'showdescription' => 0,
        'completion' => 0, 'grade' => 100, 'alwaysshowdescription' => 1,
        'allowsubmissionsfromdate' => 0, 'duedate' => time() + 604800, 'cutoffdate' => 0,
        'gradingduedate' => 0, 'submissiondrafts' => 0, 'requiresubmissionstatement' => 0,
        'sendnotifications' => 0, 'sendlatenotifications' => 0, 'sendstudentnotifications' => 0,
        'teamsubmission' => 0, 'requireallteammemberssubmit' => 0, 'teamsubmissiongroupingid' => 0,
        'blindmarking' => 0, 'hidegrader' => 0, 'markingworkflow' => 0, 'markingallocation' => 0,
        'attemptreopenmethod' => 'none', 'maxattempts' => -1,
        'assignsubmission_file_enabled' => 1, 'assignsubmission_file_maxfiles' => 2,
        'assignsubmission_file_maxsizebytes' => 1048576,
        'assignsubmission_onlinetext_enabled' => 0, 'assignfeedback_comments_enabled' => 1,
    ], $course);
    $assignmentcontext = context_module::instance($assignment->coursemodule);
    $assigncm = get_coursemodule_from_id('assign', $assignment->coursemodule, $course->id, false, MUST_EXIST);
    foreach (['student' => 87, 'studentb' => 93] as $username => $mark) {
        $user = $DB->get_record('user', ['id' => $ids[$username]], '*', MUST_EXIST);
        \core\session\manager::set_user($user);
        $draft = file_get_unused_draft_itemid();
        $fs->create_file_from_string([
            'contextid' => context_user::instance($user->id)->id, 'component' => 'user',
            'filearea' => 'draft', 'itemid' => $draft, 'filepath' => '/', 'filename' => 'Bài nộp ' . $username . '.txt',
        ], 'Private submission: ' . $username . "\n");
        $assign = new assign($assignmentcontext, $assigncm, $course);
        $notices = [];
        ensure_check($assign->save_submission((object)['files_filemanager' => $draft], $notices),
                     'Assignment submission failed for ' . $username);
        \core\session\manager::set_user($DB->get_record('user', ['id' => $ids['teacher']], '*', MUST_EXIST));
        $assign = new assign($assignmentcontext, $assigncm, $course);
        ensure_check($assign->save_grade($user->id, (object)[
            'grade' => (string)$mark, 'attemptnumber' => -1, 'addattempt' => 0,
            'assignfeedbackcomments_editor' => ['text' => 'Reviewed ' . $username, 'format' => FORMAT_HTML],
            'sendstudentnotifications' => 0,
        ]), 'Assignment grading failed');
    }
    \core\session\manager::set_user($admin);
    echo json_encode(['course_id' => (int)$course->id, 'users' => $ids,
                      'resource_id' => (int)$resource->coursemodule,
                      'file_sha256' => hash('sha256', $payload)], JSON_THROW_ON_ERROR) . "\n";
    exit(0);
}

$course = $DB->get_record('course', ['shortname' => 'CLOUD-INTEGRATION'], '*', MUST_EXIST);
$student = $DB->get_record('user', ['username' => 'student'], '*', MUST_EXIST);
$teacher = $DB->get_record('user', ['username' => 'teacher'], '*', MUST_EXIST);
$studentb = $DB->get_record('user', ['username' => 'studentb'], '*', MUST_EXIST);
$outsider = $DB->get_record('user', ['username' => 'outsider'], '*', MUST_EXIST);
$context = context_course::instance($course->id);
ensure_check(is_enrolled($context, $student->id, '', true), 'Student enrolment missing');
ensure_check(is_enrolled($context, $teacher->id, '', true), 'Teacher enrolment missing');
ensure_check(has_capability('moodle/course:update', $context, $teacher->id), 'Teacher role missing');
ensure_check(!has_capability('moodle/course:update', $context, $student->id), 'Student has teacher privileges');
ensure_check(!is_enrolled($context, $outsider->id, '', true), 'Outsider is enrolled in the private course');
ensure_check(!is_writable('/var/www/moodle/config.php'), 'Application config is writable');
ensure_check(is_writable($CFG->dataroot), 'Dataroot is not writable');
$dbversion = (int)$DB->get_field_sql('SHOW server_version_num');
ensure_check($dbversion >= 160000 && $dbversion < 170000, 'PostgreSQL 16 required');
require($CFG->dirroot . '/version.php');
ensure_check(str_starts_with($release, '4.5.15'), 'Moodle version mismatch');

if ($mode === 'write') {
    $content = "Post-restore write succeeded\n";
    $file = get_file_storage()->create_file_from_string([
        'contextid' => context_user::instance($student->id)->id, 'component' => 'user',
        'filearea' => 'private', 'itemid' => 0, 'filepath' => '/', 'filename' => 'after-restore.txt',
    ], $content);
    ensure_check($file->get_content() === $content, 'Restored file storage cannot write');
    echo json_encode(['write_read_sha256' => hash('sha256', $file->get_content())], JSON_THROW_ON_ERROR) . "\n";
    exit(0);
}
ensure_check($mode === 'verify', 'Unknown integration mode');
$cm = get_coursemodule_from_instance('resource', $DB->get_field('resource', 'id', ['course' => $course->id]),
                                    $course->id, false, MUST_EXIST);
$filecontext = context_module::instance($cm->id);
$file = get_file_storage()->get_file($filecontext->id, 'mod_resource', 'content', 0, '/', 'fixture.txt');
ensure_check($file && $file->get_content() === $payload, 'Stored file differs');
$url = moodle_url::make_pluginfile_url($filecontext->id, 'mod_resource', 'content', 0, '/', 'fixture.txt')->out(false);
$assignrecord = $DB->get_record('assign', ['course' => $course->id], '*', MUST_EXIST);
$assigncm = get_coursemodule_from_instance('assign', $assignrecord->id, $course->id, false, MUST_EXIST);
$assigncontext = context_module::instance($assigncm->id);
$submissions = [];
foreach (['student' => [$student, 87], 'studentb' => [$studentb, 93]] as $username => [$user, $mark]) {
    $assignment = new assign($assigncontext, $assigncm, $course);
    $submission = $assignment->get_user_submission($user->id, false);
    ensure_check($submission && $submission->status === ASSIGN_SUBMISSION_STATUS_SUBMITTED, 'Submission missing');
    $file = get_file_storage()->get_file($assigncontext->id, 'assignsubmission_file', 'submission_files',
                                       $submission->id, '/', 'Bài nộp ' . $username . '.txt');
    $content = 'Private submission: ' . $username . "\n";
    ensure_check($file && $file->get_content() === $content, 'Submission content differs');
    $grade = $assignment->get_user_grade($user->id, false);
    ensure_check($grade && (float)$grade->grade === (float)$mark, 'Stored grade differs');
    $feedback = $DB->get_record('assignfeedback_comments', ['grade' => $grade->id], '*', MUST_EXIST);
    ensure_check($feedback->commenttext === 'Reviewed ' . $username, 'Feedback differs');
    $submissions[$username] = ['hash' => hash('sha256', $content), 'content' => $content,
        'url' => moodle_url::make_pluginfile_url($assigncontext->id, 'assignsubmission_file',
                    'submission_files', $submission->id, '/', 'Bài nộp ' . $username . '.txt')->out(false)];
    \core\session\manager::set_user($user);
    $assignment = new assign($assigncontext, $assigncm, $course);
    ensure_check($assignment->can_view_submission($user->id), 'Student cannot view own submission');
    ensure_check(!$assignment->can_view_submission($username === 'student' ? $studentb->id : $student->id),
                 'Student can view another submission');
    ensure_check(!has_capability('mod/assign:grade', $assigncontext), 'Student can grade assignments');
    \core\session\manager::set_user($admin);
}

function new_browser() {
    $curl = curl_init();
    curl_setopt($curl, CURLOPT_COOKIEFILE, '');
    return $curl;
}

function browser_request($curl, $url, $fields = null) {
    curl_setopt_array($curl, [CURLOPT_URL => $url, CURLOPT_RETURNTRANSFER => true,
        CURLOPT_FOLLOWLOCATION => true, CURLOPT_MAXREDIRS => 10, CURLOPT_CONNECTTIMEOUT => 5,
        CURLOPT_TIMEOUT => 45]);
    if ($fields === null) {
        curl_setopt($curl, CURLOPT_HTTPGET, true);
    } else {
        // Moodle sets arg_separator.output for HTML; form bodies need literal '&'.
        curl_setopt($curl, CURLOPT_POSTFIELDS, http_build_query($fields, '', '&'));
    }
    $body = curl_exec($curl);
    ensure_check($body !== false, 'HTTP request failed: ' . curl_error($curl));
    return ['status' => curl_getinfo($curl, CURLINFO_RESPONSE_CODE), 'body' => $body,
            'url' => curl_getinfo($curl, CURLINFO_EFFECTIVE_URL)];
}

for ($attempt = 0; $attempt < 30; $attempt++) {
    $socket = @fsockopen('127.0.0.1', 8080, $errno, $errstr, 1);
    if ($socket) { fclose($socket); break; }
    sleep(1);
}
$guest = new_browser();
$anonymous = browser_request($guest, $url);
ensure_check($anonymous['body'] !== $payload, 'Anonymous access to private course file');
curl_close($guest);
foreach (['admin' => $admin, 'student' => $student, 'studentb' => $studentb, 'teacher' => $teacher,
          'outsider' => $outsider] as $username => $user) {
    $browser = new_browser();
    $login = browser_request($browser, $CFG->wwwroot . '/login/index.php');
    $document = new DOMDocument();
    @$document->loadHTML($login['body']);
    $tokens = (new DOMXPath($document))->query('//form[@id="login"]//input[@name="logintoken"]');
    ensure_check($tokens->length === 1, 'Login form CSRF token missing');
    browser_request($browser, $CFG->wwwroot . '/login/index.php', [
        'username' => $username, 'password' => $settings[$username . 'pass'],
        'logintoken' => $tokens->item(0)->getAttribute('value'),
    ]);
    $page = browser_request($browser, $CFG->wwwroot . '/course/view.php?id=' . $course->id);
    if ($username === 'outsider') {
        $denied = browser_request($browser, $url);
        ensure_check($denied['body'] !== $payload, 'Unenrolled user downloaded private course file');
        foreach ($submissions as $submission) {
            $denied = browser_request($browser, $submission['url']);
            ensure_check($denied['body'] !== $submission['content'], 'Outsider downloaded a submission');
        }
        curl_close($browser);
        continue;
    }
    $cookiecount = count(curl_getinfo($browser, CURLINFO_COOKIELIST));
    ensure_check($page['status'] === 200 && str_contains($page['body'], 'Cloud Integration Lab')
        && !str_contains($page['url'], '/login/'), $username . ' HTTP login/course access failed; '
        . 'HTTP=' . $page['status'] . ', path=' . parse_url($page['url'], PHP_URL_PATH) . ', cookies=' . $cookiecount);
    $download = browser_request($browser, $url);
    ensure_check($download['status'] === 200 && $download['body'] === $payload,
                 $username . ' authenticated download differs');
    foreach ($submissions as $owner => $submission) {
        $download = browser_request($browser, $submission['url']);
        if (in_array($username, ['admin', 'teacher', $owner], true)) {
            ensure_check($download['status'] === 200 && $download['body'] === $submission['content'],
                         'Authorized submission download differs');
        } else {
            ensure_check($download['body'] !== $submission['content'], 'Student downloaded another submission');
        }
    }
    $profile = browser_request($browser, $CFG->wwwroot . '/user/profile.php?id=' . $user->id);
    $document = new DOMDocument();
    @$document->loadHTML($profile['body']);
    $links = (new DOMXPath($document))->query('//a[contains(@href,"/login/logout.php") and contains(@href,"sesskey=")]');
    ensure_check($links->length > 0, 'Logout link with CSRF token missing');
    browser_request($browser, html_entity_decode($links->item(0)->getAttribute('href')));
    $denied = browser_request($browser, $url);
    ensure_check($denied['body'] !== $payload, 'Logged-out session still downloads private file');
    curl_close($browser);
}
$probe = new_browser();
foreach (['/config.php', '/.git/config'] as $path) {
    $response = browser_request($probe, $CFG->wwwroot . $path);
    ensure_check(in_array($response['status'], [403, 404], true), 'Sensitive path not blocked');
}
curl_close($probe);
echo json_encode([
    'moodle' => $release, 'php' => PHP_VERSION, 'postgres' => $dbversion,
    'course_id' => (int)$course->id, 'student_id' => (int)$student->id, 'teacher_id' => (int)$teacher->id,
    'file_sha256' => hash('sha256', $payload), 'http_logins' => ['admin', 'student', 'studentb', 'teacher'],
    'file_path' => parse_url($url, PHP_URL_PATH),
    'submissions_and_grades' => true, 'private_submission_access' => true, 'logout' => true,
    'enrolments_and_roles' => true, 'anonymous_file_denied' => true, 'protected_paths' => true,
], JSON_THROW_ON_ERROR) . "\n";
