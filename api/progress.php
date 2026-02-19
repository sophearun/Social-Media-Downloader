<?php
header('Content-Type: application/json');
require_once __DIR__ . '/../config/app.php';

$taskId = $_GET['task_id'] ?? '';

if (!$taskId || !preg_match('/^dl_[a-zA-Z0-9._]+$/', $taskId)) {
    echo json_encode(['error' => 'Invalid task ID']);
    exit;
}

$dlDir    = sys_get_temp_dir() . '/smd_downloads/' . $taskId;
$taskFile = $dlDir . '/task.json';

if (!file_exists($taskFile)) {
    echo json_encode(['status' => 'not_found']);
    exit;
}

$task  = json_decode(file_get_contents($taskFile), true);
$files = glob($dlDir . '/*') ?: [];

$completed = false;
$filename  = '';

foreach ($files as $f) {
    $base = basename($f);
    if ($base === 'task.json') continue;
    if (str_ends_with($base, '.part'))  continue;
    if (str_ends_with($base, '.ytdl'))  continue;
    // Non-partial, non-metadata file found — download complete
    $completed = true;
    $filename  = $base;
    break;
}

if ($completed) {
    echo json_encode([
        'status'       => 'complete',
        'filename'     => $filename,
        'download_url' => '/api/file.php?task_id=' . rawurlencode($taskId)
                        . '&file=' . rawurlencode($filename),
    ]);
} else {
    echo json_encode(['status' => 'downloading', 'percent' => 0]);
}
