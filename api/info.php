<?php
header('Content-Type: application/json');
require_once __DIR__ . '/../config/app.php';
require_once __DIR__ . '/../includes/functions.php';

$data = json_decode(file_get_contents('php://input'), true);
$url  = trim($data['url'] ?? '');

if (!$url) {
    echo json_encode(['error' => 'Please enter a URL']);
    exit;
}

$info = callYtdlp($url);

if (isset($info['error'])) {
    echo json_encode(['error' => $info['error']]);
    exit;
}

// Build format list (video-containing streams only)
$formats = [];
foreach (($info['formats'] ?? []) as $f) {
    if (($f['vcodec'] ?? 'none') !== 'none') {
        $formats[] = [
            'format_id'   => $f['format_id']   ?? '',
            'ext'         => $f['ext']          ?? 'mp4',
            'resolution'  => $f['resolution']   ?? 'N/A',
            'filesize'    => $f['filesize']      ?? 0,
            'has_video'   => true,
            'has_audio'   => ($f['acodec'] ?? 'none') !== 'none',
            'quality'     => $f['quality']      ?? 0,
            'format_note' => $f['format_note']  ?? '',
        ];
    }
}

$thumbnail = $info['thumbnail'] ?? '';
if (!$thumbnail && !empty($info['thumbnails'])) {
    $thumbnail = end($info['thumbnails'])['url'] ?? '';
}

echo json_encode([
    'title'         => substr($info['title']       ?? 'Video', 0, 200),
    'description'   => substr($info['description'] ?? '',       0, 500),
    'thumbnail'     => $thumbnail,
    'duration'      => $info['duration']      ?? 0,
    'author'        => $info['uploader']      ?? $info['channel'] ?? 'Unknown',
    'view_count'    => $info['view_count']    ?? 0,
    'like_count'    => $info['like_count']    ?? 0,
    'comment_count' => $info['comment_count'] ?? 0,
    'formats'       => $formats,
    'url'           => $url,
    'platform'      => detectPlatform($url),
    'upload_date'   => $info['upload_date']   ?? '',
    'is_photo'      => !($info['duration']    ?? 0),
]);
