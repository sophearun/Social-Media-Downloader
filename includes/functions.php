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
function formatNumber($n): string {
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
    if (strpos($u, 'tiktok.com') !== false)                                       return 'tiktok';
    if (strpos($u, 'douyin.com') !== false)                                       return 'douyin';
    if (strpos($u, 'youtube.com') !== false || strpos($u, 'youtu.be') !== false)  return 'youtube';
    if (strpos($u, 'instagram.com') !== false)                                    return 'instagram';
    if (strpos($u, 'facebook.com') !== false || strpos($u, 'fb.watch') !== false || strpos($u, 'fb.com') !== false) return 'facebook';
    if (strpos($u, 'twitter.com') !== false || strpos($u, 'x.com') !== false)     return 'twitter';
    if (strpos($u, 'pinterest.com') !== false || strpos($u, 'pin.it') !== false)  return 'pinterest';
    if (strpos($u, 'kuaishou.com') !== false || strpos($u, 'kwai.com') !== false) return 'kuaishou';
    if ((strpos($u, 'openai.com') !== false && strpos($u, 'sora') !== false) || strpos($u, 'sora.com') !== false) return 'sora';
    if (strpos($u, 'xiaohongshu.com') !== false || strpos($u, 'xhslink.com') !== false) return 'xiaohongshu';
    if (strpos($u, 'threads.net') !== false)                                      return 'threads';
    if (strpos($u, 'linkedin.com') !== false)                                     return 'linkedin';
    if (strpos($u, 'reddit.com') !== false || strpos($u, 'redd.it') !== false)   return 'reddit';
    if (strpos($u, 'bilibili.com') !== false || strpos($u, 'b23.tv') !== false)  return 'bilibili';
    if (strpos($u, 'weibo.com') !== false || strpos($u, 'weibo.cn') !== false)   return 'weibo';
    if (strpos($u, 'lemon8') !== false)                                           return 'lemon8';
    if (strpos($u, 'zhihu.com') !== false)                                        return 'zhihu';
    if (strpos($u, 'weixin.qq.com') !== false || strpos($u, 'mp.weixin') !== false) return 'wechat';
    if (strpos($u, 'pipix.com') !== false || strpos($u, 'pipixia') !== false)    return 'pipixia';
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
