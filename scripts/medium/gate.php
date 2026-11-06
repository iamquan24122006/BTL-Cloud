<?php
// Enforce maintenance on EVERY PHP request, even if ALB fails open.
if (PHP_SAPI === 'cli') { return; }
ini_set('display_errors', '0');
try {
    $d = json_decode(@file_get_contents('/etc/moodle/deploy.json'), true, 512, JSON_THROW_ON_ERROR);
    $active = json_decode(@file_get_contents('/var/lib/moodledata/.distribution/active.json'), true, 512, JSON_THROW_ON_ERROR);
    $ok = is_file('/etc/moodle/mount-ok') && !is_file('/var/lib/moodledata/.distribution/blocked')
        && $active['release'] === $d['artifact']['release'];
} catch (Throwable $e) { $ok = false; }
if (!$ok) {
    http_response_code(503);
    header('Content-Type: text/plain; charset=utf-8');
    header('Cache-Control: no-store');
    header('Retry-After: 60');
    exit("Site temporarily unavailable. Please try again later.\n");
}
