<?php
header('Content-Type: application/json');
require_once __DIR__ . '/../config/app.php';
require_once __DIR__ . '/../includes/functions.php';

$data   = json_decode(file_get_contents('php://input'), true);
$url    = trim($data['url']    ?? '');
$type   = $data['type']        ?? 'video'; // 'video' | 'audio'
$taskId = 'dl_' . bin2hex(random_bytes(8));

if (!$url) {
    echo json_encode(['error' => 'Please enter a URL']);
    exit;
}

$dlDir      = getDownloadDir($taskId);
$escapedUrl = escapeshellarg($url);
$escapedDir = escapeshellarg($dlDir);
$cookies    = file_exists(COOKIES_FILE) ? '--cookies ' . escapeshellarg(COOKIES_FILE) : '';

if ($type === 'audio') {
    $cmd = YTDLP_PATH . " -x --audio-format mp3 --audio-quality 192K"
         . " {$cookies} -o {$escapedDir}/%(title)s.%(ext)s {$escapedUrl}"
         . " > /dev/null 2>&1 &";
} else {
    $cmd = YTDLP_PATH . " -f 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'"
         . " {$cookies} -o {$escapedDir}/%(title)s.%(ext)s {$escapedUrl}"
         . " > /dev/null 2>&1 &";
}

shell_exec($cmd);

file_put_contents($dlDir . '/task.json', json_encode([
    'task_id'    => $taskId,
    'url'        => $url,
    'type'       => $type,
    'status'     => 'downloading',
    'started_at' => time(),
]));

echo json_encode(['task_id' => $taskId, 'status' => 'downloading']);
