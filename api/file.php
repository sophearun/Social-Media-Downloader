<?php
require_once __DIR__ . '/../config/app.php';

$taskId   = $_GET['task_id'] ?? '';
$filename = $_GET['file']    ?? '';

// Validate task ID
if (!$taskId || !preg_match('/^dl_[a-zA-Z0-9._]+$/', $taskId)) {
    http_response_code(400);
    die('Invalid task ID.');
}

// basename() prevents path traversal
$filename = basename($filename);
if (!$filename) {
    http_response_code(400);
    die('Invalid filename.');
}

$filepath = sys_get_temp_dir() . '/smd_downloads/' . $taskId . '/' . $filename;

// Resolve real path and ensure it stays inside the expected directory
$realpath = realpath($filepath);
$baseDir  = realpath(sys_get_temp_dir() . '/smd_downloads/' . $taskId);

if ($realpath === false || $baseDir === false || strpos($realpath, $baseDir . DIRECTORY_SEPARATOR) !== 0) {
    http_response_code(403);
    die('Access denied.');
}

if (!is_file($realpath)) {
    http_response_code(404);
    die('File not found.');
}

$mime = mime_content_type($realpath) ?: 'application/octet-stream';
$safe = rawurlencode($filename);

header('Content-Type: ' . $mime);
header('Content-Disposition: attachment; filename="' . addslashes($filename) . '"; filename*=UTF-8\'\'' . $safe);
header('Content-Length: ' . filesize($realpath));
header('X-Content-Type-Options: nosniff');
readfile($realpath);
