<?php
// Explicit synthetic dev/staging benchmark only. Run inside the selected Moodle CLI.
define('CLI_SCRIPT', true);
// The root caller verifies deploy.json and runner role before setting this value.
$site = getenv('MOODLE_BENCHMARK_SITE');
if (!$site || ($argv[1] ?? '') !== $site || !preg_match('/^[a-z][a-z0-9-]+-(dev|staging)$/D', $site)) {
    throw new RuntimeException('Explicit selected dev/staging site confirmation required');
}
require '/var/www/moodle/config.php';
require_once($CFG->dirroot . '/user/lib.php');
require_once($CFG->dirroot . '/course/lib.php');
require_once($CFG->dirroot . '/course/modlib.php');
require_once($CFG->libdir . '/resourcelib.php');
require_once($CFG->dirroot . '/mod/assign/locallib.php');
\core\session\manager::set_user(get_admin());
$private = $CFG->dataroot . '/cloud-benchmark';
if (!is_dir($private)) { mkdir($private, 0700); }
$manifest = $private . '/manifest.json';
if (is_file($manifest)) {
    if (!is_file($private . '/users.csv')) { throw new RuntimeException('Missing private benchmark credentials'); }
    echo file_get_contents($manifest); exit(0);
}
// Fail closed on partial seed; do not reset another user's password or mutate a real course.
if ($DB->record_exists('course', ['shortname' => 'CLOUD-BENCHMARK']) || is_file($private . '/users.csv')) {
    throw new RuntimeException('Partial benchmark fixture requires operator review');
}
for ($i = 1; $i <= 50; $i++) {
    if ($DB->record_exists('user', ['username' => sprintf('cloudbench%03d', $i)])) {
        throw new RuntimeException('Benchmark username already exists');
    }
}
$course = create_course((object)['shortname' => 'CLOUD-BENCHMARK', 'fullname' => 'Cloud Benchmark Lab',
    'category' => 1, 'format' => 'topics', 'numsections' => 2, 'visible' => 1,
    'summary' => 'Synthetic protocol benchmark; 50 independent student accounts.', 'summaryformat' => FORMAT_HTML]);
$manual = enrol_get_plugin('manual');
$enrol = $DB->get_record('enrol', ['courseid' => $course->id, 'enrol' => 'manual']);
if (!$enrol) {
    $enrolid = $manual->add_instance($course);
    $enrol = $DB->get_record('enrol', ['id' => $enrolid], '*', MUST_EXIST);
}
foreach (enrol_get_instances($course->id, false) as $entry) {
    if ($entry->enrol === 'guest') { $DB->set_field('enrol', 'status', ENROL_INSTANCE_DISABLED, ['id' => $entry->id]); }
}
$role = $DB->get_record('role', ['shortname' => 'student'], '*', MUST_EXIST);
$rows = [];
for ($i = 1; $i <= 50; $i++) {
    $username = sprintf('cloudbench%03d', $i);
    $password = bin2hex(random_bytes(24)) . '!aA7';
    $id = user_create_user((object)['username' => $username, 'password' => $password, 'auth' => 'manual',
        'firstname' => 'Benchmark', 'lastname' => sprintf('%03d', $i), 'email' => $username . '@example.invalid',
        'emailstop' => 1, 'confirmed' => 1, 'mnethostid' => $CFG->mnet_localhost_id]);
    $manual->enrol_user($enrol, $id, $role->id);
    $rows[] = [$username, $password];
}
$content = str_repeat("Cloud benchmark synthetic file 0123456789\n", 26215);
$content = substr($content, 0, 1048576);
$draft = file_get_unused_draft_itemid();
get_file_storage()->create_file_from_string(['contextid' => context_user::instance($USER->id)->id,
    'component' => 'user', 'filearea' => 'draft', 'itemid' => $draft, 'filepath' => '/', 'filename' => 'benchmark.bin'], $content);
$resource = add_moduleinfo((object)['modulename' => 'resource', 'module' => $DB->get_field('modules', 'id', ['name' => 'resource']),
    'section' => 0, 'name' => 'Benchmark download', 'visible' => 1, 'cmidnumber' => '', 'intro' => 'Synthetic 1 MiB file',
    'introformat' => FORMAT_HTML, 'showdescription' => 1, 'display' => RESOURCELIB_DISPLAY_DOWNLOAD,
    'files' => $draft, 'showsize' => 1, 'showtype' => 1, 'showdate' => 1], $course);
$assignment = add_moduleinfo((object)['modulename' => 'assign', 'module' => $DB->get_field('modules', 'id', ['name' => 'assign']),
    'section' => 1, 'name' => 'Benchmark assignment', 'visible' => 1, 'cmidnumber' => '',
    'intro' => 'Synthetic read benchmark', 'introformat' => FORMAT_HTML, 'submissiondrafts' => 1,
    'requiresubmissionstatement' => 0, 'sendnotifications' => 0, 'sendlatenotifications' => 0,
    'sendstudentnotifications' => 0, 'duedate' => 0, 'cutoffdate' => 0, 'gradingduedate' => 0, 'allowsubmissionsfromdate' => 0,
    'grade' => 100, 'teamsubmission' => 0, 'requireallteammemberssubmit' => 0, 'blindmarking' => 0,
    'markingworkflow' => 0, 'markingallocation' => 0, 'alwaysshowdescription' => 1,
    'attemptreopenmethod' => 'none', 'maxattempts' => 1,
    'assignsubmission_file_enabled' => 1, 'assignsubmission_file_maxfiles' => 1, 'assignsubmission_file_maxsizebytes' => 1048576,
    'assignsubmission_onlinetext_enabled' => 0, 'assignfeedback_comments_enabled' => 1], $course);
$csv = fopen($private . '/users.csv', 'x');
chmod($private . '/users.csv', 0600);
fputcsv($csv, ['username', 'password']);
foreach ($rows as $row) { fputcsv($csv, $row); }
fclose($csv);
$context = context_module::instance($resource->coursemodule);
$result = ['course_id' => (int)$course->id, 'course_marker' => 'Cloud Benchmark Lab', 'users' => 50,
    'file_path' => '/pluginfile.php/' . $context->id . '/mod_resource/content/1/benchmark.bin',
    'file_sha256' => hash('sha256', $content), 'file_bytes' => strlen($content),
    'assignment_id' => (int)$assignment->coursemodule, 'assignment_marker' => 'Benchmark assignment'];
file_put_contents($manifest, json_encode($result, JSON_THROW_ON_ERROR) . "\n");
chmod($manifest, 0600);
echo file_get_contents($manifest);
