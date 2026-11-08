<?php
// CLI-only security acceptance. Passwords are read from a protected runtime file.
if (PHP_SAPI !== 'cli') {
    http_response_code(404);
    exit;
}
define('CLI_SCRIPT', true);
require('/var/www/moodle/config.php');

function rotation_assert(bool $condition, string $message): void {
    if (!$condition) {
        throw new RuntimeException($message);
    }
}

$settings = json_decode(file_get_contents('/etc/moodle/admin-rotation.json'), true, 512, JSON_THROW_ON_ERROR);
rotation_assert(isset($settings['oldpass'], $settings['newpass']), 'Rotation settings missing');
rotation_assert(is_string($settings['oldpass']) && is_string($settings['newpass']), 'Rotation settings invalid');
rotation_assert(!hash_equals($settings['oldpass'], $settings['newpass']), 'Rotation needs a new credential');
$admin = get_admin();
rotation_assert($admin->username === 'admin' && $admin->auth === 'manual', 'Unexpected administrator identity');
if (!validate_internal_user_password($admin, $settings['newpass'])) {
    rotation_assert(validate_internal_user_password($admin, $settings['oldpass']),
                    'Known administrator credential does not match; refusing rotation');
    rotation_assert(update_internal_user_password($admin, $settings['newpass']), 'Password update failed');
}
$admin = $DB->get_record('user', ['id' => $admin->id], '*', MUST_EXIST);
rotation_assert(validate_internal_user_password($admin, $settings['newpass']), 'New credential not verified');
rotation_assert(!validate_internal_user_password($admin, $settings['oldpass']), 'Old credential still valid');
\core\session\manager::kill_user_sessions($admin->id);
echo json_encode(['admin_rotation_verified' => true, 'old_password_rejected' => true,
                  'existing_admin_sessions_revoked' => true], JSON_THROW_ON_ERROR) . "\n";
