<?php
/**
 * General helper functions.
 */

require_once __DIR__ . '/../config/app.php';

/** Escape output for HTML context. */
function sanitize(string $str): string {
    return htmlspecialchars($str, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

/** Format large numbers: 1200 → 1.2K, 3500000 → 3.5M */
function formatNumber(int|float $n): string {
    if ($n >= 1_000_000) return round($n / 1_000_000, 1) . 'M';
    if ($n >= 1_000)     return round($n / 1_000, 1) . 'K';
    return (string) $n;
}

/** Human-friendly relative time: "3 hours ago" */
function timeAgo(string $datetime): string {
    $diff = time() - strtotime($datetime);
    if ($diff < 60)          return 'just now';
    if ($diff < 3600)        return floor($diff / 60) . ' minutes ago';
    if ($diff < 86400)       return floor($diff / 3600) . ' hours ago';
    if ($diff < 604800)      return floor($diff / 86400) . ' days ago';
    if ($diff < 2592000)     return floor($diff / 604800) . ' weeks ago';
    if ($diff < 31536000)    return floor($diff / 2592000) . ' months ago';
    return floor($diff / 31536000) . ' years ago';
}

/** Create a URL-safe slug from any string. */
function slugify(string $str): string {
    $str = mb_strtolower(trim($str));
    $str = preg_replace('/[^a-z0-9\s-]/', '', $str);
    $str = preg_replace('/[\s-]+/', '-', $str);
    return trim($str, '-');
}

/** Generate an initials avatar URL via ui-avatars.com. */
function generateAvatar(string $name, int $size = 80): string {
    $name  = rawurlencode(trim($name) ?: 'User');
    return "https://ui-avatars.com/api/?name={$name}&size={$size}&background=8b5cf6&color=fff&bold=true";
}

/** Detect the social platform from a URL string. */
function detectPlatform(string $url): string {
    $u = strtolower($url);
    if (str_contains($u, 'tiktok.com'))                              return 'tiktok';
    if (str_contains($u, 'douyin.com'))                              return 'douyin';
    if (str_contains($u, 'youtube.com') || str_contains($u, 'youtu.be')) return 'youtube';
    if (str_contains($u, 'instagram.com'))                           return 'instagram';
    if (str_contains($u, 'facebook.com') || str_contains($u, 'fb.watch') || str_contains($u, 'fb.com')) return 'facebook';
    if (str_contains($u, 'twitter.com') || str_contains($u, 'x.com')) return 'twitter';
    if (str_contains($u, 'pinterest.com') || str_contains($u, 'pin.it')) return 'pinterest';
    if (str_contains($u, 'kuaishou.com') || str_contains($u, 'kwai.com')) return 'kuaishou';
    if ((str_contains($u, 'openai.com') && str_contains($u, 'sora')) || str_contains($u, 'sora.com')) return 'sora';
    if (str_contains($u, 'xiaohongshu.com') || str_contains($u, 'xhslink.com')) return 'xiaohongshu';
    if (str_contains($u, 'threads.net'))                             return 'threads';
    if (str_contains($u, 'linkedin.com'))                            return 'linkedin';
    if (str_contains($u, 'reddit.com') || str_contains($u, 'redd.it')) return 'reddit';
    if (str_contains($u, 'bilibili.com') || str_contains($u, 'b23.tv')) return 'bilibili';
    if (str_contains($u, 'weibo.com') || str_contains($u, 'weibo.cn')) return 'weibo';
    if (str_contains($u, 'lemon8'))                                  return 'lemon8';
    if (str_contains($u, 'zhihu.com'))                               return 'zhihu';
    if (str_contains($u, 'weixin.qq.com') || str_contains($u, 'mp.weixin')) return 'wechat';
    if (str_contains($u, 'pipix.com') || str_contains($u, 'pipixia')) return 'pipixia';
    return 'unknown';
}

/**
 * Call yt-dlp and return parsed JSON info.
 * Returns array on success, or ['error' => '...'] on failure.
 */
function callYtdlp(string $url, array $extraOpts = []): array {
    $escapedUrl = escapeshellarg($url);
    $cookies    = file_exists(COOKIES_FILE) ? '--cookies ' . escapeshellarg(COOKIES_FILE) : '';
    $opts       = implode(' ', array_map('escapeshellarg', $extraOpts));
    $cmd        = YTDLP_PATH . " --dump-json --no-playlist {$cookies} {$opts} {$escapedUrl} 2>&1";

    $output = shell_exec($cmd);
    if ($output === null) {
        return ['error' => 'yt-dlp execution failed.'];
    }

    // yt-dlp may print multiple JSON lines (playlist); take last valid one
    foreach (array_reverse(explode("\n", trim($output))) as $line) {
        $decoded = json_decode($line, true);
        if ($decoded && isset($decoded['title'])) {
            return $decoded;
        }
    }
    return ['error' => 'Could not parse yt-dlp output: ' . substr($output, 0, 400)];
}

/**
 * Return (and create if necessary) a per-task temporary download directory.
 * Task ID is validated before use.
 */
function getDownloadDir(string $taskId = ''): string {
    $base = DOWNLOAD_DIR;
    if (!is_dir($base)) {
        mkdir($base, 0700, true);
    }
    if ($taskId === '') return $base;

    // Only allow safe characters in task IDs
    if (!preg_match('/^dl_[a-zA-Z0-9._]+$/', $taskId)) {
        die(json_encode(['error' => 'Invalid task ID']));
    }
    $dir = $base . $taskId;
    if (!is_dir($dir)) {
        mkdir($dir, 0700, true);
    }
    return $dir;
}

/** Format seconds to HH:MM:SS or MM:SS */
function formatDuration(int $seconds): string {
    $h = intdiv($seconds, 3600);
    $m = intdiv($seconds % 3600, 60);
    $s = $seconds % 60;
    if ($h > 0) return sprintf('%d:%02d:%02d', $h, $m, $s);
    return sprintf('%d:%02d', $m, $s);
}
