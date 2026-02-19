"""
Social Media Downloader — Multi-Platform
==========================================
គាំទ្រ: TikTok, Douyin, YouTube, Instagram, Facebook, X (Twitter), Pinterest, Kuaishou
Features: Profile Grabber, Analytics, Bulk Download, Comments, Search, Watermark Removal
"""

import os, re, json, uuid, time, threading, traceback, shutil, tempfile, sqlite3, logging, subprocess
import httpx
from flask import Flask, render_template, request, jsonify, send_file
from yt_dlp import YoutubeDL
try:
    from curl_cffi import requests as cffi_requests
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False

# ==================== FFmpeg Integration ====================
def get_ffmpeg_path():
    """Get FFmpeg binary path. Tries static_ffmpeg first, then system PATH."""
    # Try static_ffmpeg (pip installed)
    try:
        import static_ffmpeg
        ff, fp = static_ffmpeg.run.get_or_fetch_platform_executables_else_raise()
        return {'ffmpeg': ff, 'ffprobe': fp, 'dir': os.path.dirname(ff)}
    except Exception:
        pass
    # Try system PATH
    for name in ('ffmpeg', 'ffmpeg.exe'):
        for d in os.environ.get('PATH', '').split(os.pathsep):
            p = os.path.join(d, name)
            if os.path.isfile(p):
                return {'ffmpeg': p, 'ffprobe': os.path.join(d, name.replace('ffmpeg', 'ffprobe')), 'dir': d}
    return None

FFMPEG_PATHS = get_ffmpeg_path()
HAS_FFMPEG = FFMPEG_PATHS is not None
if HAS_FFMPEG:
    logging.info(f"FFmpeg found: {FFMPEG_PATHS['ffmpeg']}")
else:
    logging.warning("FFmpeg not found — audio extraction and format merging will be limited")


def ffmpeg_run(args, timeout=300):
    """Run an FFmpeg command and return (success, stdout, stderr)."""
    if not HAS_FFMPEG:
        return False, '', 'FFmpeg not installed'
    cmd = [FFMPEG_PATHS['ffmpeg']] + args
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode == 0, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return False, '', 'FFmpeg timed out'
    except Exception as e:
        return False, '', str(e)


def ffprobe_run(args, timeout=60):
    """Run FFprobe and return parsed JSON output."""
    if not HAS_FFMPEG:
        return None
    cmd = [FFMPEG_PATHS['ffprobe'], '-v', 'quiet', '-print_format', 'json'] + args
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if r.returncode == 0:
            return json.loads(r.stdout)
    except Exception:
        pass
    return None


def ffmpeg_get_media_info(filepath):
    """Get media file info (duration, resolution, codecs, bitrate, size)."""
    info = ffprobe_run(['-show_format', '-show_streams', filepath])
    if not info:
        return None
    fmt = info.get('format', {})
    streams = info.get('streams', [])
    video_stream = next((s for s in streams if s.get('codec_type') == 'video'), {})
    audio_stream = next((s for s in streams if s.get('codec_type') == 'audio'), {})
    duration = float(fmt.get('duration', 0))
    return {
        'duration': round(duration, 2),
        'size': int(fmt.get('size', 0)),
        'bitrate': int(fmt.get('bit_rate', 0)),
        'format_name': fmt.get('format_name', ''),
        'video_codec': video_stream.get('codec_name', ''),
        'video_width': int(video_stream.get('width', 0)),
        'video_height': int(video_stream.get('height', 0)),
        'video_fps': eval(video_stream['r_frame_rate']) if video_stream.get('r_frame_rate') and '/' in str(video_stream.get('r_frame_rate', '')) else 0,
        'audio_codec': audio_stream.get('codec_name', ''),
        'audio_sample_rate': int(audio_stream.get('sample_rate', 0)),
        'audio_channels': int(audio_stream.get('channels', 0)),
    }


def ffmpeg_convert(input_path, output_path, options=None):
    """Convert media file using FFmpeg.
    options: dict with keys like format, video_codec, audio_codec, resolution, bitrate, quality
    """
    if not HAS_FFMPEG:
        return False, 'FFmpeg not installed'
    opts = options or {}
    args = ['-i', input_path, '-y']  # -y = overwrite

    # Video codec
    vcodec = opts.get('video_codec', '')
    if vcodec == 'copy':
        args += ['-c:v', 'copy']
    elif vcodec:
        args += ['-c:v', vcodec]

    # Audio codec
    acodec = opts.get('audio_codec', '')
    if acodec == 'copy':
        args += ['-c:a', 'copy']
    elif acodec:
        args += ['-c:a', acodec]

    # Resolution scaling
    resolution = opts.get('resolution', '')
    if resolution:
        res_map = {'360p': '640:360', '480p': '854:480', '720p': '1280:720', '1080p': '1920:1080', '1440p': '2560:1440', '4k': '3840:2160'}
        scale = res_map.get(resolution, resolution)
        args += ['-vf', f'scale={scale}:force_original_aspect_ratio=decrease,pad={scale}:(ow-iw)/2:(oh-ih)/2']

    # Audio quality
    audio_quality = opts.get('audio_quality', '')
    if audio_quality:
        args += ['-b:a', audio_quality]

    # Video quality (CRF)
    crf = opts.get('crf', '')
    if crf:
        args += ['-crf', str(crf)]

    # Video bitrate
    vbitrate = opts.get('video_bitrate', '')
    if vbitrate:
        args += ['-b:v', vbitrate]

    # Audio only (no video)
    if opts.get('audio_only'):
        args += ['-vn']

    # Video only (no audio)
    if opts.get('video_only'):
        args += ['-an']

    args.append(output_path)
    ok, stdout, stderr = ffmpeg_run(args, timeout=opts.get('timeout', 600))
    if ok and os.path.isfile(output_path):
        return True, output_path
    return False, stderr

app = Flask(__name__)

# ==================== Configuration ====================
DOWNLOAD_FOLDER = r'D:\Downloads'
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

API_BASE_URL = "https://api.tikhub.io"
TIKHUB_API_KEY = os.environ.get('TIKHUB_API_KEY', '')  # Set your TikHub API key here or via env var

# Bakong KHQR Donate Config
BAKONG_TOKEN = os.environ.get('BAKONG_TOKEN', 'c79641eb29bd57e0f4ca4360bbbbaea938f751f9eb1df96345dc384c4fe6bc18')
BAKONG_ACCOUNT = os.environ.get('BAKONG_ACCOUNT', 'rin_sophearun2@aclb')
BAKONG_MERCHANT_NAME = 'SMMMEGA'
BAKONG_MERCHANT_CITY = 'Phnom Penh'
BAKONG_QR_EXPIRY = 120  # seconds
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '7831160098:AAGQ5mvUf1_VVOqa0JIOWcq2YWrFLYZP8FU')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '-8192780683')

# WatermarkRemover-AI Config
WATERMARK_REMOVER_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'WatermarkRemover-AI')
WATERMARK_REMOVER_SCRIPT = os.path.join(WATERMARK_REMOVER_DIR, 'remwm.py')
HAS_WATERMARK_REMOVER = os.path.isfile(WATERMARK_REMOVER_SCRIPT)
if HAS_WATERMARK_REMOVER:
    logging.info(f'WatermarkRemover-AI found: {WATERMARK_REMOVER_DIR}')
else:
    logging.warning(f'WatermarkRemover-AI not found at: {WATERMARK_REMOVER_DIR}')

download_progress = {}
profile_tasks = {}
sora_tasks = {}  # {task_id: {status, urls, results, ...}}

# Facebook cookies support — place a 'cookies.txt' (Netscape format) in the app folder
COOKIES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cookies.txt')

def _get_cookies_file():
    """Return cookies.txt path if it exists, else None."""
    if os.path.isfile(COOKIES_FILE):
        return COOKIES_FILE
    return None

def _try_copy_browser_cookies(browser='chrome'):
    """Try to safely copy locked browser cookie DB for yt-dlp usage."""
    try:
        from yt_dlp.cookies import SUPPORTED_BROWSERS
        # We'll just pass the tuple — yt-dlp handles it internally
        return (browser,)
    except Exception:
        return None

def _get_facebook_cookies_for_cffi():
    """Load cookies from cookies.txt for curl_cffi requests."""
    cookies = {}
    cfile = _get_cookies_file()
    if not cfile:
        return cookies
    try:
        with open(cfile, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split('\t')
                if len(parts) >= 7 and '.facebook.com' in parts[0]:
                    cookies[parts[5]] = parts[6]
    except Exception:
        pass
    return cookies

# ==================== Facebook Graph API ====================
FB_GRAPH_API_VERSION = 'v21.0'
FB_GRAPH_BASE = f'https://graph.facebook.com/{FB_GRAPH_API_VERSION}'
FB_TOKEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fb_token.json')

def _load_fb_token():
    """Load Facebook Graph API access token from config file."""
    if os.path.isfile(FB_TOKEN_FILE):
        try:
            with open(FB_TOKEN_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('access_token', '')
        except Exception:
            pass
    return ''

def _save_fb_token(token):
    """Save access token to config file."""
    with open(FB_TOKEN_FILE, 'w', encoding='utf-8') as f:
        json.dump({'access_token': token}, f)

def fb_graph_request(endpoint, params=None, token=None):
    """Make a Facebook Graph API request."""
    if not token:
        token = _load_fb_token()
    if not token:
        return None
    url = f'{FB_GRAPH_BASE}/{endpoint.lstrip("/")}'
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }
    try:
        with httpx.Client(headers=headers, timeout=30, follow_redirects=True) as c:
            r = c.get(url, params=params or {})
            if r.status_code == 200:
                return r.json()
            elif r.status_code == 400:
                err = r.json()
                err_msg = err.get('error', {}).get('message', '')
                return {'error': True, 'message': err_msg, 'code': r.status_code}
            else:
                return {'error': True, 'message': f'HTTP {r.status_code}', 'code': r.status_code}
    except Exception as e:
        return {'error': True, 'message': str(e)}

def fb_graph_get_page_id(page_name, token=None):
    """Resolve page name/username to Page ID via Graph API."""
    result = fb_graph_request(page_name, {
        'fields': 'id,name,about,fan_count,followers_count,picture.type(large){url}',
    }, token)
    return result

def fb_graph_get_videos(page_id, token=None, limit=100, after=None):
    """Get videos from a Facebook Page via Graph API."""
    params = {
        'fields': 'id,title,description,created_time,length,permalink_url,'
                  'thumbnails{uri},source,likes.limit(0).summary(true),'
                  'comments.limit(0).summary(true),views',
        'limit': min(limit, 100),
    }
    if after:
        params['after'] = after
    return fb_graph_request(f'{page_id}/videos', params, token)

def fb_graph_get_reels(page_id, token=None, limit=100, after=None):
    """Get Reels from a Facebook Page via Graph API."""
    params = {
        'fields': 'id,description,created_time,length,permalink_url,'
                  'thumbnails{uri},likes.limit(0).summary(true),'
                  'comments.limit(0).summary(true)',
        'limit': min(limit, 100),
    }
    if after:
        params['after'] = after
    return fb_graph_request(f'{page_id}/video_reels', params, token)

def fb_graph_get_photos(page_id, token=None, limit=100, after=None):
    """Get photos from a Facebook Page via Graph API."""
    params = {
        'fields': 'id,name,created_time,link,picture,source,images,'
                  'album{id,name},width,height,'
                  'likes.limit(0).summary(true),'
                  'comments.limit(0).summary(true)',
        'limit': min(limit, 100),
    }
    if after:
        params['after'] = after
    return fb_graph_request(f'{page_id}/photos', params, token)

def fb_graph_get_albums(page_id, token=None, limit=100, after=None):
    """Get photo albums from a Facebook Page via Graph API."""
    params = {
        'fields': 'id,name,count,created_time,link,cover_photo{source},type',
        'limit': min(limit, 100),
    }
    if after:
        params['after'] = after
    return fb_graph_request(f'{page_id}/albums', params, token)

def fb_graph_get_album_photos(album_id, token=None, limit=100, after=None):
    """Get photos from a specific album via Graph API."""
    params = {
        'fields': 'id,name,created_time,link,picture,source,images,'
                  'width,height,likes.limit(0).summary(true),'
                  'comments.limit(0).summary(true)',
        'limit': min(limit, 100),
    }
    if after:
        params['after'] = after
    return fb_graph_request(f'{album_id}/photos', params, token)


# ==================== Platform Definitions ====================
PLATFORMS = {
    'tiktok':      {'name': 'TikTok',         'icon': 'fab fa-tiktok',             'color': '#fe2c55'},
    'douyin':      {'name': 'Douyin (抖音)',    'icon': 'fas fa-music',              'color': '#00f0ff'},
    'youtube':     {'name': 'YouTube',         'icon': 'fab fa-youtube',            'color': '#ff0000'},
    'instagram':   {'name': 'Instagram',       'icon': 'fab fa-instagram',          'color': '#e4405f'},
    'facebook':    {'name': 'Facebook',        'icon': 'fab fa-facebook',           'color': '#1877f2'},
    'twitter':     {'name': 'X (Twitter)',     'icon': 'fab fa-x-twitter',          'color': '#000000'},
    'pinterest':   {'name': 'Pinterest',       'icon': 'fab fa-pinterest',          'color': '#bd081c'},
    'kuaishou':    {'name': 'Kuaishou (快手)',   'icon': 'fas fa-kuaishou',              'color': '#ff4906'},
    'sora':        {'name': 'Sora',            'icon': 'fas fa-wand-magic-sparkles','color': '#a259ff'},
    'xiaohongshu': {'name': 'Xiaohongshu (小红书)','icon': 'fas fa-xiaohongshu',             'color': '#ff2442'},
    'threads':     {'name': 'Threads',         'icon': 'fab fa-threads',            'color': '#000000'},
    'linkedin':    {'name': 'LinkedIn',        'icon': 'fab fa-linkedin',           'color': '#0077b5'},
    'reddit':      {'name': 'Reddit',          'icon': 'fab fa-reddit',             'color': '#ff4500'},
    'bilibili':    {'name': 'Bilibili (哔哩哔哩)', 'icon': 'fab fa-bilibili',         'color': '#00a1d6'},
    'weibo':       {'name': 'Weibo (微博)',     'icon': 'fab fa-weibo',              'color': '#e6162d'},
    'lemon8':      {'name': 'Lemon8',          'icon': 'fas fa-lemon',              'color': '#a8e600'},
    'zhihu':       {'name': 'Zhihu (知乎)',     'icon': 'fas fa-z',                  'color': '#0084ff'},
    'wechat':      {'name': 'WeChat (微信)',    'icon': 'fab fa-weixin',             'color': '#07c160'},
    'pipixia':     {'name': 'Pipixia (皮皮虾)',  'icon': 'fas fa-shrimp',             'color': '#ff6699'},
}

# ==================== URL Utilities ====================
def detect_platform(url):
    url = url.lower()
    if 'tiktok.com' in url:      return 'tiktok'
    if 'douyin.com' in url:      return 'douyin'
    if 'youtube.com' in url or 'youtu.be' in url: return 'youtube'
    if 'instagram.com' in url:   return 'instagram'
    if 'facebook.com' in url or 'fb.watch' in url or 'fb.com' in url: return 'facebook'
    if 'twitter.com' in url or 'x.com' in url: return 'twitter'
    if 'pinterest.com' in url or 'pin.it' in url: return 'pinterest'
    if 'kuaishou.com' in url or 'kwai.com' in url or 'gifshow.com' in url: return 'kuaishou'
    if 'sora' in url and 'openai.com' in url: return 'sora'
    if 'sora.com' in url: return 'sora'
    if 'sora.chatgpt.com' in url or ('chatgpt.com' in url and '/p/s_' in url): return 'sora'
    if 'xiaohongshu.com' in url or 'xhslink.com' in url: return 'xiaohongshu'
    if 'threads.net' in url:     return 'threads'
    if 'linkedin.com' in url:    return 'linkedin'
    if 'reddit.com' in url or 'redd.it' in url: return 'reddit'
    if 'bilibili.com' in url or 'b23.tv' in url: return 'bilibili'
    if 'weibo.com' in url or 'weibo.cn' in url: return 'weibo'
    if 'lemon8-app.com' in url or 'lemon8.com' in url: return 'lemon8'
    if 'zhihu.com' in url:       return 'zhihu'
    if 'weixin.qq.com' in url or 'mp.weixin' in url: return 'wechat'
    if 'pipix.com' in url or 'pipixia' in url: return 'pipixia'
    return None

def is_valid_url(url):
    return bool(re.match(r'https?://', url)) and detect_platform(url) is not None
    # Also accept generic URLs for yt-dlp fallback
    # return bool(re.match(r'https?://', url))

def is_profile_url(url):
    """Check if URL is a profile/channel rather than single video."""
    pf = detect_platform(url)
    profile_patterns = {
        'tiktok':      [r'tiktok\.com/@[\w.-]+/?$', r'tiktok\.com/@[\w.-]+\?'],
        'douyin':      [r'douyin\.com/user/', r'v\.douyin\.com/'],
        'youtube':     [r'youtube\.com/@[\w.-]+', r'youtube\.com/c/', r'youtube\.com/channel/', r'youtube\.com/user/'],
        'instagram':   [r'instagram\.com/[\w.-]+/?$', r'instagram\.com/[\w.-]+/?\?'],
        'facebook':    [r'facebook\.com/[\w.-]+/?$', r'facebook\.com/profile\.php'],
        'twitter':     [r'(twitter|x)\.com/[\w]+/?$', r'(twitter|x)\.com/[\w]+\?'],
        'pinterest':   [r'pinterest\.com/[\w.-]+/?$', r'pinterest\.com/[\w.-]+/[\w.-]+'],
        'kuaishou':    [r'kuaishou\.com/profile/', r'kwai\.com/@'],
        'xiaohongshu': [r'xiaohongshu\.com/user/profile/'],
        'threads':     [r'threads\.net/@[\w.-]+/?$'],
        'linkedin':    [r'linkedin\.com/in/[\w.-]+'],
        'reddit':      [r'reddit\.com/user/[\w.-]+', r'reddit\.com/r/[\w.-]+'],
        'bilibili':    [r'bilibili\.com/space/', r'space\.bilibili\.com/'],
        'weibo':       [r'weibo\.com/u/', r'weibo\.com/[\w]+/?$'],
        'lemon8':      [r'lemon8.*/@[\w.-]+/?$'],
        'zhihu':       [r'zhihu\.com/people/'],
        'wechat':      [r'mp\.weixin\.qq\.com/mp/profile'],
        'pipixia':     [r'pipix\.com/user/'],
    }
    for pat in profile_patterns.get(pf, []):
        if re.search(pat, url, re.I):
            return True
    return False

def extract_username(url, platform=None):
    if not platform:
        platform = detect_platform(url)
    patterns = {
        'tiktok':      r'tiktok\.com/@([\w.-]+)',
        'youtube':     r'youtube\.com/(?:@|c/|channel/|user/)([\w.-]+)',
        'instagram':   r'instagram\.com/([\w.-]+)',
        'facebook':    r'facebook\.com/([\w.-]+)',
        'twitter':     r'(?:twitter|x)\.com/([\w]+)',
        'pinterest':   r'pinterest\.com/([\w.-]+)',
        'kuaishou':    r'(?:kuaishou\.com/profile/|kwai\.com/@)([\w.-]+)',
        'xiaohongshu': r'xiaohongshu\.com/user/profile/([\w]+)',
        'threads':     r'threads\.net/@([\w.-]+)',
        'linkedin':    r'linkedin\.com/in/([\w.-]+)',
        'reddit':      r'reddit\.com/(?:user|r)/([\w.-]+)',
        'bilibili':    r'(?:space\.bilibili|bilibili\.com/space)/([\d]+)',
        'weibo':       r'weibo\.com/(?:u/)?([\w]+)',
        'lemon8':      r'lemon8.*/@([\w.-]+)',
        'zhihu':       r'zhihu\.com/people/([\w.-]+)',
        'pipixia':     r'pipix\.com/user/([\d]+)',
    }
    pat = patterns.get(platform, '')
    if pat:
        m = re.search(pat, url, re.I)
        if m:
            return m.group(1)
    return None

# ==================== yt-dlp Configuration ====================
COMMON_YDL_OPTS = {
    'quiet': True,
    'no_warnings': True,
    'socket_timeout': 30,
    'retries': 3,
    'nocheckcertificate': True,
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    },
}
# Inject FFmpeg path so yt-dlp can merge streams, extract audio, etc.
if HAS_FFMPEG:
    COMMON_YDL_OPTS['ffmpeg_location'] = FFMPEG_PATHS['dir']

def get_ydl_opts(platform=None, extra=None):
    opts = {**COMMON_YDL_OPTS}
    if platform == 'tiktok':
        opts['extractor_args'] = {'TikTok': {'api_hostname': ['api22-normal-c-useast2a.tiktokv.com']}}
        opts['http_headers'] = {**opts['http_headers'], 'Referer': 'https://www.tiktok.com/'}
    elif platform == 'instagram':
        opts['http_headers'] = {**opts['http_headers'], 'Referer': 'https://www.instagram.com/'}
        cfile = _get_cookies_file()
        if cfile:
            opts['cookiefile'] = cfile
        else:
            for browser in ('chrome', 'edge', 'firefox', 'opera', 'brave'):
                try:
                    opts['cookiesfrombrowser'] = (browser,)
                    break
                except Exception:
                    continue
    elif platform == 'youtube':
        opts['extractor_args'] = {'youtube': {'skip': ['dash', 'hls']}}
    elif platform == 'facebook':
        opts['http_headers'] = {**opts['http_headers'], 'Referer': 'https://www.facebook.com/'}
        cfile = _get_cookies_file()
        if cfile:
            opts['cookiefile'] = cfile
        else:
            for browser in ('chrome', 'edge', 'firefox', 'opera', 'brave'):
                try:
                    opts['cookiesfrombrowser'] = (browser,)
                    break
                except Exception:
                    continue
    elif platform == 'twitter':
        opts['http_headers'] = {**opts['http_headers'], 'Referer': 'https://x.com/'}
        cfile = _get_cookies_file()
        if cfile:
            opts['cookiefile'] = cfile
        else:
            for browser in ('chrome', 'edge', 'firefox', 'opera', 'brave'):
                try:
                    opts['cookiesfrombrowser'] = (browser,)
                    break
                except Exception:
                    continue
    elif platform == 'threads':
        opts['http_headers'] = {**opts['http_headers'], 'Referer': 'https://www.threads.net/'}
        cfile = _get_cookies_file()
        if cfile:
            opts['cookiefile'] = cfile
    elif platform == 'linkedin':
        opts['http_headers'] = {**opts['http_headers'], 'Referer': 'https://www.linkedin.com/'}
        cfile = _get_cookies_file()
        if cfile:
            opts['cookiefile'] = cfile
    elif platform == 'reddit':
        opts['http_headers'] = {**opts['http_headers'], 'Referer': 'https://www.reddit.com/'}
    elif platform == 'bilibili':
        opts['http_headers'] = {**opts['http_headers'], 'Referer': 'https://www.bilibili.com/'}
    elif platform == 'weibo':
        opts['http_headers'] = {**opts['http_headers'], 'Referer': 'https://weibo.com/'}
        cfile = _get_cookies_file()
        if cfile:
            opts['cookiefile'] = cfile
    elif platform in ('xiaohongshu', 'lemon8', 'zhihu', 'wechat', 'pipixia', 'kuaishou', 'sora'):
        cfile = _get_cookies_file()
        if cfile:
            opts['cookiefile'] = cfile
    if extra:
        opts.update(extra)
    return opts

HTTP_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
}

# ==================== Progress Hook ====================
def progress_hook(d, task_id):
    if d['status'] == 'downloading':
        total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
        downloaded = d.get('downloaded_bytes', 0)
        if total > 0:
            download_progress[task_id] = {
                'status': 'downloading',
                'percent': round((downloaded / total) * 100, 1),
                'speed': d.get('speed', 0),
                'eta': d.get('eta', 0),
            }
    elif d['status'] == 'finished':
        download_progress[task_id] = {'status': 'processing', 'percent': 100, 'speed': 0, 'eta': 0}

# ==================== TikTok/Douyin API Helpers (TikHub API v1) ====================
def api_request(endpoint, params=None):
    """Generic GET request to the TikHub API (api.tikhub.io)."""
    try:
        headers = dict(HTTP_HEADERS)
        if TIKHUB_API_KEY:
            headers['Authorization'] = f'Bearer {TIKHUB_API_KEY}'
        with httpx.Client(headers=headers, timeout=30, follow_redirects=True) as c:
            r = c.get(f"{API_BASE_URL}{endpoint}", params=params or {})
            if r.status_code == 200:
                return r.json()
    except Exception:
        pass
    return None

# ---------- Hybrid (auto-detect TikTok / Douyin / Bilibili) ----------
def api_hybrid_video_data(url, minimal=False):
    """Parse a single video URL using the hybrid endpoint (supports TikTok & Douyin)."""
    return api_request("/api/v1/hybrid/video_data", {"url": url, "minimal": str(minimal).lower()})

# ---------- TikTok Web ----------
def api_get_sec_user_id(url):
    d = api_request("/api/v1/tiktok/web/get_sec_user_id", {"url": url})
    if d and d.get('code') == 200:
        return d.get('data', '')
    return None

def api_get_unique_id(url):
    d = api_request("/api/v1/tiktok/web/get_unique_id", {"url": url})
    if d and d.get('code') == 200:
        return d.get('data', '')
    return None

def api_get_user_profile_tiktok(unique_id='', sec_uid=''):
    p = {}
    if unique_id: p['uniqueId'] = unique_id
    if sec_uid:   p['secUid'] = sec_uid
    return api_request("/api/v1/tiktok/web/fetch_user_profile", p)

def api_get_user_posts_tiktok(sec_uid, cursor=0, count=35):
    return api_request("/api/v1/tiktok/web/fetch_user_post",
                       {'secUid': sec_uid, 'cursor': cursor, 'count': count, 'coverFormat': 2})

def api_tiktok_fetch_one_video(item_id):
    """Get single TikTok video data by item ID."""
    return api_request("/api/v1/tiktok/web/fetch_one_video", {'itemId': item_id})

def api_tiktok_fetch_comments(aweme_id, cursor=0, count=20):
    """Get comments for a TikTok video."""
    return api_request("/api/v1/tiktok/web/fetch_post_comment",
                       {'aweme_id': aweme_id, 'cursor': cursor, 'count': count})

def api_tiktok_fetch_user_like(sec_uid, cursor=0, count=35):
    """Get user liked videos."""
    return api_request("/api/v1/tiktok/web/fetch_user_like",
                       {'secUid': sec_uid, 'cursor': cursor, 'count': count, 'coverFormat': 2})

# ---------- Douyin Web ----------
def api_get_douyin_user_profile(sec_user_id):
    return api_request("/api/v1/douyin/web/handler_user_profile", {'sec_user_id': sec_user_id})

def api_get_douyin_user_posts(sec_user_id, max_cursor=0, count=20):
    return api_request("/api/v1/douyin/web/fetch_user_post_videos",
                       {'sec_user_id': sec_user_id, 'max_cursor': max_cursor, 'count': count})

def api_douyin_fetch_one_video(aweme_id):
    """Get single Douyin video data by aweme_id."""
    return api_request("/api/v1/douyin/web/fetch_one_video", {'aweme_id': aweme_id})

def api_douyin_fetch_comments(aweme_id, cursor=0, count=20):
    """Get comments for a Douyin video."""
    return api_request("/api/v1/douyin/web/fetch_video_comments",
                       {'aweme_id': aweme_id, 'cursor': cursor, 'count': count})

def api_douyin_get_sec_user_id(url):
    """Extract sec_user_id from a Douyin user URL."""
    d = api_request("/api/v1/douyin/web/get_sec_user_id", {"url": url})
    if d and d.get('code') == 200:
        return d.get('data', '')
    return None

def api_douyin_get_aweme_id(url):
    """Extract aweme_id from a Douyin video URL."""
    d = api_request("/api/v1/douyin/web/get_aweme_id", {"url": url})
    if d and d.get('code') == 200:
        return d.get('data', '')
    return None

# ---------- Xiaohongshu (小红书) API (TikHub) ----------
def api_xhs_get_user_info(user_id):
    """Get Xiaohongshu user info by user_id."""
    return api_request("/api/v1/xiaohongshu/web/get_user_info", {"user_id": user_id})

def api_xhs_get_user_posts(user_id, cursor=''):
    """Get Xiaohongshu user posts."""
    p = {'user_id': user_id}
    if cursor:
        p['cursor'] = cursor
    return api_request("/api/v1/xiaohongshu/web/get_user_posts", p)

def api_xhs_get_note_info(note_id):
    """Get single Xiaohongshu note/post info."""
    return api_request("/api/v1/xiaohongshu/web/get_note_info", {"note_id": note_id})

# ---------- Bilibili (哔哩哔哩) API (TikHub) ----------
def api_bili_get_user_info(uid):
    """Get Bilibili user info by uid."""
    return api_request("/api/v1/bilibili/web/get_user_info", {"uid": str(uid)})

def api_bili_get_user_videos(uid, page=1, page_size=30):
    """Get Bilibili user videos."""
    return api_request("/api/v1/bilibili/web/get_user_videos",
                       {'uid': str(uid), 'page': page, 'page_size': page_size})

def api_bili_get_video_info(bvid):
    """Get single Bilibili video info by bvid."""
    return api_request("/api/v1/bilibili/web/get_video_info", {"bvid": bvid})

# ---------- Weibo (微博) API (TikHub) ----------
def api_weibo_get_user_info(uid):
    """Get Weibo user info by uid."""
    return api_request("/api/v1/weibo/web/get_user_info", {"uid": str(uid)})

def api_weibo_get_user_posts(uid, page=1):
    """Get Weibo user posts."""
    return api_request("/api/v1/weibo/web/get_user_posts", {'uid': str(uid), 'page': page})

# ---------- Twitter / X API (TikHub) ----------
def api_twitter_get_user_info(screen_name):
    """Get Twitter/X user info by screen_name."""
    return api_request("/api/v1/twitter/web/get_user_info", {"screen_name": screen_name})

def api_twitter_get_user_tweets(user_id, cursor='', count=20):
    """Get Twitter/X user tweets."""
    p = {'user_id': str(user_id), 'count': count}
    if cursor:
        p['cursor'] = cursor
    return api_request("/api/v1/twitter/web/get_user_tweets", p)

# ---------- YouTube API (TikHub) ----------
def api_youtube_get_channel_info(channel_id):
    """Get YouTube channel info."""
    return api_request("/api/v1/youtube/web/get_channel_info", {"channel_id": channel_id})

def api_youtube_get_channel_videos(channel_id, cursor=''):
    """Get YouTube channel videos."""
    p = {'channel_id': channel_id}
    if cursor:
        p['cursor'] = cursor
    return api_request("/api/v1/youtube/web/get_channel_videos", p)

# ---------- Reddit API (TikHub) ----------
def api_reddit_get_user_posts(username, after='', count=25):
    """Get Reddit user posts."""
    p = {'username': username, 'count': count}
    if after:
        p['after'] = after
    return api_request("/api/v1/reddit/web/get_user_posts", p)

# ---------- Threads API (TikHub) ----------
def api_threads_get_user_info(username):
    """Get Threads user info."""
    return api_request("/api/v1/threads/web/get_user_info", {"username": username})

def api_threads_get_user_posts(user_id, max_id=''):
    """Get Threads user posts."""
    p = {'user_id': str(user_id)}
    if max_id:
        p['max_id'] = max_id
    return api_request("/api/v1/threads/web/get_user_posts", p)

# ---------- Kuaishou (快手) API (TikHub) ----------
def api_kuaishou_get_user_info(user_id):
    """Get Kuaishou user info."""
    return api_request("/api/v1/kuaishou/web/get_user_info", {"user_id": user_id})

def api_kuaishou_get_user_posts(user_id, cursor=''):
    """Get Kuaishou user posts."""
    p = {'user_id': user_id}
    if cursor:
        p['cursor'] = cursor
    return api_request("/api/v1/kuaishou/web/get_user_posts", p)

# ---------- Instagram Web & App API (TikHub) ----------
def api_ig_get_user_info_by_username(username):
    """Get Instagram user info by username (Web API)."""
    return api_request("/api/v1/instagram/web/get_user_info", {"username": username})

def api_ig_app_get_user_info(username):
    """Get Instagram user info by username (App API — more reliable)."""
    return api_request("/api/v1/instagram/app/get_user_info", {"username": username})

def api_ig_get_user_info_by_id(user_id):
    """Get Instagram user info by user_id (Web API)."""
    return api_request("/api/v1/instagram/web/get_user_info_by_id", {"user_id": str(user_id)})

def api_ig_web_get_user_posts(user_id, end_cursor='', count=12):
    """Get user posts via Instagram Web API."""
    p = {'user_id': str(user_id), 'count': count}
    if end_cursor:
        p['end_cursor'] = end_cursor
    return api_request("/api/v1/instagram/web/get_user_posts", p)

def api_ig_app_get_user_posts(user_id, max_id='', count=12):
    """Get user posts via Instagram App API (faster, more data)."""
    p = {'user_id': str(user_id), 'count': count}
    if max_id:
        p['max_id'] = max_id
    return api_request("/api/v1/instagram/app/get_user_posts", p)

def api_ig_get_user_reels(user_id, max_id='', count=12):
    """Get user reels."""
    p = {'user_id': str(user_id), 'count': count}
    if max_id:
        p['max_id'] = max_id
    return api_request("/api/v1/instagram/app/get_user_reels", p)

def api_ig_get_post_info(shortcode):
    """Get single Instagram post info by shortcode."""
    return api_request("/api/v1/instagram/web/get_post_info", {"shortcode": shortcode})

def api_ig_app_get_post_info(media_id):
    """Get single Instagram post info by media_id (App API)."""
    return api_request("/api/v1/instagram/app/get_post_info", {"media_id": str(media_id)})

def api_ig_get_post_comments(shortcode, end_cursor='', count=20):
    """Get comments for an Instagram post."""
    p = {'shortcode': shortcode, 'count': count}
    if end_cursor:
        p['end_cursor'] = end_cursor
    return api_request("/api/v1/instagram/web/get_post_comments", p)

def api_ig_get_user_stories(user_id):
    """Get user stories."""
    return api_request("/api/v1/instagram/app/get_user_stories", {"user_id": str(user_id)})

def api_ig_get_user_highlights(user_id):
    """Get user highlights."""
    return api_request("/api/v1/instagram/app/get_user_highlights", {"user_id": str(user_id)})


def extract_instagram_api_item(item):
    """Convert Instagram API item (Web or App) to unified format."""
    try:
        media_type = item.get('media_type', item.get('product_type', ''))
        shortcode = item.get('shortcode', item.get('code', ''))
        pk = str(item.get('pk', item.get('id', '')))
        caption = item.get('caption', {})
        if isinstance(caption, dict):
            title = (caption.get('text', '') or '')[:200]
        elif isinstance(caption, str):
            title = caption[:200]
        else:
            title = 'Post'
        thumb = ''
        img_versions = item.get('image_versions2', {})
        if isinstance(img_versions, dict):
            candidates = img_versions.get('candidates', [])
            if candidates and isinstance(candidates, list):
                thumb = candidates[0].get('url', '')
        if not thumb:
            thumb = item.get('display_url', item.get('thumbnail_src', ''))
            if not thumb:
                tn_res = item.get('thumbnail_resources', [])
                if tn_res and isinstance(tn_res, list):
                    thumb = tn_res[-1].get('src', '')
        dur = item.get('video_duration', 0) or 0
        like_count = item.get('like_count', 0)
        if not like_count:
            edge_liked = item.get('edge_media_preview_like', {})
            if isinstance(edge_liked, dict):
                like_count = edge_liked.get('count', 0)
        comment_count = item.get('comment_count', 0)
        if not comment_count:
            edge_comment = item.get('edge_media_to_comment', item.get('edge_media_preview_comment', {}))
            if isinstance(edge_comment, dict):
                comment_count = edge_comment.get('count', 0)
        view_count = item.get('view_count', item.get('video_view_count', 0)) or 0
        play_count = item.get('play_count', 0) or 0
        view_count = view_count or play_count
        is_video = item.get('is_video', False) or media_type in (2, 'video', 'clips', 'igtv')
        post_type = 'video' if is_video else 'photo'
        if item.get('product_type') == 'clips':
            post_type = 'reel'
        owner = item.get('owner', item.get('user', {}))
        if isinstance(owner, dict):
            author_name = owner.get('full_name', owner.get('username', ''))
        else:
            author_name = ''
        ts = item.get('taken_at', item.get('taken_at_timestamp', 0)) or 0
        url = f"https://www.instagram.com/p/{shortcode}/" if shortcode else ''
        if not url and pk:
            url = f"https://www.instagram.com/p/{pk}/"
        return {
            'id': pk or shortcode, 'title': title or 'Post', 'url': url,
            'thumbnail': thumb, 'duration': dur,
            'view_count': view_count, 'like_count': like_count,
            'comment_count': comment_count, 'share_count': 0,
            'create_time': ts, 'author': author_name,
            'platform': 'instagram', 'type': post_type,
        }
    except Exception:
        return None


def extract_xhs_api_item(item):
    """Convert Xiaohongshu API item to unified format."""
    try:
        nid = item.get('note_id', item.get('id', ''))
        title = (item.get('display_title', '') or item.get('title', '') or item.get('desc', ''))[:200]
        thumb = ''
        cover = item.get('cover', item.get('image_list', [{}]))
        if isinstance(cover, dict):
            thumb = cover.get('url', cover.get('url_default', ''))
        elif isinstance(cover, list) and cover:
            thumb = cover[0].get('url', cover[0].get('url_default', '')) if isinstance(cover[0], dict) else ''
        interact = item.get('interact_info', {})
        is_video = item.get('type') == 'video' or item.get('media_type') == 'video'
        return {
            'id': nid, 'title': title or 'Post',
            'url': f'https://www.xiaohongshu.com/explore/{nid}' if nid else '',
            'thumbnail': thumb, 'duration': 0,
            'view_count': interact.get('view_count', 0) or 0,
            'like_count': interact.get('liked_count', item.get('liked_count', 0)) or 0,
            'comment_count': interact.get('comment_count', 0) or 0,
            'share_count': interact.get('share_count', 0) or 0,
            'create_time': item.get('time', item.get('create_time', 0)) or 0,
            'author': item.get('user', {}).get('nickname', '') if isinstance(item.get('user'), dict) else '',
            'platform': 'xiaohongshu', 'type': 'video' if is_video else 'photo',
        }
    except Exception:
        return None


def extract_bili_api_item(item):
    """Convert Bilibili API item to unified format."""
    try:
        bvid = item.get('bvid', '')
        aid = item.get('aid', item.get('id', ''))
        return {
            'id': bvid or str(aid),
            'title': (item.get('title', '') or 'Video')[:200],
            'url': f'https://www.bilibili.com/video/{bvid}' if bvid else '',
            'thumbnail': item.get('pic', item.get('cover', '')),
            'duration': item.get('duration', item.get('length', 0)) or 0,
            'view_count': item.get('play', item.get('stat', {}).get('view', 0)) or 0,
            'like_count': item.get('stat', {}).get('like', 0) or 0,
            'comment_count': item.get('stat', {}).get('reply', item.get('comment', 0)) or 0,
            'share_count': item.get('stat', {}).get('share', 0) or 0,
            'create_time': item.get('created', item.get('pubdate', 0)) or 0,
            'author': item.get('author', item.get('owner', {}).get('name', '')) if isinstance(item.get('owner', {}), dict) else item.get('author', ''),
            'platform': 'bilibili', 'type': 'video',
        }
    except Exception:
        return None


def extract_weibo_api_item(item):
    """Convert Weibo API item to unified format."""
    try:
        mid = str(item.get('mid', item.get('id', item.get('idstr', ''))))
        text = (item.get('text_raw', '') or item.get('text', ''))[:200]
        import html as html_mod
        text = html_mod.unescape(re.sub(r'<[^>]+>', '', text))
        thumb = ''
        page_info = item.get('page_info', {})
        if isinstance(page_info, dict):
            thumb = page_info.get('page_pic', {}).get('url', '') if isinstance(page_info.get('page_pic'), dict) else ''
        pics = item.get('pics', [])
        if not thumb and pics and isinstance(pics, list):
            thumb = pics[0].get('large', {}).get('url', pics[0].get('url', '')) if isinstance(pics[0], dict) else ''
        has_video = bool(page_info.get('type') == 'video') if isinstance(page_info, dict) else False
        return {
            'id': mid, 'title': text or 'Post',
            'url': f'https://weibo.com/{item.get("user", {}).get("id", "")}/{mid}' if mid else '',
            'thumbnail': thumb, 'duration': 0,
            'view_count': item.get('reads_count', item.get('show_count', 0)) or 0,
            'like_count': item.get('attitudes_count', 0) or 0,
            'comment_count': item.get('comments_count', 0) or 0,
            'share_count': item.get('reposts_count', 0) or 0,
            'create_time': 0,
            'author': item.get('user', {}).get('screen_name', '') if isinstance(item.get('user'), dict) else '',
            'platform': 'weibo', 'type': 'video' if has_video else 'photo',
        }
    except Exception:
        return None


def extract_twitter_api_item(item):
    """Convert Twitter/X API item to unified format."""
    try:
        tid = str(item.get('id', item.get('id_str', '')))
        text = (item.get('full_text', '') or item.get('text', ''))[:200]
        thumb = ''
        media = item.get('extended_entities', {}).get('media', item.get('entities', {}).get('media', []))
        has_video = False
        if isinstance(media, list) and media:
            thumb = media[0].get('media_url_https', media[0].get('media_url', ''))
            if media[0].get('type') == 'video':
                has_video = True
        user = item.get('user', {})
        screen_name = user.get('screen_name', '') if isinstance(user, dict) else ''
        return {
            'id': tid, 'title': text or 'Tweet',
            'url': f'https://x.com/{screen_name}/status/{tid}' if screen_name and tid else '',
            'thumbnail': thumb, 'duration': 0,
            'view_count': item.get('view_count', 0) or 0,
            'like_count': item.get('favorite_count', 0) or 0,
            'comment_count': item.get('reply_count', 0) or 0,
            'share_count': item.get('retweet_count', 0) or 0,
            'create_time': 0,
            'author': user.get('name', screen_name) if isinstance(user, dict) else '',
            'platform': 'twitter', 'type': 'video' if has_video else 'photo',
        }
    except Exception:
        return None


# ==================== Video Info Extraction ====================
def extract_tiktok_api_item(item):
    try:
        video = item.get('video', {})
        stats = item.get('stats', {})
        author = item.get('author', {})
        thumb = video.get('cover', '') or video.get('dynamicCover', '') or video.get('originCover', '')
        aid = item.get('id', '')
        uid = author.get('uniqueId', '')
        return {
            'id': aid, 'title': item.get('desc', 'Video')[:200],
            'url': f"https://www.tiktok.com/@{uid}/video/{aid}" if uid and aid else '',
            'thumbnail': thumb, 'duration': video.get('duration', 0),
            'view_count': stats.get('playCount', 0), 'like_count': stats.get('diggCount', 0),
            'comment_count': stats.get('commentCount', 0), 'share_count': stats.get('shareCount', 0),
            'create_time': item.get('createTime', 0), 'author': author.get('nickname', uid),
            'platform': 'tiktok', 'type': 'video',
        }
    except Exception:
        return None

def extract_douyin_api_item(item):
    try:
        video = item.get('video', {})
        stats = item.get('statistics', {})
        author = item.get('author', {})
        thumb = ''
        cover = video.get('cover', video.get('origin_cover', {}))
        if isinstance(cover, dict):
            urls = cover.get('url_list', [])
            if urls: thumb = urls[0]
        aid = item.get('aweme_id', '')
        dur = video.get('duration', 0)
        return {
            'id': aid, 'title': item.get('desc', 'Video')[:200],
            'url': f"https://www.douyin.com/video/{aid}" if aid else '',
            'thumbnail': thumb, 'duration': dur // 1000 if dur > 1000 else dur,
            'view_count': stats.get('play_count', 0), 'like_count': stats.get('digg_count', 0),
            'comment_count': stats.get('comment_count', 0), 'share_count': stats.get('share_count', 0),
            'create_time': item.get('create_time', 0), 'author': author.get('nickname', ''),
            'platform': 'douyin', 'type': 'video',
        }
    except Exception:
        return None

def extract_ytdlp_entry(entry, platform=''):
    """Convert yt-dlp entry to unified format."""
    if not entry:
        return None
    thumb = ''
    thumbs = entry.get('thumbnails', [])
    if thumbs:
        thumb = thumbs[-1].get('url', '') if isinstance(thumbs[-1], dict) else ''
    elif entry.get('thumbnail'):
        thumb = entry['thumbnail']

    post_type = 'video'
    if entry.get('ext') in ('jpg', 'png', 'webp') or not entry.get('duration'):
        post_type = 'photo' if not entry.get('duration') else 'video'

    return {
        'id': str(entry.get('id', '')),
        'title': (entry.get('title', '') or entry.get('description', '') or 'Post')[:200],
        'url': entry.get('webpage_url', entry.get('url', '')),
        'thumbnail': thumb,
        'duration': entry.get('duration') or 0,
        'view_count': entry.get('view_count') or 0,
        'like_count': entry.get('like_count') or 0,
        'comment_count': entry.get('comment_count') or 0,
        'share_count': entry.get('repost_count', 0) or 0,
        'create_time': entry.get('timestamp') or 0,
        'author': entry.get('uploader', entry.get('channel', '')) or '',
        'platform': platform or detect_platform(entry.get('webpage_url', '')) or '',
        'type': post_type,
    }

# ==================== Profile Grabbers ====================
def grab_tiktok_profile(url, task_id, max_videos=0):
    task = profile_tasks[task_id]
    try:
        task.update({'status': 'getting_profile', 'message': 'កំពុងទាញយក TikTok Profile...'})
        username = extract_username(url, 'tiktok')
        sec_uid, profile_info = None, None

        if username:
            resp = api_get_user_profile_tiktok(unique_id=username)
            if resp and resp.get('code') == 200:
                pd = resp.get('data', {})
                ui = pd.get('userInfo', pd)
                u, s = ui.get('user', {}), ui.get('stats', {})
                sec_uid = u.get('secUid', '')
                profile_info = {
                    'nickname': u.get('nickname', username), 'username': u.get('uniqueId', username),
                    'avatar': u.get('avatarLarger', u.get('avatarMedium', '')),
                    'signature': u.get('signature', ''), 'followers': s.get('followerCount', 0),
                    'following': s.get('followingCount', 0),
                    'likes': s.get('heartCount', s.get('heart', 0)),
                    'video_count': s.get('videoCount', 0),
                }

        if not sec_uid:
            sec_uid = api_get_sec_user_id(url)

        if not sec_uid:
            return _grab_ytdlp_fallback(url, task_id, max_videos, 'tiktok', username, profile_info)

        if not profile_info:
            profile_info = _default_profile(username or 'Unknown', sec_uid)
        task['profile'] = profile_info
        task.update({'status': 'grabbing', 'message': 'កំពុងទាញយកវីដេអូ...'})

        videos, cursor, has_more, page = [], 0, True, 0
        while has_more:
            page += 1
            task['message'] = f'ទំព័រ {page}... ({len(videos)} វីដេអូ)'
            resp = api_get_user_posts_tiktok(sec_uid, cursor=cursor, count=35)
            if not resp or resp.get('code') != 200: break
            data = resp.get('data', {})
            items = data.get('itemList', data.get('aweme_list', []))
            if not items: break
            for item in items:
                v = extract_tiktok_api_item(item)
                if v:
                    videos.append(v)
                    task['total'] = len(videos)
                    if 0 < max_videos <= len(videos):
                        has_more = False; break
            has_more = has_more and data.get('hasMore', data.get('has_more', False))
            cursor = data.get('cursor', 0)
            if not cursor or not has_more: break
            time.sleep(1.5)

        task.update({'status': 'completed', 'videos': videos, 'total': len(videos),
                     'message': f'រកឃើញ {len(videos)} វីដេអូ'})
    except Exception as e:
        profile_tasks[task_id].update({'status': 'error', 'message': f'កំហុស: {e}'})


def grab_douyin_profile(url, task_id, max_videos=0):
    task = profile_tasks[task_id]
    try:
        task.update({'status': 'getting_profile', 'message': 'កំពុងទាញយក Douyin Profile...'})
        sid = None
        m = re.search(r'douyin\.com/user/([\w-]+)', url)
        if m: sid = m.group(1)
        if not sid:
            try:
                with httpx.Client(headers=HTTP_HEADERS, timeout=15, follow_redirects=True) as c:
                    r = c.get(url)
                    m2 = re.search(r'douyin\.com/user/([\w-]+)', str(r.url))
                    if m2: sid = m2.group(1)
            except Exception: pass
        if not sid:
            task.update({'status': 'error', 'message': 'រកមិនឃើញ Douyin user ID'}); return

        profile_info = _default_profile('Douyin User', sid)
        profile_info['platform'] = 'douyin'
        pr = api_get_douyin_user_profile(sid)
        if pr and pr.get('code') == 200:
            pd = pr.get('data', {}).get('user', {})
            profile_info.update({
                'nickname': pd.get('nickname', profile_info['nickname']),
                'username': pd.get('unique_id', pd.get('short_id', sid[:20])),
                'signature': pd.get('signature', ''), 'followers': pd.get('follower_count', 0),
                'following': pd.get('following_count', 0), 'likes': pd.get('total_favorited', 0),
                'video_count': pd.get('aweme_count', 0),
            })
            av = pd.get('avatar_larger', {})
            if isinstance(av, dict) and av.get('url_list'):
                profile_info['avatar'] = av['url_list'][0]

        task['profile'] = profile_info
        task.update({'status': 'grabbing', 'message': 'កំពុងទាញយកវីដេអូ...'})

        videos, max_cursor, has_more, page = [], 0, True, 0
        while has_more:
            page += 1
            task['message'] = f'ទំព័រ {page}... ({len(videos)} វីដេអូ)'
            resp = api_get_douyin_user_posts(sid, max_cursor=max_cursor, count=20)
            if not resp or resp.get('code') != 200: break
            data = resp.get('data', {})
            items = data.get('aweme_list', [])
            if not items: break
            for item in items:
                v = extract_douyin_api_item(item)
                if v:
                    videos.append(v)
                    task['total'] = len(videos)
                    if 0 < max_videos <= len(videos):
                        has_more = False; break
            has_more = has_more and data.get('has_more', False)
            max_cursor = data.get('max_cursor', data.get('cursor', 0))
            if not has_more: break
            time.sleep(1.5)

        task.update({'status': 'completed', 'videos': videos, 'total': len(videos),
                     'message': f'រកឃើញ {len(videos)} វីដេអូ'})
    except Exception as e:
        profile_tasks[task_id].update({'status': 'error', 'message': f'កំហុស: {e}'})


def _extract_fb_graph_photo(item, page_name=''):
    """Convert a Graph API photo item to unified format."""
    photo_id = item.get('id', '')
    # Get best quality image URL
    source_url = item.get('source', '')
    images = item.get('images', [])
    if images and isinstance(images, list):
        # Images are sorted largest first
        source_url = images[0].get('source', source_url)
    thumb = item.get('picture', source_url)
    link = item.get('link', '')
    if not link and photo_id:
        link = f'https://www.facebook.com/photo/?fbid={photo_id}'
    likes = 0
    likes_data = item.get('likes', {})
    if isinstance(likes_data, dict):
        summary = likes_data.get('summary', {})
        likes = summary.get('total_count', 0) if isinstance(summary, dict) else 0
    comments = 0
    comments_data = item.get('comments', {})
    if isinstance(comments_data, dict):
        summary = comments_data.get('summary', {})
        comments = summary.get('total_count', 0) if isinstance(summary, dict) else 0
    created = item.get('created_time', '')
    create_ts = 0
    if created:
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
            create_ts = int(dt.timestamp())
        except Exception:
            pass
    album_name = ''
    album_data = item.get('album', {})
    if isinstance(album_data, dict):
        album_name = album_data.get('name', '')
    title = item.get('name', '') or ''
    if not title:
        title = f'Photo ({album_name})' if album_name else 'Facebook Photo'
    return {
        'id': photo_id,
        'title': title[:120],
        'url': link,
        'thumbnail': thumb,
        'source': source_url,
        'duration': 0,
        'view_count': 0,
        'like_count': likes,
        'comment_count': comments,
        'share_count': 0,
        'create_time': create_ts,
        'author': page_name,
        'platform': 'facebook',
        'type': 'photo',
        'width': item.get('width', 0),
        'height': item.get('height', 0),
    }


def _extract_fb_graph_video(item, page_name='', vtype='video'):
    """Convert a Graph API video/reel item to unified format."""
    vid_id = item.get('id', '')
    permalink = item.get('permalink_url', '')
    if not permalink and vid_id:
        permalink = f'https://www.facebook.com/{page_name}/videos/{vid_id}'
    thumb = ''
    thumbs = item.get('thumbnails', {})
    if isinstance(thumbs, dict) and thumbs.get('data'):
        thumb = thumbs['data'][0].get('uri', '')
    elif isinstance(thumbs, list) and thumbs:
        thumb = thumbs[0].get('uri', '')
    likes = 0
    likes_data = item.get('likes', {})
    if isinstance(likes_data, dict):
        summary = likes_data.get('summary', {})
        likes = summary.get('total_count', 0) if isinstance(summary, dict) else 0
    comments = 0
    comments_data = item.get('comments', {})
    if isinstance(comments_data, dict):
        summary = comments_data.get('summary', {})
        comments = summary.get('total_count', 0) if isinstance(summary, dict) else 0
    views = item.get('views', 0) or 0
    created = item.get('created_time', '')
    create_ts = 0
    if created:
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
            create_ts = int(dt.timestamp())
        except Exception:
            pass
    return {
        'id': vid_id,
        'title': item.get('title', item.get('description', f'Facebook {vtype.title()}')[:80]) or f'Facebook {vtype.title()}',
        'url': permalink if permalink.startswith('http') else f'https://www.facebook.com{permalink}',
        'thumbnail': thumb,
        'duration': int(item.get('length', 0) or 0),
        'view_count': views,
        'like_count': likes,
        'comment_count': comments,
        'share_count': 0,
        'create_time': create_ts,
        'author': page_name,
        'platform': 'facebook',
        'type': vtype,
        'source': item.get('source', ''),
    }


def _grab_facebook_via_graph(username, url, token, task_id, max_videos=0):
    """Fetch all videos + photos from a Facebook Page via Graph API (no limit)."""
    task = profile_tasks[task_id]
    task['message'] = 'កំពុងភ្ជាប់ Graph API...'

    # Resolve page name to page ID
    page_name = username or url.rstrip('/').split('/')[-1]
    page_data = fb_graph_get_page_id(page_name, token)
    if not page_data or page_data.get('error'):
        err_msg = ''
        if page_data and page_data.get('message'):
            err_msg = page_data['message']
        return None, None, f'Graph API error: {err_msg}'

    page_id = page_data.get('id', '')
    if not page_id:
        return None, None, 'Cannot resolve Facebook Page ID'

    # Build profile info
    pic_url = ''
    pic_data = page_data.get('picture', {})
    if isinstance(pic_data, dict) and pic_data.get('data'):
        pic_url = pic_data['data'].get('url', '')
    profile_info = {
        'nickname': page_data.get('name', page_name),
        'username': page_name,
        'avatar': pic_url,
        'signature': (page_data.get('about', '') or '')[:200],
        'followers': page_data.get('followers_count', page_data.get('fan_count', 0)) or 0,
        'following': 0,
        'likes': page_data.get('fan_count', 0) or 0,
        'video_count': 0,
    }
    task['profile'] = profile_info

    # Fetch ALL content with pagination (videos + reels + photos)
    items = []
    seen_ids = set()
    video_count = 0
    photo_count = 0
    task.update({'status': 'grabbing', 'message': 'កំពុងទាញយកទិន្នន័យតាម Graph API...'})

    def _update_msg():
        task['total'] = len(items)
        task['message'] = f'Graph API: {video_count} វីដេអូ + {photo_count} រូបភាព...'

    # --- Videos (no limit) ---
    after = None
    while True:
        result = fb_graph_get_videos(page_id, token, limit=100, after=after)
        if not result or result.get('error'):
            break
        data = result.get('data', [])
        if not data:
            break
        for item in data:
            if item.get('id') in seen_ids:
                continue
            v = _extract_fb_graph_video(item, page_name, 'video')
            if v:
                seen_ids.add(v['id'])
                items.append(v)
                video_count += 1
                _update_msg()
                if 0 < max_videos <= len(items):
                    break
        if 0 < max_videos <= len(items):
            break
        paging = result.get('paging', {})
        after = paging.get('cursors', {}).get('after')
        if not after or not paging.get('next'):
            break

    # --- Reels ---
    if max_videos <= 0 or len(items) < max_videos:
        after = None
        while True:
            result = fb_graph_get_reels(page_id, token, limit=100, after=after)
            if not result or result.get('error'):
                break
            data = result.get('data', [])
            if not data:
                break
            for item in data:
                if item.get('id') in seen_ids:
                    continue
                v = _extract_fb_graph_video(item, page_name, 'reel')
                if v:
                    seen_ids.add(v['id'])
                    items.append(v)
                    video_count += 1
                    _update_msg()
                    if 0 < max_videos <= len(items):
                        break
            if 0 < max_videos <= len(items):
                break
            paging = result.get('paging', {})
            after = paging.get('cursors', {}).get('after')
            if not after or not paging.get('next'):
                break

    # --- Photos (all albums) ---
    if max_videos <= 0 or len(items) < max_videos:
        task['message'] = f'Graph API: {video_count} វីដេអូ — កំពុងទាញយករូបភាព...'
        # First get all albums
        album_ids = []
        after = None
        while True:
            result = fb_graph_get_albums(page_id, token, limit=100, after=after)
            if not result or result.get('error'):
                break
            data = result.get('data', [])
            if not data:
                break
            for alb in data:
                alb_id = alb.get('id')
                if alb_id:
                    album_ids.append(alb_id)
            paging = result.get('paging', {})
            after = paging.get('cursors', {}).get('after')
            if not after or not paging.get('next'):
                break

        # Get photos from each album
        for alb_id in album_ids:
            after = None
            while True:
                result = fb_graph_get_album_photos(alb_id, token, limit=100, after=after)
                if not result or result.get('error'):
                    break
                data = result.get('data', [])
                if not data:
                    break
                for item in data:
                    if item.get('id') in seen_ids:
                        continue
                    p = _extract_fb_graph_photo(item, page_name)
                    if p:
                        seen_ids.add(p['id'])
                        items.append(p)
                        photo_count += 1
                        _update_msg()
                        if 0 < max_videos <= len(items):
                            break
                if 0 < max_videos <= len(items):
                    break
                paging = result.get('paging', {})
                after = paging.get('cursors', {}).get('after')
                if not after or not paging.get('next'):
                    break
            if 0 < max_videos <= len(items):
                break

        # Also get page-level photos (not in albums)
        if max_videos <= 0 or len(items) < max_videos:
            after = None
            while True:
                result = fb_graph_get_photos(page_id, token, limit=100, after=after)
                if not result or result.get('error'):
                    break
                data = result.get('data', [])
                if not data:
                    break
                for item in data:
                    if item.get('id') in seen_ids:
                        continue
                    p = _extract_fb_graph_photo(item, page_name)
                    if p:
                        seen_ids.add(p['id'])
                        items.append(p)
                        photo_count += 1
                        _update_msg()
                        if 0 < max_videos <= len(items):
                            break
                if 0 < max_videos <= len(items):
                    break
                paging = result.get('paging', {})
                after = paging.get('cursors', {}).get('after')
                if not after or not paging.get('next'):
                    break

    profile_info['video_count'] = len(items)
    return items, profile_info, None


def grab_facebook_profile(url, task_id, max_videos=0):
    """Dedicated Facebook profile/page video grabber with Graph API support."""
    task = profile_tasks[task_id]
    username = extract_username(url, 'facebook') or ''
    try:
        task.update({'status': 'getting_profile', 'message': 'កំពុងទាញយក Facebook Profile...'})

        # ========== Method 1: Facebook Graph API ==========
        fb_token = _load_fb_token()
        if fb_token:
            task['message'] = 'កំពុងប្រើ Facebook Graph API...'
            videos, profile_info, err = _grab_facebook_via_graph(username, url, fb_token, task_id, max_videos)
            if videos and not err:
                v_count = sum(1 for v in videos if v.get('type') != 'photo')
                p_count = sum(1 for v in videos if v.get('type') == 'photo')
                msg = f'រកឃើញ {v_count} វីដេអូ + {p_count} រូបភាព (Graph API)' if p_count else f'រកឃើញ {v_count} វីដេអូ (Graph API)'
                task.update({
                    'status': 'completed', 'videos': videos, 'total': len(videos),
                    'profile': profile_info,
                    'message': msg
                })
                return
            elif err:
                task['message'] = f'Graph API: {err} — កំពុងព្យាយាមវិធីផ្សេង...'

        # Ensure URL points to /videos/ section
        grab_url = url.rstrip('/')
        if '/videos' not in grab_url and '/watch' not in grab_url and '/reel' not in grab_url:
            grab_url += '/videos/'

        # ========== Method 2: curl_cffi with cookies ==========
        video_urls = []
        profile_info = None
        if HAS_CURL_CFFI:
            task['message'] = 'កំពុងស្កេន Facebook page...'
            fb_cookies = _get_facebook_cookies_for_cffi()
            try:
                r = cffi_requests.get(
                    grab_url,
                    impersonate='chrome131',
                    timeout=25,
                    cookies=fb_cookies if fb_cookies else None,
                )
                if r.status_code == 200:
                    html = r.text
                    # Extract video IDs from HTML/JSON data
                    vid_ids = set()
                    # Pattern 1: /videos/NNNN
                    vid_ids.update(re.findall(r'/videos/(\d{10,})', html))
                    # Pattern 2: /watch/?v=NNNN
                    vid_ids.update(re.findall(r'/watch/?\?v=(\d{10,})', html))
                    # Pattern 3: /reel/NNNN
                    reel_ids = re.findall(r'/reel/(\d{10,})', html)
                    vid_ids.update(reel_ids)
                    # Pattern 4: JSON "videoID":"NNNN"
                    vid_ids.update(re.findall(r'"videoID"\s*:\s*"(\d{10,})"', html))
                    vid_ids.update(re.findall(r'"video_id"\s*:\s*"(\d{10,})"', html))
                    # Pattern 5: Video nodes in React data
                    vid_ids.update(re.findall(r'"__typename"\s*:\s*"Video"[^}]*?"id"\s*:\s*"(\d{10,})"', html))
                    vid_ids.update(re.findall(r'"id"\s*:\s*"(\d{10,})"[^}]*?"__typename"\s*:\s*"Video"', html))

                    for vid in vid_ids:
                        vid_url = f'https://www.facebook.com/watch/?v={vid}'
                        if vid_url not in video_urls:
                            video_urls.append(vid_url)

                    # Try to extract profile info from HTML
                    title_m = re.search(r'<title[^>]*>(.*?)</title>', html)
                    page_title = title_m.group(1).strip() if title_m else username
                    page_title = page_title.replace(' | Facebook', '').replace(' - Facebook', '').strip()
                    if page_title and page_title != 'Facebook':
                        profile_info = _default_profile(page_title, username)
                        # Try to get followers
                        followers_m = re.search(r'"follower_count"\s*:\s*(\d+)', html)
                        if followers_m:
                            profile_info['followers'] = int(followers_m.group(1))
            except Exception:
                pass

        # ========== Method 2: yt-dlp with cookies ==========
        if not video_urls:
            task['message'] = 'កំពុងប្រើ yt-dlp ជាមួយ cookies...'
            # Try yt-dlp with cookies (cookies.txt or browser)
            for attempt_opts in _facebook_ydl_attempts(grab_url, max_videos):
                try:
                    with YoutubeDL(attempt_opts) as ydl:
                        info = ydl.extract_info(grab_url, download=False)
                    if info:
                        entries = []
                        raw = info.get('entries', [])
                        if raw:
                            for e in raw:
                                if e:
                                    if e.get('_type') == 'playlist' or e.get('entries'):
                                        for se in (e.get('entries', []) or []):
                                            if se: entries.append(se)
                                    else:
                                        entries.append(e)
                        if entries:
                            if not profile_info:
                                profile_info = {
                                    'nickname': info.get('title', info.get('uploader', username)) or username,
                                    'username': info.get('uploader_id', username) or username,
                                    'avatar': '', 'signature': (info.get('description', '') or '')[:200],
                                    'followers': info.get('channel_follower_count', 0) or 0,
                                    'following': 0, 'likes': 0,
                                    'video_count': len(entries),
                                }
                            videos = []
                            for e in entries:
                                v = extract_ytdlp_entry(e, 'facebook')
                                if v:
                                    videos.append(v)
                                    if 0 < max_videos <= len(videos):
                                        break
                            task.update({
                                'status': 'completed', 'videos': videos, 'total': len(videos),
                                'profile': profile_info, 'message': f'រកឃើញ {len(videos)} វីដេអូ'
                            })
                            return
                        break
                except Exception:
                    continue

        # ========== Build results from scraped URLs ==========
        if video_urls:
            if not profile_info:
                profile_info = _default_profile(username or 'Facebook Page', username)
            task['profile'] = profile_info
            task.update({'status': 'grabbing', 'message': f'កំពុងដំណើរការ {len(video_urls)} វីដេអូ...'})

            videos = []
            limit = max_videos if max_videos > 0 else len(video_urls)
            for i, vurl in enumerate(video_urls[:limit]):
                vid_id = re.search(r'v=(\d+)', vurl)
                vid_id = vid_id.group(1) if vid_id else str(i)
                v = {
                    'id': vid_id,
                    'title': f'Facebook Video {i+1}',
                    'url': vurl,
                    'thumbnail': '',
                    'duration': 0,
                    'view_count': 0, 'like_count': 0, 'comment_count': 0, 'share_count': 0,
                    'create_time': 0, 'author': username,
                    'platform': 'facebook', 'type': 'video',
                }
                # Try to get more info via yt-dlp for each video
                try:
                    opts = get_ydl_opts('facebook', {'socket_timeout': 10})
                    with YoutubeDL(opts) as ydl:
                        vinfo = ydl.extract_info(vurl, download=False)
                    if vinfo:
                        v['title'] = vinfo.get('title', v['title'])
                        v['thumbnail'] = vinfo.get('thumbnail', '')
                        v['duration'] = vinfo.get('duration', 0)
                        v['view_count'] = vinfo.get('view_count', 0)
                except Exception:
                    pass
                videos.append(v)
                task['total'] = len(videos)
                task['message'] = f'វីដេអូ {len(videos)}/{min(limit, len(video_urls))}...'

            task.update({
                'status': 'completed', 'videos': videos, 'total': len(videos),
                'profile': profile_info,
                'message': f'រកឃើញ {len(videos)} វីដេអូ'
            })
            return

        # ========== All methods failed ==========
        error_msg = (
            'រកមិនឃើញ Facebook Profile វីដេអូ។\n\n'
            '� វិធីទី 1 — Facebook Graph API (ល្អបំផុត):\n'
            '1. ទៅ developers.facebook.com → Create App\n'
            '2. ចម្លង Page Access Token\n'
            '3. បិទភ្ជាប់ Token នៅក្នុងកម្មវិធីនេះ\n\n'
            '🍪 វិធីទី 2 — Cookies:\n'
            '1. ដំឡើង extension "Get cookies.txt LOCALLY"\n'
            '2. Log in ទៅ Facebook\n'
            '3. Export cookies ជា cookies.txt\n'
            '4. Upload file cookies.txt'
        )
        task.update({'status': 'error', 'message': error_msg})

    except Exception as e:
        profile_tasks[task_id].update({'status': 'error', 'message': f'កំហុស: {e}'})


def _facebook_ydl_attempts(url, max_videos):
    """Generate yt-dlp option sets to try for Facebook (cookies file, then browsers)."""
    base = {
        'quiet': True, 'no_warnings': True, 'socket_timeout': 20,
        'nocheckcertificate': True, 'ignoreerrors': True,
        'extract_flat': 'in_playlist',
        'playlistend': max_videos if max_videos > 0 else None,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Referer': 'https://www.facebook.com/',
        },
    }
    # Try 1: cookies.txt file
    cfile = _get_cookies_file()
    if cfile:
        yield {**base, 'cookiefile': cfile}
    # Try 2-5: browser cookies
    for browser in ('chrome', 'edge', 'firefox', 'brave'):
        yield {**base, 'cookiesfrombrowser': (browser,)}


def grab_instagram_profile(url, task_id, max_videos=0):
    """Instagram profile grabber via TikHub Instagram Web & App API with yt-dlp fallback."""
    task = profile_tasks[task_id]
    try:
        task.update({'status': 'getting_profile', 'message': 'កំពុងទាញយក Instagram Profile...'})
        username = extract_username(url, 'instagram') or ''

        if not username:
            # Try to extract from URL variations
            m = re.search(r'instagram\.com/([\w.-]+)', url)
            if m:
                username = m.group(1)
            if not username:
                task.update({'status': 'error', 'message': 'រកមិនឃើញ Instagram username ពី URL'})
                return

        # Remove trailing slashes and filter out non-profile paths
        username = username.strip('/').split('/')[0]
        if username.lower() in ('p', 'reel', 'reels', 'stories', 'explore', 'accounts', 'direct'):
            task.update({'status': 'error', 'message': f'\'{username}\' មិនមែនជា username'})
            return

        user_id = None
        profile_info = None
        api_method = None

        # ============ Strategy 1: TikHub Instagram App API (most reliable) ============
        task['message'] = 'កំពុងប្រើ Instagram App API...'
        try:
            resp = api_ig_app_get_user_info(username)
            if resp and resp.get('code') == 200:
                ud = resp.get('data', {})
                u = ud.get('user', ud)
                user_id = str(u.get('pk', u.get('pk_id', u.get('id', ''))))
                profile_info = {
                    'nickname': u.get('full_name', username) or username,
                    'username': u.get('username', username),
                    'avatar': u.get('hd_profile_pic_url_info', {}).get('url', '')
                              or u.get('profile_pic_url', ''),
                    'signature': (u.get('biography', '') or '')[:200],
                    'followers': u.get('follower_count', 0),
                    'following': u.get('following_count', 0),
                    'likes': 0,
                    'video_count': u.get('media_count', 0),
                }
                api_method = 'app'
                logging.info(f'Instagram App API: user_id={user_id} for @{username}')
        except Exception as ex:
            logging.warning(f'Instagram App API error: {ex}')

        # ============ Strategy 2: TikHub Instagram Web API (fallback) ============
        if not user_id:
            task['message'] = 'កំពុងប្រើ Instagram Web API...'
            try:
                resp = api_ig_get_user_info_by_username(username)
                if resp and resp.get('code') == 200:
                    ud = resp.get('data', {})
                    u = ud.get('user', ud)
                    user_id = str(u.get('id', u.get('pk', '')))
                    profile_info = {
                        'nickname': u.get('full_name', username) or username,
                        'username': u.get('username', username),
                        'avatar': u.get('profile_pic_url_hd', u.get('profile_pic_url', '')),
                        'signature': (u.get('biography', '') or '')[:200],
                        'followers': u.get('edge_followed_by', {}).get('count', 0)
                                     if isinstance(u.get('edge_followed_by'), dict)
                                     else u.get('follower_count', 0),
                        'following': u.get('edge_follow', {}).get('count', 0)
                                     if isinstance(u.get('edge_follow'), dict)
                                     else u.get('following_count', 0),
                        'likes': 0,
                        'video_count': u.get('edge_owner_to_timeline_media', {}).get('count', 0)
                                       if isinstance(u.get('edge_owner_to_timeline_media'), dict)
                                       else u.get('media_count', 0),
                    }
                    api_method = 'web'
                    logging.info(f'Instagram Web API: user_id={user_id} for @{username}')
            except Exception as ex:
                logging.warning(f'Instagram Web API error: {ex}')

        # ============ Strategy 3: yt-dlp fallback ============
        if not user_id:
            task['message'] = 'កំពុងសាកល្បង yt-dlp...'
            logging.info(f'Instagram API failed, falling back to yt-dlp for @{username}')
            return _grab_instagram_ytdlp_fallback(url, username, task_id, max_videos)

        # ============ Grab posts via API ============
        task['profile'] = profile_info
        task.update({'status': 'grabbing', 'message': 'កំពុងទាញយក Posts...'})

        videos = []
        page = 0

        # --- Grab Posts via App API (primary) ---
        if api_method == 'app':
            max_id = ''
            has_more = True
            while has_more:
                page += 1
                task['message'] = f'ទំព័រ {page}... ({len(videos)} posts)'
                try:
                    resp = api_ig_app_get_user_posts(user_id, max_id=max_id, count=33)
                    if not resp or resp.get('code') != 200:
                        break
                    data = resp.get('data', {})
                    items = data.get('items', data.get('feed_items', []))
                    if not items:
                        break
                    for item in items:
                        # App API may nest media inside 'media' key
                        media = item.get('media', item) if isinstance(item, dict) else item
                        v = extract_instagram_api_item(media)
                        if v:
                            videos.append(v)
                            task['total'] = len(videos)
                            if 0 < max_videos <= len(videos):
                                has_more = False
                                break
                    has_more = has_more and data.get('more_available', False)
                    max_id = data.get('next_max_id', '')
                    if not max_id:
                        break
                    time.sleep(1.5)
                except Exception as ex:
                    logging.warning(f'Instagram App posts page {page} error: {ex}')
                    break
        else:
            # --- Grab Posts via Web API ---
            end_cursor = ''
            has_next = True
            while has_next:
                page += 1
                task['message'] = f'ទំព័រ {page}... ({len(videos)} posts)'
                try:
                    resp = api_ig_web_get_user_posts(user_id, end_cursor=end_cursor, count=12)
                    if not resp or resp.get('code') != 200:
                        break
                    data = resp.get('data', {})
                    # Web API uses edge_owner_to_timeline_media structure
                    media_data = data.get('edge_owner_to_timeline_media',
                                 data.get('user', {}).get('edge_owner_to_timeline_media', data))
                    edges = []
                    if isinstance(media_data, dict):
                        edges = media_data.get('edges', [])
                        page_info = media_data.get('page_info', {})
                        has_next = page_info.get('has_next_page', False)
                        end_cursor = page_info.get('end_cursor', '')
                    elif isinstance(media_data, list):
                        edges = media_data
                        has_next = False
                    else:
                        break

                    if not edges:
                        # Try flat items list (App-style response from Web endpoint)
                        items = data.get('items', [])
                        for item in items:
                            v = extract_instagram_api_item(item)
                            if v:
                                videos.append(v)
                                task['total'] = len(videos)
                                if 0 < max_videos <= len(videos):
                                    has_next = False
                                    break
                    else:
                        for edge in edges:
                            node = edge.get('node', edge)
                            v = extract_instagram_api_item(node)
                            if v:
                                videos.append(v)
                                task['total'] = len(videos)
                                if 0 < max_videos <= len(videos):
                                    has_next = False
                                    break
                    if not end_cursor:
                        break
                    time.sleep(1.5)
                except Exception as ex:
                    logging.warning(f'Instagram Web posts page {page} error: {ex}')
                    break

        # --- Also grab Reels if we have few results ---
        if len(videos) < 5 or (max_videos == 0 or len(videos) < max_videos):
            task['message'] = f'កំពុងទាញយក Reels... ({len(videos)} posts)'
            try:
                reel_max_id = ''
                reel_more = True
                reel_page = 0
                while reel_more:
                    reel_page += 1
                    resp = api_ig_get_user_reels(user_id, max_id=reel_max_id, count=12)
                    if not resp or resp.get('code') != 200:
                        break
                    data = resp.get('data', {})
                    items = data.get('items', [])
                    if not items:
                        break
                    existing_ids = {v['id'] for v in videos}
                    for item in items:
                        media = item.get('media', item) if isinstance(item, dict) else item
                        v = extract_instagram_api_item(media)
                        if v and v['id'] not in existing_ids:
                            v['type'] = 'reel'
                            videos.append(v)
                            task['total'] = len(videos)
                            if 0 < max_videos <= len(videos):
                                reel_more = False
                                break
                    reel_more = reel_more and data.get('paging_info', {}).get('more_available', False)
                    reel_max_id = data.get('paging_info', {}).get('max_id', data.get('next_max_id', ''))
                    if not reel_max_id:
                        break
                    time.sleep(1.5)
            except Exception as ex:
                logging.warning(f'Instagram Reels error: {ex}')

        if not videos:
            # If API returned profile but no posts, try yt-dlp
            logging.info(f'Instagram API returned 0 posts for @{username}, trying yt-dlp...')
            return _grab_instagram_ytdlp_fallback(url, username, task_id, max_videos, profile_info)

        task.update({'status': 'completed', 'videos': videos, 'total': len(videos),
                     'profile': profile_info,
                     'message': f'រកឃើញ {len(videos)} posts (via Instagram {api_method.upper()} API)'})
    except Exception as e:
        logging.error(f'grab_instagram_profile error: {e}')
        profile_tasks[task_id].update({'status': 'error', 'message': f'កំហុស: {e}'})


def _grab_instagram_ytdlp_fallback(url, username, task_id, max_videos, profile_info=None):
    """Fallback: grab Instagram profile using yt-dlp with cookies."""
    task = profile_tasks[task_id]
    grab_url = f'https://www.instagram.com/{username}/' if username else url
    info = None
    attempt_names = []

    # Try cookies.txt
    cfile = _get_cookies_file()
    if cfile:
        attempt_names.append('cookies.txt')
        task['message'] = 'yt-dlp: cookies.txt...'
        try:
            opts = get_ydl_opts('instagram', {
                'extract_flat': 'in_playlist',
                'playlistend': max_videos if max_videos > 0 else None,
                'ignoreerrors': True, 'cookiefile': cfile,
            })
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(grab_url, download=False)
            if not (info and info.get('entries')):
                info = None
        except Exception:
            info = None

    # Try browser cookies
    if not info:
        for browser in ('chrome', 'edge', 'firefox', 'brave'):
            attempt_names.append(f'browser:{browser}')
            task['message'] = f'yt-dlp: {browser} cookies...'
            try:
                opts = get_ydl_opts('instagram', {
                    'extract_flat': 'in_playlist',
                    'playlistend': max_videos if max_videos > 0 else None,
                    'ignoreerrors': True, 'cookiesfrombrowser': (browser,),
                })
                opts.pop('cookiefile', None)
                with YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(grab_url, download=False)
                if info and info.get('entries'):
                    break
                else:
                    info = None
            except Exception:
                info = None

    # Try no auth (public)
    if not info:
        attempt_names.append('no-auth')
        task['message'] = 'yt-dlp: no auth...'
        try:
            opts = get_ydl_opts('instagram', {
                'extract_flat': 'in_playlist',
                'playlistend': max_videos if max_videos > 0 else None,
                'ignoreerrors': True,
            })
            opts.pop('cookiefile', None)
            opts.pop('cookiesfrombrowser', None)
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(grab_url, download=False)
        except Exception:
            info = None

    if not info:
        error_msg = (
            'រកមិនឃើញ Instagram Profile វីដេអូ។\n\n'
            '💡 សាកល្បង:\n'
            '1. ប្រើ TikHub API Key (TIKHUB_API_KEY env var)\n'
            '2. ឬ Upload cookies.txt (via browser extension)\n\n'
            f'⚙️ Attempts: {", ".join(attempt_names)}'
        )
        task.update({'status': 'error', 'message': error_msg})
        return

    # Process yt-dlp results
    entries = []
    raw_entries = info.get('entries', [])
    if raw_entries:
        for e in raw_entries:
            if not e: continue
            if e.get('_type') == 'playlist' or e.get('entries'):
                for se in (e.get('entries') or []):
                    if se: entries.append(se)
            else:
                entries.append(e)

    if not profile_info:
        profile_info = {
            'nickname': info.get('title', info.get('uploader', username)) or username,
            'username': info.get('uploader_id', username) or username,
            'avatar': '', 'signature': (info.get('description', '') or '')[:200],
            'followers': info.get('channel_follower_count', 0) or 0,
            'following': 0, 'likes': 0,
            'video_count': info.get('playlist_count', 0) or len(entries),
        }
        thumbs = info.get('thumbnails', [])
        if thumbs and isinstance(thumbs[-1], dict):
            profile_info['avatar'] = thumbs[-1].get('url', '')

    task['profile'] = profile_info
    task.update({'status': 'grabbing', 'message': f'កំពុងដំណើរការ {len(entries)} posts...'})

    videos = []
    for e in entries:
        v = extract_ytdlp_entry(e, 'instagram')
        if v:
            videos.append(v)
            task['total'] = len(videos)
            if 0 < max_videos <= len(videos):
                break

    task.update({'status': 'completed', 'videos': videos, 'total': len(videos),
                 'profile': profile_info, 'message': f'រកឃើញ {len(videos)} posts (yt-dlp)'})


# ==================== New Platform Grabbers (TikHub API + yt-dlp fallback) ====================

def grab_xiaohongshu_profile(url, task_id, max_videos=0):
    """Xiaohongshu (小红书) Profile Grabber via TikHub API."""
    task = profile_tasks[task_id]
    try:
        task.update({'status': 'getting_profile', 'message': 'កំពុងទាញយក Xiaohongshu Profile...'})
        user_id = extract_username(url, 'xiaohongshu')
        if not user_id:
            m = re.search(r'xiaohongshu\.com/user/profile/(\w+)', url)
            if m: user_id = m.group(1)
        if not user_id:
            return grab_universal_profile(url, task_id, max_videos, 'xiaohongshu')

        profile_info = _default_profile(user_id, user_id)
        resp = api_xhs_get_user_info(user_id)
        if resp and resp.get('code') == 200:
            ud = resp.get('data', {})
            profile_info.update({
                'nickname': ud.get('nickname', user_id),
                'username': ud.get('red_id', user_id),
                'avatar': ud.get('imageb', ud.get('images', '')),
                'signature': (ud.get('desc', '') or '')[:200],
                'followers': ud.get('fans', ud.get('fansCount', 0)) or 0,
                'following': ud.get('follows', ud.get('followingCount', 0)) or 0,
                'likes': ud.get('liked', ud.get('interaction', 0)) or 0,
                'video_count': ud.get('noteCount', ud.get('notes', 0)) or 0,
            })
        task['profile'] = profile_info
        task.update({'status': 'grabbing', 'message': 'កំពុងទាញយក posts...'})

        videos, cursor, page = [], '', 0
        while True:
            page += 1
            task['message'] = f'ទំព័រ {page}... ({len(videos)} posts)'
            resp = api_xhs_get_user_posts(user_id, cursor=cursor)
            if not resp or resp.get('code') != 200: break
            data = resp.get('data', {})
            items = data.get('notes', data.get('items', []))
            if not items: break
            for item in items:
                v = extract_xhs_api_item(item)
                if v:
                    videos.append(v)
                    task['total'] = len(videos)
                    if 0 < max_videos <= len(videos): break
            if 0 < max_videos <= len(videos): break
            cursor = data.get('cursor', data.get('next_cursor', ''))
            if not cursor or not data.get('has_more', False): break
            time.sleep(1.5)

        if not videos:
            return grab_universal_profile(url, task_id, max_videos, 'xiaohongshu')
        task.update({'status': 'completed', 'videos': videos, 'total': len(videos),
                     'message': f'រកឃើញ {len(videos)} posts'})
    except Exception as e:
        profile_tasks[task_id].update({'status': 'error', 'message': f'កំហុស: {e}'})


def grab_bilibili_profile(url, task_id, max_videos=0):
    """哔哩哔哩 (Bilibili) Profile Grabber via TikHub API."""
    task = profile_tasks[task_id]
    try:
        task.update({'status': 'getting_profile', 'message': 'កំពុងទាញយក Bilibili Profile...'})
        uid = extract_username(url, 'bilibili')
        if not uid:
            m = re.search(r'space\.bilibili\.com/(\d+)', url)
            if m: uid = m.group(1)
        if not uid:
            return grab_universal_profile(url, task_id, max_videos, 'bilibili')

        profile_info = _default_profile(uid, uid)
        resp = api_bili_get_user_info(uid)
        if resp and resp.get('code') == 200:
            ud = resp.get('data', {})
            profile_info.update({
                'nickname': ud.get('name', uid),
                'username': str(ud.get('mid', uid)),
                'avatar': ud.get('face', ''),
                'signature': (ud.get('sign', '') or '')[:200],
                'followers': ud.get('fans', ud.get('follower', 0)) or 0,
                'following': ud.get('following', ud.get('friend', 0)) or 0,
                'likes': ud.get('likes', 0) or 0,
                'video_count': ud.get('archive_count', ud.get('video', 0)) or 0,
            })
        task['profile'] = profile_info
        task.update({'status': 'grabbing', 'message': 'កំពុងទាញយកវីដេអូ...'})

        videos, pg = [], 1
        while True:
            task['message'] = f'ទំព័រ {pg}... ({len(videos)} វីដេអូ)'
            resp = api_bili_get_user_videos(uid, page=pg, page_size=30)
            if not resp or resp.get('code') != 200: break
            data = resp.get('data', {})
            vlist = data.get('vlist', data.get('list', data.get('items', [])))
            if not vlist: break
            for item in vlist:
                v = extract_bili_api_item(item)
                if v:
                    videos.append(v)
                    task['total'] = len(videos)
                    if 0 < max_videos <= len(videos): break
            if 0 < max_videos <= len(videos): break
            total_pages = data.get('pages', data.get('page', {}).get('pn', 1))
            if pg >= total_pages: break
            pg += 1
            time.sleep(1.5)

        if not videos:
            return grab_universal_profile(url, task_id, max_videos, 'bilibili')
        task.update({'status': 'completed', 'videos': videos, 'total': len(videos),
                     'message': f'រកឃើញ {len(videos)} វីដេអូ'})
    except Exception as e:
        profile_tasks[task_id].update({'status': 'error', 'message': f'កំហុស: {e}'})


def grab_weibo_profile(url, task_id, max_videos=0):
    """微博 (Weibo) Profile Grabber via TikHub API."""
    task = profile_tasks[task_id]
    try:
        task.update({'status': 'getting_profile', 'message': 'កំពុងទាញយក Weibo Profile...'})
        uid = extract_username(url, 'weibo')
        if not uid:
            m = re.search(r'weibo\.com/(?:u/)?(\d+)', url)
            if m: uid = m.group(1)
        if not uid:
            return grab_universal_profile(url, task_id, max_videos, 'weibo')

        profile_info = _default_profile(uid, uid)
        resp = api_weibo_get_user_info(uid)
        if resp and resp.get('code') == 200:
            ud = resp.get('data', {})
            profile_info.update({
                'nickname': ud.get('screen_name', uid),
                'username': ud.get('domain', str(ud.get('id', uid))),
                'avatar': ud.get('avatar_hd', ud.get('profile_image_url', '')),
                'signature': (ud.get('description', '') or '')[:200],
                'followers': ud.get('followers_count', 0) or 0,
                'following': ud.get('friends_count', 0) or 0,
                'likes': 0,
                'video_count': ud.get('statuses_count', 0) or 0,
            })
        task['profile'] = profile_info
        task.update({'status': 'grabbing', 'message': 'កំពុងទាញយក posts...'})

        videos, pg = [], 1
        while True:
            task['message'] = f'ទំព័រ {pg}... ({len(videos)} posts)'
            resp = api_weibo_get_user_posts(uid, page=pg)
            if not resp or resp.get('code') != 200: break
            data = resp.get('data', {})
            items = data.get('statuses', data.get('list', data.get('cards', [])))
            if not items: break
            for item in items:
                v = extract_weibo_api_item(item)
                if v:
                    videos.append(v)
                    task['total'] = len(videos)
                    if 0 < max_videos <= len(videos): break
            if 0 < max_videos <= len(videos): break
            pg += 1
            if pg > 50: break
            time.sleep(1.5)

        if not videos:
            return grab_universal_profile(url, task_id, max_videos, 'weibo')
        task.update({'status': 'completed', 'videos': videos, 'total': len(videos),
                     'message': f'រកឃើញ {len(videos)} posts'})
    except Exception as e:
        profile_tasks[task_id].update({'status': 'error', 'message': f'កំហុស: {e}'})


def grab_twitter_profile(url, task_id, max_videos=0):
    """Twitter/X Profile Grabber via TikHub API + yt-dlp fallback."""
    task = profile_tasks[task_id]
    try:
        task.update({'status': 'getting_profile', 'message': 'កំពុងទាញយក X/Twitter Profile...'})
        screen_name = extract_username(url, 'twitter')
        if not screen_name:
            m = re.search(r'(?:twitter|x)\.com/(\w+)', url, re.I)
            if m: screen_name = m.group(1)
        if not screen_name:
            return grab_universal_profile(url, task_id, max_videos, 'twitter')

        profile_info = _default_profile(screen_name, screen_name)
        user_id = None
        resp = api_twitter_get_user_info(screen_name)
        if resp and resp.get('code') == 200:
            ud = resp.get('data', {})
            user_id = str(ud.get('id', ud.get('id_str', '')))
            profile_info.update({
                'nickname': ud.get('name', screen_name),
                'username': ud.get('screen_name', screen_name),
                'avatar': (ud.get('profile_image_url_https', '') or '').replace('_normal', ''),
                'signature': (ud.get('description', '') or '')[:200],
                'followers': ud.get('followers_count', 0) or 0,
                'following': ud.get('friends_count', 0) or 0,
                'likes': ud.get('favourites_count', 0) or 0,
                'video_count': ud.get('statuses_count', 0) or 0,
            })
        task['profile'] = profile_info

        if user_id:
            task.update({'status': 'grabbing', 'message': 'កំពុងទាញយក tweets...'})
            videos, cursor, page = [], '', 0
            while True:
                page += 1
                task['message'] = f'ទំព័រ {page}... ({len(videos)} tweets)'
                resp = api_twitter_get_user_tweets(user_id, cursor=cursor)
                if not resp or resp.get('code') != 200: break
                data = resp.get('data', {})
                items = data.get('tweets', data.get('list', []))
                if not items: break
                for item in items:
                    v = extract_twitter_api_item(item)
                    if v:
                        videos.append(v)
                        task['total'] = len(videos)
                        if 0 < max_videos <= len(videos): break
                if 0 < max_videos <= len(videos): break
                cursor = data.get('cursor', data.get('next_cursor', ''))
                if not cursor: break
                time.sleep(1.5)

            if videos:
                task.update({'status': 'completed', 'videos': videos, 'total': len(videos),
                             'message': f'រកឃើញ {len(videos)} tweets'})
                return

        return _grab_ytdlp_fallback(url, task_id, max_videos, 'twitter', screen_name, profile_info)
    except Exception as e:
        profile_tasks[task_id].update({'status': 'error', 'message': f'កំហុស: {e}'})


def grab_youtube_profile(url, task_id, max_videos=0):
    """YouTube Profile Grabber via yt-dlp (excellent native support)."""
    return grab_universal_profile(url, task_id, max_videos, 'youtube')


def grab_threads_profile(url, task_id, max_videos=0):
    """Threads Profile Grabber via TikHub API."""
    task = profile_tasks[task_id]
    try:
        task.update({'status': 'getting_profile', 'message': 'កំពុងទាញយក Threads Profile...'})
        username = extract_username(url, 'threads')
        if not username:
            m = re.search(r'threads\.net/@?(\w+)', url, re.I)
            if m: username = m.group(1)
        if not username:
            return grab_universal_profile(url, task_id, max_videos, 'threads')

        profile_info = _default_profile(username, username)
        user_id = None
        resp = api_threads_get_user_info(username)
        if resp and resp.get('code') == 200:
            ud = resp.get('data', {})
            user_id = str(ud.get('pk', ud.get('id', '')))
            profile_info.update({
                'nickname': ud.get('full_name', username),
                'username': ud.get('username', username),
                'avatar': ud.get('profile_pic_url', ''),
                'signature': (ud.get('biography', '') or '')[:200],
                'followers': ud.get('follower_count', 0) or 0,
                'following': ud.get('following_count', 0) or 0,
                'likes': 0,
                'video_count': ud.get('media_count', 0) or 0,
            })
        task['profile'] = profile_info

        if user_id:
            task.update({'status': 'grabbing', 'message': 'កំពុងទាញយក posts...'})
            videos, max_id, page = [], '', 0
            while True:
                page += 1
                task['message'] = f'ទំព័រ {page}... ({len(videos)} posts)'
                resp = api_threads_get_user_posts(user_id, max_id=max_id)
                if not resp or resp.get('code') != 200: break
                data = resp.get('data', {})
                items = data.get('threads', data.get('items', data.get('posts', [])))
                if not items: break
                for item in items:
                    post = item.get('thread_items', [item])[0] if isinstance(item.get('thread_items'), list) else item
                    post_data = post.get('post', post)
                    caption = post_data.get('caption', {})
                    text = ''
                    if isinstance(caption, dict):
                        text = caption.get('text', '')[:200]
                    elif isinstance(caption, str):
                        text = caption[:200]
                    pk = str(post_data.get('pk', post_data.get('id', '')))
                    code = post_data.get('code', '')
                    thumb = ''
                    img = post_data.get('image_versions2', {})
                    if isinstance(img, dict):
                        cands = img.get('candidates', [])
                        if cands: thumb = cands[0].get('url', '')
                    v = {
                        'id': pk, 'title': text or 'Post',
                        'url': f'https://www.threads.net/@{username}/post/{code}' if code else '',
                        'thumbnail': thumb, 'duration': 0,
                        'view_count': 0,
                        'like_count': post_data.get('like_count', 0) or 0,
                        'comment_count': post_data.get('text_post_app_info', {}).get('reply_count', 0) or 0,
                        'share_count': post_data.get('reshare_count', 0) or 0,
                        'create_time': post_data.get('taken_at', 0) or 0,
                        'author': username, 'platform': 'threads',
                        'type': 'video' if post_data.get('video_versions') else 'photo',
                    }
                    videos.append(v)
                    task['total'] = len(videos)
                    if 0 < max_videos <= len(videos): break
                if 0 < max_videos <= len(videos): break
                max_id = data.get('next_max_id', data.get('cursor', ''))
                if not max_id: break
                time.sleep(1.5)

            if videos:
                task.update({'status': 'completed', 'videos': videos, 'total': len(videos),
                             'message': f'រកឃើញ {len(videos)} posts'})
                return

        return grab_universal_profile(url, task_id, max_videos, 'threads')
    except Exception as e:
        profile_tasks[task_id].update({'status': 'error', 'message': f'កំហុស: {e}'})


def grab_kuaishou_profile(url, task_id, max_videos=0):
    """快手 (Kuaishou) Profile Grabber via TikHub API."""
    task = profile_tasks[task_id]
    try:
        task.update({'status': 'getting_profile', 'message': 'កំពុងទាញយក Kuaishou Profile...'})
        user_id = extract_username(url, 'kuaishou')
        if not user_id:
            m = re.search(r'kuaishou\.com/profile/(\w+)', url, re.I)
            if m: user_id = m.group(1)
        if not user_id:
            return grab_universal_profile(url, task_id, max_videos, 'kuaishou')

        profile_info = _default_profile(user_id, user_id)
        resp = api_kuaishou_get_user_info(user_id)
        if resp and resp.get('code') == 200:
            ud = resp.get('data', {})
            profile_info.update({
                'nickname': ud.get('name', ud.get('user_name', user_id)),
                'username': ud.get('userId', ud.get('eid', user_id)),
                'avatar': ud.get('headurl', ud.get('hd_headurl', '')),
                'signature': (ud.get('description', '') or '')[:200],
                'followers': ud.get('fan', ud.get('fansCount', 0)) or 0,
                'following': ud.get('follow', ud.get('followCount', 0)) or 0,
                'likes': ud.get('liked', 0) or 0,
                'video_count': ud.get('photo_count', ud.get('photoCount', 0)) or 0,
            })
        task['profile'] = profile_info
        task.update({'status': 'grabbing', 'message': 'កំពុងទាញយកវីដេអូ...'})

        videos, cursor, page = [], '', 0
        while True:
            page += 1
            task['message'] = f'ទំព័រ {page}... ({len(videos)} វីដេអូ)'
            resp = api_kuaishou_get_user_posts(user_id, cursor=cursor)
            if not resp or resp.get('code') != 200: break
            data = resp.get('data', {})
            items = data.get('feeds', data.get('photos', data.get('list', [])))
            if not items: break
            for item in items:
                vid = item.get('photo_id', item.get('id', ''))
                v = {
                    'id': str(vid),
                    'title': (item.get('caption', '') or item.get('ext_params', {}).get('desc', '') or 'Video')[:200],
                    'url': f'https://www.kuaishou.com/short-video/{vid}' if vid else '',
                    'thumbnail': item.get('cover_thumbnail_urls', [{}])[0].get('url', item.get('headUrl', '')) if item.get('cover_thumbnail_urls') else item.get('coverUrl', ''),
                    'duration': (item.get('duration', 0) or 0) // 1000,
                    'view_count': item.get('view_count', item.get('viewCount', 0)) or 0,
                    'like_count': item.get('like_count', item.get('likeCount', 0)) or 0,
                    'comment_count': item.get('comment_count', item.get('commentCount', 0)) or 0,
                    'share_count': item.get('share_count', 0) or 0,
                    'create_time': item.get('timestamp', 0) or 0,
                    'author': '', 'platform': 'kuaishou', 'type': 'video',
                }
                videos.append(v)
                task['total'] = len(videos)
                if 0 < max_videos <= len(videos): break
            if 0 < max_videos <= len(videos): break
            cursor = data.get('cursor', data.get('pcursor', ''))
            if not cursor: break
            time.sleep(1.5)

        if not videos:
            return grab_universal_profile(url, task_id, max_videos, 'kuaishou')
        task.update({'status': 'completed', 'videos': videos, 'total': len(videos),
                     'message': f'រកឃើញ {len(videos)} វីដេអូ'})
    except Exception as e:
        profile_tasks[task_id].update({'status': 'error', 'message': f'កំហុស: {e}'})


def grab_reddit_profile(url, task_id, max_videos=0):
    """Reddit Profile Grabber via TikHub API + yt-dlp fallback."""
    task = profile_tasks[task_id]
    try:
        task.update({'status': 'getting_profile', 'message': 'កំពុងទាញយក Reddit Profile...'})
        username = extract_username(url, 'reddit')
        if not username:
            m = re.search(r'reddit\.com/user/(\w+)', url, re.I)
            if m: username = m.group(1)
        if not username:
            return grab_universal_profile(url, task_id, max_videos, 'reddit')

        profile_info = _default_profile(username, username)
        task['profile'] = profile_info
        task.update({'status': 'grabbing', 'message': 'កំពុងទាញយក posts...'})

        videos, after, page = [], '', 0
        while True:
            page += 1
            task['message'] = f'ទំព័រ {page}... ({len(videos)} posts)'
            resp = api_reddit_get_user_posts(username, after=after)
            if not resp or resp.get('code') != 200: break
            data = resp.get('data', {})
            children = data.get('children', data.get('posts', data.get('items', [])))
            if not children: break
            for child in children:
                item = child.get('data', child) if isinstance(child, dict) and 'data' in child else child
                pid = item.get('id', item.get('name', ''))
                title = (item.get('title', '') or 'Post')[:200]
                thumb = item.get('thumbnail', '')
                if thumb in ('self', 'default', 'nsfw', 'spoiler', ''): thumb = ''
                permalink = item.get('permalink', '')
                post_url = f'https://www.reddit.com{permalink}' if permalink else ''
                has_video = bool(item.get('is_video') or item.get('media'))
                v = {
                    'id': str(pid), 'title': title,
                    'url': post_url, 'thumbnail': thumb, 'duration': 0,
                    'view_count': item.get('view_count', 0) or 0,
                    'like_count': item.get('ups', item.get('score', 0)) or 0,
                    'comment_count': item.get('num_comments', 0) or 0,
                    'share_count': item.get('num_crossposts', 0) or 0,
                    'create_time': int(item.get('created_utc', 0)),
                    'author': item.get('author', username),
                    'platform': 'reddit', 'type': 'video' if has_video else 'photo',
                }
                videos.append(v)
                task['total'] = len(videos)
                if 0 < max_videos <= len(videos): break
            if 0 < max_videos <= len(videos): break
            after = data.get('after', '')
            if not after: break
            time.sleep(1.5)

        if not videos:
            return grab_universal_profile(url, task_id, max_videos, 'reddit')
        task.update({'status': 'completed', 'videos': videos, 'total': len(videos),
                     'message': f'រកឃើញ {len(videos)} posts'})
    except Exception as e:
        profile_tasks[task_id].update({'status': 'error', 'message': f'កំហុស: {e}'})



def grab_universal_profile(url, task_id, max_videos=0, platform=''):
    pname = PLATFORMS.get(platform, {}).get('name', platform)
    try:
        task = profile_tasks[task_id]
        task.update({'status': 'getting_profile', 'message': f'កំពុងទាញយក {pname} Profile...'})
        username = extract_username(url, platform) or ''

        # For YouTube, ensure we get the videos tab
        grab_url = url
        if platform == 'youtube' and '@' in url and '/videos' not in url and '/shorts' not in url:
            grab_url = url.rstrip('/') + '/videos'

        opts = get_ydl_opts(platform, {
            'extract_flat': 'in_playlist',
            'playlistend': max_videos if max_videos > 0 else None,
            'ignoreerrors': True,
        })

        task['message'] = f'កំពុងស្កេន {pname}...'
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(grab_url, download=False)

        if not info:
            task.update({'status': 'error', 'message': f'រកមិនឃើញ {pname} Profile'}); return

        # Handle nested playlists (e.g., YouTube channel has sub-playlists)
        entries = []
        raw_entries = info.get('entries', [])
        if raw_entries is not None:
            for e in raw_entries:
                if e is None: continue
                if e.get('_type') == 'playlist' or e.get('entries'):
                    # Nested playlist — flatten
                    sub = e.get('entries', [])
                    if sub:
                        for se in sub:
                            if se: entries.append(se)
                else:
                    entries.append(e)

        # Build profile info
        profile_info = {
            'nickname': info.get('title', info.get('uploader', info.get('channel', username))) or username,
            'username': info.get('uploader_id', info.get('channel_id', username)) or username,
            'avatar': '', 'signature': (info.get('description', '') or '')[:200],
            'followers': info.get('channel_follower_count', 0) or 0,
            'following': 0, 'likes': 0,
            'video_count': info.get('playlist_count', 0) or len(entries),
        }
        thumbs = info.get('thumbnails', [])
        if thumbs and isinstance(thumbs[-1], dict):
            profile_info['avatar'] = thumbs[-1].get('url', '')

        task['profile'] = profile_info
        task.update({'status': 'grabbing', 'message': f'កំពុងដំណើរការ {len(entries)} posts...'})

        videos = []
        for e in entries:
            v = extract_ytdlp_entry(e, platform)
            if v:
                videos.append(v)
                task['total'] = len(videos)
                if 0 < max_videos <= len(videos):
                    break

        task.update({'status': 'completed', 'videos': videos, 'total': len(videos),
                     'profile': profile_info, 'message': f'រកឃើញ {len(videos)} posts'})
    except Exception as e:
        profile_tasks[task_id].update({'status': 'error', 'message': f'កំហុស: {e}'})


def _grab_ytdlp_fallback(url, task_id, max_videos, platform, username, profile_info):
    """Fallback to yt-dlp extract_flat for any platform."""
    task = profile_tasks[task_id]
    task['message'] = 'កំពុងប្រើ yt-dlp...'
    try:
        opts = get_ydl_opts(platform, {'extract_flat': 'in_playlist',
                                        'playlistend': max_videos if max_videos > 0 else None})
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        if info and info.get('entries'):
            entries = list(info['entries'])
            if not profile_info:
                profile_info = _default_profile(info.get('title', username or 'Unknown'), username or '')
            videos = [extract_ytdlp_entry(e, platform) for e in entries if e]
            videos = [v for v in videos if v]
            task.update({'status': 'completed', 'profile': profile_info or _default_profile(username, ''),
                         'videos': videos, 'total': len(videos),
                         'message': f'រកឃើញ {len(videos)} posts (yt-dlp)'})
            return
    except Exception:
        pass
    task.update({'status': 'error', 'message': 'រកមិនឃើញព័ត៌មាន Profile។ សូមពិនិត្យ URL។'})


def _default_profile(nickname, username):
    return {'nickname': nickname, 'username': username, 'avatar': '', 'signature': '',
            'followers': 0, 'following': 0, 'likes': 0, 'video_count': 0}


# ==================== Comment Extraction ====================
def extract_comments_for_url(url, platform=None):
    """Extract comments via yt-dlp (works best for YouTube)."""
    if not platform:
        platform = detect_platform(url)
    try:
        opts = get_ydl_opts(platform, {
            'getcomments': True,
            'extractor_args': {'youtube': {'comment_sort': ['top'], 'max_comments': ['100,20,20,5']}},
        })
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        comments = info.get('comments', [])
        return [{
            'author': c.get('author', 'Anonymous'),
            'text': c.get('text', ''),
            'likes': c.get('like_count', 0),
            'time': c.get('timestamp', 0),
            'author_thumbnail': c.get('author_thumbnail', ''),
        } for c in comments[:100]]
    except Exception:
        return []


# ==================== Search ====================
def search_videos_ydl(query, platform='youtube', count=20, search_type='keyword'):
    """Search for videos by keyword/hashtag via yt-dlp and Graph API."""
    # Prepare query based on search type
    actual_query = query
    if search_type == 'hashtag':
        actual_query = query.lstrip('#')

    # --- Facebook search via Graph API ---
    if platform == 'facebook':
        return _search_facebook(actual_query, count, search_type)

    # --- TikTok search via hashtag/keyword URL ---
    if platform == 'tiktok':
        return _search_tiktok(actual_query, count, search_type)

    # --- Pinterest search via yt-dlp ---
    if platform == 'pinterest':
        return _search_pinterest(actual_query, count)

    # --- yt-dlp based search ---
    search_prefixes = {
        'youtube': f'ytsearch{count}:{actual_query}',
        'twitter': f'https://x.com/search?q={actual_query}&f=video',
    }
    search_url = search_prefixes.get(platform)
    if not search_url:
        return []
    try:
        extra = {'extract_flat': True, 'playlistend': count}
        if platform == 'twitter':
            extra['extract_flat'] = False
        opts = get_ydl_opts(platform, extra)
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(search_url, download=False)
        entries = info.get('entries', []) if info else []
        results = []
        for e in entries:
            if e:
                v = extract_ytdlp_entry(e, platform)
                if v:
                    results.append(v)
                    if len(results) >= count:
                        break
        return results
    except Exception as ex:
        logging.warning(f'Search error ({platform}): {ex}')
        return []


def _search_facebook(query, count=20, search_type='keyword'):
    """Search Facebook via Graph API for videos/posts."""
    token = _load_fb_token()
    if not token:
        return []
    results = []
    try:
        # Search public pages/posts related to query
        if search_type == 'hashtag':
            # Search pages by hashtag keyword
            endpoint = 'search'
            params = {
                'q': query,
                'type': 'page',
                'fields': 'id,name,link,picture',
                'limit': min(count, 25),
            }
        else:
            # Search pages for keyword
            endpoint = 'search'
            params = {
                'q': query,
                'type': 'page',
                'fields': 'id,name,link,picture',
                'limit': min(count, 25),
            }
        data = fb_graph_request(endpoint, params, token)
        if data and 'data' in data:
            for page in data['data']:
                # Get videos from each found page
                page_id = page.get('id')
                if not page_id:
                    continue
                page_vids = fb_graph_request(f'{page_id}/videos', {
                    'fields': 'id,title,description,created_time,length,source,picture,likes.summary(true),comments.summary(true),views',
                    'limit': min(5, count - len(results)) if count > len(results) else 2,
                }, token)
                if page_vids and 'data' in page_vids:
                    for vid in page_vids['data']:
                        v = _extract_fb_graph_video(vid)
                        if v:
                            v['author'] = page.get('name', '')
                            results.append(v)
                            if len(results) >= count:
                                break
                if len(results) >= count:
                    break
        # Also try direct video search
        if len(results) < count:
            vid_search = fb_graph_request('search', {
                'q': query,
                'type': 'video',
                'fields': 'id,title,description,created_time,length,source,picture,from',
                'limit': min(count - len(results), 20),
            }, token)
            if vid_search and 'data' in vid_search:
                seen = {r.get('id') for r in results}
                for vid in vid_search['data']:
                    if vid.get('id') not in seen:
                        v = _extract_fb_graph_video(vid)
                        if v:
                            v['author'] = vid.get('from', {}).get('name', '')
                            results.append(v)
                            if len(results) >= count:
                                break
    except Exception as ex:
        logging.warning(f'Facebook search error: {ex}')
    return results


def _search_tiktok(query, count=20, search_type='keyword'):
    """Search TikTok via TikHub hybrid API first, then yt-dlp fallback."""
    results = []

    # Try Evil0ctal hybrid API for hashtag search
    if search_type == 'hashtag':
        tag_url = f'https://www.tiktok.com/tag/{query}'
        try:
            hybrid = api_hybrid_video_data(tag_url, minimal=False)
            if hybrid and hybrid.get('code') == 200:
                hd = hybrid.get('data', {})
                items = hd.get('itemList', hd.get('aweme_list', []))
                if isinstance(items, list):
                    for item in items:
                        v = extract_tiktok_api_item(item)
                        if v:
                            results.append(v)
                            if len(results) >= count:
                                return results
        except Exception:
            pass

    # yt-dlp fallback
    try:
        if search_type == 'hashtag':
            search_url = f'https://www.tiktok.com/tag/{query}'
        else:
            search_url = f'https://www.tiktok.com/search?q={query}'
        opts = get_ydl_opts('tiktok', {'extract_flat': True, 'playlistend': count})
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(search_url, download=False)
        entries = info.get('entries', []) if info else []
        for e in entries:
            if e:
                v = extract_ytdlp_entry(e, 'tiktok')
                if v:
                    # Avoid duplicates from hybrid results
                    if not any(r.get('id') == v.get('id') for r in results):
                        results.append(v)
                    if len(results) >= count:
                        break
        return results
    except Exception as ex:
        logging.warning(f'TikTok search error: {ex}')
        return results if results else []


def _search_pinterest(query, count=20):
    """Search Pinterest via yt-dlp."""
    try:
        search_url = f'https://www.pinterest.com/search/pins/?q={query}'
        opts = get_ydl_opts('pinterest', {'extract_flat': True, 'playlistend': count})
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(search_url, download=False)
        entries = info.get('entries', []) if info else []
        results = []
        for e in entries:
            if e:
                v = extract_ytdlp_entry(e, 'pinterest')
                if v:
                    results.append(v)
                    if len(results) >= count:
                        break
        return results
    except Exception as ex:
        logging.warning(f'Pinterest search error: {ex}')
        return []


# ==================== Flask Routes ====================

# Global error handlers — always return JSON for API routes
@app.errorhandler(404)
def not_found(e):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Route not found'}), 404
    return render_template('index.html'), 404

@app.errorhandler(500)
def internal_error(e):
    if request.path.startswith('/api/'):
        return jsonify({'error': f'Server error: {e}'}), 500
    return render_template('index.html'), 500

@app.errorhandler(405)
def method_not_allowed(e):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Method not allowed'}), 405
    return render_template('index.html'), 405

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/platforms')
def get_platforms():
    return jsonify(PLATFORMS)


@app.route('/api/info', methods=['POST'])
def get_video_info():
    data = request.get_json()
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'error': 'សូមបញ្ចូល URL'}), 400

    platform = detect_platform(url)
    if not platform:
        return jsonify({'error': 'URL មិនត្រឹមត្រូវ។ គាំទ្រ TikTok, Douyin, YouTube, Instagram, Facebook, X, Pinterest, Xiaohongshu, Bilibili, Reddit, Weibo, Threads, LinkedIn...'}), 400

    # --- Try TikHub Hybrid API first for TikTok / Douyin / Xiaohongshu / Bilibili ---
    if platform in ('tiktok', 'douyin', 'xiaohongshu', 'bilibili'):
        try:
            hybrid = api_hybrid_video_data(url, minimal=False)
            if hybrid and hybrid.get('code') == 200:
                hd = hybrid.get('data', {})
                # Support both TikTok and Douyin response structures
                vid = hd.get('video', hd)
                author_info = hd.get('author', {})
                stats = hd.get('statistics', hd.get('stats', {}))
                title = hd.get('desc', vid.get('title', 'Video'))
                thumb = ''
                if platform == 'tiktok':
                    vc = vid.get('cover', vid.get('dynamicCover', vid.get('originCover', '')))
                    if isinstance(vc, str): thumb = vc
                else:
                    cover = vid.get('cover', vid.get('origin_cover', {}))
                    if isinstance(cover, dict):
                        urls = cover.get('url_list', [])
                        if urls: thumb = urls[0]
                    elif isinstance(cover, str):
                        thumb = cover
                # Build download URL via nwm (no watermark)
                nwm_url = ''
                play_addr = vid.get('play_addr', {})
                if isinstance(play_addr, dict):
                    ul = play_addr.get('url_list', [])
                    if ul: nwm_url = ul[0]
                elif isinstance(play_addr, str):
                    nwm_url = play_addr
                if not nwm_url:
                    nwm_url = vid.get('download_addr', vid.get('downloadAddr', ''))
                    if isinstance(nwm_url, dict):
                        ul = nwm_url.get('url_list', [])
                        nwm_url = ul[0] if ul else ''

                dur = vid.get('duration', hd.get('duration', 0))
                if isinstance(dur, (int, float)) and dur > 10000:
                    dur = dur // 1000  # ms → s for Douyin

                return jsonify({
                    'title': (title or 'Video')[:200],
                    'description': (hd.get('desc', '') or '')[:500],
                    'thumbnail': thumb,
                    'duration': dur,
                    'author': author_info.get('nickname', author_info.get('uniqueId', 'Unknown')),
                    'view_count': stats.get('playCount', stats.get('play_count', 0)),
                    'like_count': stats.get('diggCount', stats.get('digg_count', 0)),
                    'comment_count': stats.get('commentCount', stats.get('comment_count', 0)),
                    'formats': [
                        {'format_id': 'nwm', 'ext': 'mp4', 'resolution': 'Original (No Watermark)',
                         'filesize': 0, 'has_video': True, 'has_audio': True, 'quality': 10,
                         'format_note': 'No Watermark'},
                    ] if nwm_url else [],
                    'url': url, 'platform': platform,
                    'upload_date': '',
                    'is_photo': not dur,
                    'nwm_url': nwm_url,
                    'api_source': 'tikhub',
                })
        except Exception:
            pass  # Fallback to yt-dlp below

    # --- yt-dlp fallback for all platforms ---
    try:
        opts = get_ydl_opts(platform, {'extract_flat': False})
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)

        formats = []
        if info.get('formats'):
            for f in info['formats']:
                fmt = {
                    'format_id': f.get('format_id', ''), 'ext': f.get('ext', 'mp4'),
                    'resolution': f.get('resolution', 'N/A'), 'filesize': f.get('filesize', 0),
                    'has_video': f.get('vcodec', 'none') != 'none',
                    'has_audio': f.get('acodec', 'none') != 'none',
                    'quality': f.get('quality', 0), 'format_note': f.get('format_note', ''),
                }
                if fmt['has_video']:
                    formats.append(fmt)

        thumb = info.get('thumbnail', '')
        if not thumb and info.get('thumbnails'):
            thumb = info['thumbnails'][-1].get('url', '')

        return jsonify({
            'title': info.get('title', 'Video'), 'description': (info.get('description', '') or '')[:500],
            'thumbnail': thumb, 'duration': info.get('duration', 0),
            'author': info.get('uploader', info.get('creator', info.get('channel', 'Unknown'))),
            'view_count': info.get('view_count', 0), 'like_count': info.get('like_count', 0),
            'comment_count': info.get('comment_count', 0), 'formats': formats,
            'url': url, 'platform': platform,
            'upload_date': info.get('upload_date', ''),
            'is_photo': not info.get('duration'),
        })
    except Exception as e:
        return jsonify({'error': f'កំហុស: {e}'}), 500


@app.route('/api/download', methods=['POST'])
def download_video():
    data = request.get_json()
    url = data.get('url', '').strip()
    fmt = data.get('format', 'video')
    quality = data.get('quality', '')       # e.g. '720p', '1080p', '4k'
    output_fmt = data.get('output_format', '')  # e.g. 'mp4', 'mkv', 'webm', 'mp3', 'wav', 'flac'
    if not url:
        return jsonify({'error': 'សូមបញ្ចូល URL'}), 400

    platform = detect_platform(url) or ''
    task_id = str(uuid.uuid4())[:8]

    if fmt == 'audio':
        codec = 'mp3'
        if output_fmt in ('wav', 'flac', 'aac', 'ogg', 'm4a'):
            codec = output_fmt
        filename = f'{platform}_audio_{task_id}.{codec}'
        ydl_opts = get_ydl_opts(platform, {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(DOWNLOAD_FOLDER, filename),
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': codec, 'preferredquality': '192'}],
            'progress_hooks': [lambda d: progress_hook(d, task_id)],
        })
    else:
        ext = output_fmt if output_fmt in ('mp4', 'mkv', 'webm', 'avi', 'mov') else 'mp4'
        # Choose best format based on quality
        if quality == '360p':
            fmt_str = 'best[height<=360][ext=mp4]/best[height<=360]/best'
        elif quality == '480p':
            fmt_str = 'best[height<=480][ext=mp4]/best[height<=480]/best'
        elif quality == '720p':
            fmt_str = 'bestvideo[height<=720]+bestaudio/best[height<=720]/best'
        elif quality == '1080p':
            fmt_str = 'bestvideo[height<=1080]+bestaudio/best[height<=1080]/best'
        elif quality == '1440p':
            fmt_str = 'bestvideo[height<=1440]+bestaudio/best[height<=1440]/best'
        elif quality == '4k':
            fmt_str = 'bestvideo[height<=2160]+bestaudio/best'
        elif quality == 'best':
            fmt_str = 'bestvideo+bestaudio/best'
        else:
            fmt_str = 'best[ext=mp4]/best'
        filename = f'{platform}_video_{task_id}.{ext}'
        ydl_opts = get_ydl_opts(platform, {
            'format': fmt_str,
            'outtmpl': os.path.join(DOWNLOAD_FOLDER, filename),
            'progress_hooks': [lambda d: progress_hook(d, task_id)],
            'merge_output_format': ext,
        })

    download_progress[task_id] = {'status': 'starting', 'percent': 0, 'speed': 0, 'eta': 0}

    def do_dl():
        try:
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            actual = next((f for f in os.listdir(DOWNLOAD_FOLDER) if task_id in f), filename)
            download_progress[task_id] = {'status': 'completed', 'percent': 100, 'filename': actual}
        except Exception as e:
            download_progress[task_id] = {'status': 'error', 'error': str(e)}

    threading.Thread(target=do_dl).start()
    return jsonify({'task_id': task_id})


@app.route('/api/progress/<task_id>')
def get_progress(task_id):
    return jsonify(download_progress.get(task_id, {'status': 'unknown'}))


@app.route('/api/file/<filename>')
def serve_file(filename):
    fp = os.path.join(DOWNLOAD_FOLDER, filename)
    if os.path.exists(fp):
        return send_file(fp, as_attachment=True)
    return jsonify({'error': 'រកមិនឃើញឯកសារ'}), 404


@app.route('/api/profile/grab', methods=['POST'])
def grab_profile():
    data = request.get_json()
    url = data.get('url', '').strip()
    max_videos = data.get('max_videos', 0)
    if not url:
        return jsonify({'error': 'សូមបញ្ចូល URL'}), 400

    platform = detect_platform(url)
    if not platform:
        return jsonify({'error': 'URL មិនត្រឹមត្រូវ'}), 400

    task_id = str(uuid.uuid4())[:8]
    profile_tasks[task_id] = {
        'status': 'starting', 'message': 'កំពុងចាប់ផ្តើម...',
        'profile': None, 'videos': [], 'total': 0, 'url': url, 'platform': platform,
    }

    grabbers = {
        'tiktok': grab_tiktok_profile,
        'douyin': grab_douyin_profile,
        'facebook': grab_facebook_profile,
        'instagram': grab_instagram_profile,
        'xiaohongshu': grab_xiaohongshu_profile,
        'bilibili': grab_bilibili_profile,
        'weibo': grab_weibo_profile,
        'twitter': grab_twitter_profile,
        'youtube': grab_youtube_profile,
        'threads': grab_threads_profile,
        'kuaishou': grab_kuaishou_profile,
        'reddit': grab_reddit_profile,
    }
    target = grabbers.get(platform, lambda u, t, m: grab_universal_profile(u, t, m, platform))
    threading.Thread(target=target, args=(url, task_id, max_videos)).start()
    return jsonify({'task_id': task_id, 'platform': platform})


@app.route('/api/profile/status/<task_id>')
def profile_status(task_id):
    task = profile_tasks.get(task_id, {'status': 'unknown'})
    result = {
        'status': task.get('status'), 'message': task.get('message', ''),
        'total': task.get('total', 0), 'profile': task.get('profile'),
        'platform': task.get('platform', ''),
    }
    if task.get('status') == 'completed':
        result['videos'] = task.get('videos', [])
    return jsonify(result)


@app.route('/api/profile/download', methods=['POST'])
def download_profile_video():
    data = request.get_json()
    url = data.get('url', '').strip()
    vid = data.get('video_id', '')
    media_type = data.get('type', 'video')
    source_url = data.get('source', '')
    if not url:
        return jsonify({'error': 'សូមបញ្ចូល URL'}), 400

    platform = detect_platform(url) or 'video'
    task_id = str(uuid.uuid4())[:8]

    # Handle photo download directly via source URL
    if media_type == 'photo' and source_url:
        download_progress[task_id] = {'status': 'starting', 'percent': 0, 'speed': 0, 'eta': 0}
        def do_photo_dl():
            try:
                ext = 'jpg'
                if '.png' in source_url.lower():
                    ext = 'png'
                elif '.webp' in source_url.lower():
                    ext = 'webp'
                filename = f'{platform}_photo_{vid}_{task_id}.{ext}'
                filepath = os.path.join(DOWNLOAD_FOLDER, filename)
                with httpx.Client(timeout=30, follow_redirects=True) as c:
                    r = c.get(source_url)
                    r.raise_for_status()
                    with open(filepath, 'wb') as f:
                        f.write(r.content)
                download_progress[task_id] = {'status': 'completed', 'percent': 100, 'filename': filename}
            except Exception as e:
                download_progress[task_id] = {'status': 'error', 'error': str(e)}
        threading.Thread(target=do_photo_dl).start()
        return jsonify({'task_id': task_id})

    filename = f'{platform}_{vid}_{task_id}.mp4'
    ydl_opts = get_ydl_opts(platform, {
        'format': 'best[ext=mp4]/best',
        'outtmpl': os.path.join(DOWNLOAD_FOLDER, filename),
        'progress_hooks': [lambda d: progress_hook(d, task_id)],
        'merge_output_format': 'mp4',
    })
    download_progress[task_id] = {'status': 'starting', 'percent': 0, 'speed': 0, 'eta': 0}

    def do_dl():
        try:
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            actual = next((f for f in os.listdir(DOWNLOAD_FOLDER) if task_id in f), filename)
            download_progress[task_id] = {'status': 'completed', 'percent': 100, 'filename': actual}
        except Exception as e:
            download_progress[task_id] = {'status': 'error', 'error': str(e)}

    threading.Thread(target=do_dl).start()
    return jsonify({'task_id': task_id})


@app.route('/api/profile/download-all', methods=['POST'])
def download_all_profile():
    data = request.get_json()
    videos = data.get('videos', [])
    if not videos:
        return jsonify({'error': 'មិនមានវីដេអូ'}), 400

    batch_id = str(uuid.uuid4())[:8]
    download_progress[batch_id] = {
        'status': 'batch_starting', 'percent': 0,
        'total': len(videos), 'completed': 0, 'failed': 0,
        'current': '', 'files': [],
    }

    def do_batch():
        total = len(videos)
        completed = failed = 0
        files = []
        for i, v in enumerate(videos):
            url = v.get('url', '')
            vid = v.get('id', str(i))
            media_type = v.get('type', 'video')
            source = v.get('source', '')
            if not url: failed += 1; continue
            download_progress[batch_id].update({
                'current': v.get('title', f'Post {i+1}')[:50],
                'percent': round((i / total) * 100, 1),
            })
            try:
                platform = detect_platform(url) or 'video'
                # Download photo directly from source URL
                if media_type == 'photo' and source:
                    ext = 'jpg'
                    if '.png' in source.lower(): ext = 'png'
                    elif '.webp' in source.lower(): ext = 'webp'
                    fname = f'batch_{batch_id}_{vid}.{ext}'
                    filepath = os.path.join(DOWNLOAD_FOLDER, fname)
                    with httpx.Client(timeout=30, follow_redirects=True) as c:
                        r = c.get(source)
                        r.raise_for_status()
                        with open(filepath, 'wb') as fw:
                            fw.write(r.content)
                    files.append(fname); completed += 1
                else:
                    fname = f'batch_{batch_id}_{vid}.mp4'
                    opts = get_ydl_opts(platform, {
                        'format': 'best[ext=mp4]/best',
                        'outtmpl': os.path.join(DOWNLOAD_FOLDER, fname),
                        'merge_output_format': 'mp4',
                    })
                    with YoutubeDL(opts) as ydl:
                        ydl.download([url])
                    actual = next((f for f in os.listdir(DOWNLOAD_FOLDER) if f'batch_{batch_id}_{vid}' in f), fname)
                    files.append(actual); completed += 1
            except Exception:
                failed += 1
            download_progress[batch_id].update({'completed': completed, 'failed': failed, 'files': files})
            time.sleep(0.5)
        download_progress[batch_id].update({
            'status': 'batch_completed', 'percent': 100,
            'completed': completed, 'failed': failed, 'files': files,
        })

    threading.Thread(target=do_batch).start()
    return jsonify({'task_id': batch_id, 'total': len(videos)})


@app.route('/api/comments', methods=['POST'])
def get_comments():
    data = request.get_json()
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'error': 'សូមបញ្ចូល URL'}), 400
    platform = detect_platform(url)
    comments = extract_comments_for_url(url, platform)
    return jsonify({'comments': comments, 'total': len(comments), 'platform': platform})


@app.route('/api/search', methods=['POST'])
def search_content():
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        platform = data.get('platform', 'youtube')
        count = data.get('count', 20)
        if isinstance(count, str):
            count = int(count) if count.isdigit() else 20
        if count <= 0:
            count = 999999  # "all" = no limit
        if not query:
            return jsonify({'error': 'សូមបញ្ចូលពាក្យស្វែងរក'}), 400

        search_type = data.get('search_type', 'keyword')
        results = search_videos_ydl(query, platform, count, search_type)
        return jsonify({'results': results, 'total': len(results), 'platform': platform, 'query': query, 'search_type': search_type})
    except Exception as e:
        logging.error(f'Search API error: {e}')
        return jsonify({'error': f'កំហុសក្នុងការស្វែងរក: {e}', 'results': [], 'total': 0}), 500


@app.route('/api/clean', methods=['POST'])
def clean_downloads():
    try:
        count = sum(1 for f in os.listdir(DOWNLOAD_FOLDER) if os.path.isfile(os.path.join(DOWNLOAD_FOLDER, f)))
        for f in os.listdir(DOWNLOAD_FOLDER):
            fp = os.path.join(DOWNLOAD_FOLDER, f)
            if os.path.isfile(fp):
                os.remove(fp)
        return jsonify({'message': f'បានលុប {count} ឯកសារ'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/cookies/status')
def cookies_status():
    """Check if cookies.txt is configured."""
    cfile = _get_cookies_file()
    if cfile:
        # Check which platforms have cookies
        platforms_with_cookies = set()
        try:
            with open(cfile, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    parts = line.split('\t')
                    if len(parts) >= 7:
                        domain = parts[0].lower()
                        if 'facebook' in domain: platforms_with_cookies.add('facebook')
                        if 'instagram' in domain: platforms_with_cookies.add('instagram')
                        if 'twitter' in domain or 'x.com' in domain: platforms_with_cookies.add('twitter')
        except Exception:
            pass
        return jsonify({
            'has_cookies': True,
            'file': 'cookies.txt',
            'platforms': list(platforms_with_cookies),
        })
    return jsonify({'has_cookies': False, 'platforms': []})


@app.route('/api/cookies/upload', methods=['POST'])
def upload_cookies():
    """Upload a cookies.txt file."""
    if 'file' not in request.files:
        # Check for raw text body
        text = request.get_data(as_text=True)
        if text and ('# Netscape HTTP Cookie File' in text or '.facebook.com' in text):
            with open(COOKIES_FILE, 'w', encoding='utf-8') as f:
                f.write(text)
            return jsonify({'success': True, 'message': 'បានរក្សាទុក cookies.txt'})
        return jsonify({'error': 'សូមភ្ជាប់ file cookies.txt'}), 400
    
    f = request.files['file']
    if f.filename:
        f.save(COOKIES_FILE)
        return jsonify({'success': True, 'message': 'បានរក្សាទុក cookies.txt'})
    return jsonify({'error': 'File is empty'}), 400


@app.route('/api/fb-token', methods=['GET'])
def get_fb_token():
    """Check if Facebook Graph API token is configured."""
    token = _load_fb_token()
    if token:
        # Show only last 6 chars for security
        masked = '•' * max(0, len(token) - 6) + token[-6:] if len(token) > 6 else token
        return jsonify({'has_token': True, 'masked': masked})
    return jsonify({'has_token': False})


@app.route('/api/fb-token', methods=['POST'])
def save_fb_token():
    """Save Facebook Graph API access token."""
    data = request.get_json()
    token = data.get('token', '').strip()
    if not token:
        # Delete token
        if os.path.isfile(FB_TOKEN_FILE):
            os.remove(FB_TOKEN_FILE)
        return jsonify({'success': True, 'message': 'បានលុប Token'})
    # Validate token by making a test request
    test = fb_graph_request('me', {'fields': 'id,name'}, token)
    if test and not test.get('error'):
        _save_fb_token(token)
        return jsonify({'success': True, 'message': f'បានរក្សាទុក Token ({test.get("name", "OK")})'})
    elif test and test.get('message'):
        return jsonify({'error': f'Token មិនត្រឹមត្រូវ: {test["message"]}'}), 400
    else:
        # Save anyway — some tokens only work for specific pages
        _save_fb_token(token)
        return jsonify({'success': True, 'message': 'បានរក្សាទុក Token (មិនបានផ្ទៀងផ្ទាត់)'})


# ==================== FFmpeg API Routes ====================
@app.route('/api/ffmpeg/status')
def ffmpeg_status():
    """Check FFmpeg availability and version."""
    if not HAS_FFMPEG:
        return jsonify({'available': False, 'message': 'FFmpeg not installed'})
    ok, stdout, stderr = ffmpeg_run(['-version'])
    version = ''
    if ok and stdout:
        first_line = stdout.split('\n')[0]
        version = first_line.strip()
    return jsonify({
        'available': True,
        'version': version,
        'path': FFMPEG_PATHS['ffmpeg'],
        'formats': {
            'video': ['mp4', 'mkv', 'webm', 'avi', 'mov'],
            'audio': ['mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a'],
        },
        'qualities': ['360p', '480p', '720p', '1080p', '1440p', '4k', 'best'],
    })


@app.route('/api/ffmpeg/convert', methods=['POST'])
def ffmpeg_convert_route():
    """Convert a downloaded file to a different format.
    Body: { filename, output_format, quality?, resolution?, audio_only? }
    """
    if not HAS_FFMPEG:
        return jsonify({'error': 'FFmpeg not installed'}), 400
    data = request.get_json()
    filename = data.get('filename', '')
    output_format = data.get('output_format', 'mp4')
    if not filename:
        return jsonify({'error': 'Missing filename'}), 400
    input_path = os.path.join(DOWNLOAD_FOLDER, filename)
    if not os.path.isfile(input_path):
        return jsonify({'error': 'File not found'}), 404

    task_id = str(uuid.uuid4())[:8]
    base_name = os.path.splitext(filename)[0]
    out_filename = f'{base_name}_converted_{task_id}.{output_format}'
    output_path = os.path.join(DOWNLOAD_FOLDER, out_filename)

    options = {
        'audio_only': data.get('audio_only', output_format in ('mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a')),
        'resolution': data.get('resolution', ''),
        'crf': data.get('crf', ''),
        'audio_quality': data.get('audio_quality', '192k'),
        'video_codec': data.get('video_codec', ''),
        'audio_codec': data.get('audio_codec', ''),
    }

    download_progress[task_id] = {'status': 'converting', 'percent': 50, 'speed': 0, 'eta': 0}

    def do_convert():
        try:
            ok, result = ffmpeg_convert(input_path, output_path, options)
            if ok:
                download_progress[task_id] = {'status': 'completed', 'percent': 100, 'filename': out_filename}
            else:
                download_progress[task_id] = {'status': 'error', 'error': f'Conversion failed: {result}'}
        except Exception as e:
            download_progress[task_id] = {'status': 'error', 'error': str(e)}

    threading.Thread(target=do_convert).start()
    return jsonify({'task_id': task_id, 'output_filename': out_filename})


@app.route('/api/ffmpeg/media-info', methods=['POST'])
def ffmpeg_media_info_route():
    """Get detailed media info for a downloaded file."""
    data = request.get_json()
    filename = data.get('filename', '')
    if not filename:
        return jsonify({'error': 'Missing filename'}), 400
    filepath = os.path.join(DOWNLOAD_FOLDER, filename)
    if not os.path.isfile(filepath):
        return jsonify({'error': 'File not found'}), 404
    if not HAS_FFMPEG:
        # Basic info without FFmpeg
        size = os.path.getsize(filepath)
        return jsonify({'filename': filename, 'size': size, 'ffmpeg': False})
    info = ffmpeg_get_media_info(filepath)
    if info:
        info['filename'] = filename
        info['ffmpeg'] = True
        return jsonify(info)
    return jsonify({'error': 'Could not read media info'}), 500


# ==================== Watermark Remover ====================
watermark_tasks = {}

@app.route('/api/watermark/remove', methods=['POST'])
def watermark_remove():
    """Remove watermark from a video via URL or uploaded file."""
    if not HAS_FFMPEG:
        return jsonify({'error': 'FFmpeg មិនទាន់ដំឡើង'}), 500

    task_id = str(uuid.uuid4())[:8]
    position = request.form.get('position', 'bottom-left')
    method = request.form.get('method', 'blur')
    blur_strength = int(request.form.get('blur_strength', '20'))
    video_url = request.form.get('url', '').strip()
    uploaded = request.files.get('file')

    input_path = None
    cleanup_input = False

    # Method 1: Download from URL first
    if video_url:
        try:
            platform = detect_platform(video_url) or 'unknown'
            dl_filename = f'wm_input_{task_id}.mp4'
            dl_path = os.path.join(DOWNLOAD_FOLDER, dl_filename)

            # Try API (no-watermark source) for TikTok/Douyin etc.
            nwm_url = None
            if platform in ('tiktok', 'douyin', 'xiaohongshu', 'bilibili'):
                try:
                    hybrid = api_hybrid_video_data(video_url, minimal=False)
                    if hybrid and hybrid.get('code') == 200:
                        hd = hybrid.get('data', {})
                        vid = hd.get('video', hd)
                        play_addr = vid.get('play_addr', {})
                        if isinstance(play_addr, dict):
                            ul = play_addr.get('url_list', [])
                            if ul: nwm_url = ul[0]
                        elif isinstance(play_addr, str):
                            nwm_url = play_addr
                        if not nwm_url:
                            da = vid.get('download_addr', vid.get('downloadAddr', ''))
                            if isinstance(da, dict):
                                ul = da.get('url_list', [])
                                nwm_url = ul[0] if ul else ''
                            elif isinstance(da, str):
                                nwm_url = da
                except Exception:
                    pass

            if nwm_url:
                # Download no-watermark version directly
                try:
                    with httpx.Client(timeout=60, follow_redirects=True) as c:
                        r = c.get(nwm_url)
                        if r.status_code == 200:
                            with open(dl_path, 'wb') as f:
                                f.write(r.content)
                            input_path = dl_path
                            cleanup_input = True
                except Exception:
                    pass

            if not input_path:
                # Download via yt-dlp
                opts = get_ydl_opts(platform, {
                    'format': 'best[ext=mp4]/best',
                    'outtmpl': dl_path,
                    'quiet': True,
                })
                with YoutubeDL(opts) as ydl:
                    ydl.download([video_url])
                # Find the actual downloaded file
                actual = next((os.path.join(DOWNLOAD_FOLDER, f) for f in os.listdir(DOWNLOAD_FOLDER) if task_id in f), dl_path)
                if os.path.isfile(actual):
                    input_path = actual
                    cleanup_input = True
                else:
                    return jsonify({'error': 'មិនអាចទាញយកវីដេអូ'}), 400

        except Exception as e:
            return jsonify({'error': f'កំហុសក្នុងការទាញយក: {e}'}), 500

    # Method 2: Uploaded file
    elif uploaded and uploaded.filename:
        ext = uploaded.filename.rsplit('.', 1)[-1].lower() if '.' in uploaded.filename else 'mp4'
        up_filename = f'wm_upload_{task_id}.{ext}'
        up_path = os.path.join(DOWNLOAD_FOLDER, up_filename)
        uploaded.save(up_path)
        input_path = up_path
        cleanup_input = True
    else:
        return jsonify({'error': 'សូមផ្តល់ URL ឬ Upload ឯកសារ'}), 400

    # Get video dimensions
    info = ffmpeg_get_media_info(input_path)
    if not info or not info.get('video_width'):
        if cleanup_input:
            try: os.remove(input_path)
            except: pass
        return jsonify({'error': 'មិនអាចអានព័ត៌មានវីដេអូ'}), 400

    w = info['video_width']
    h = info['video_height']

    output_filename = f'wm_clean_{task_id}.mp4'
    output_path = os.path.join(DOWNLOAD_FOLDER, output_filename)

    # Calculate watermark region based on position
    # Default watermark ~20% width, ~8% height
    wm_w = int(w * 0.25)
    wm_h = int(h * 0.08)
    pad = int(min(w, h) * 0.02)

    pos_map = {
        'top-left':      (pad, pad),
        'top-right':     (w - wm_w - pad, pad),
        'bottom-left':   (pad, h - wm_h - pad),
        'bottom-right':  (w - wm_w - pad, h - wm_h - pad),
        'bottom-center': ((w - wm_w) // 2, h - wm_h - pad),
        'auto':          (pad, h - wm_h - pad),  # Default: bottom-left (most common)
    }
    wm_x, wm_y = pos_map.get(position, pos_map['bottom-left'])

    watermark_tasks[task_id] = {'status': 'processing', 'percent': 0}

    def do_remove():
        try:
            if method == 'blur':
                # Blur watermark area
                vf = (f"split[main][blur];[blur]crop={wm_w}:{wm_h}:{wm_x}:{wm_y},"
                      f"boxblur={blur_strength}[blurred];"
                      f"[main][blurred]overlay={wm_x}:{wm_y}")
            elif method == 'crop':
                # Crop out watermark area (reduce video size)
                if position.startswith('bottom'):
                    crop_h = h - wm_h - pad
                    vf = f"crop={w}:{crop_h}:0:0"
                elif position.startswith('top'):
                    crop_h = h - wm_h - pad
                    vf = f"crop={w}:{crop_h}:0:{wm_h + pad}"
                else:
                    vf = f"crop={w - wm_w}:{h}:{wm_w}:0"
            elif method == 'delogo':
                # FFmpeg delogo filter
                vf = f"delogo=x={wm_x}:y={wm_y}:w={wm_w}:h={wm_h}:show=0"
            else:
                vf = (f"split[main][blur];[blur]crop={wm_w}:{wm_h}:{wm_x}:{wm_y},"
                      f"boxblur={blur_strength}[blurred];"
                      f"[main][blurred]overlay={wm_x}:{wm_y}")

            args = ['-i', input_path, '-vf', vf, '-c:a', 'copy', '-y', output_path]
            ok, stdout, stderr = ffmpeg_run(args, timeout=300)

            if ok and os.path.isfile(output_path):
                watermark_tasks[task_id] = {
                    'status': 'completed',
                    'percent': 100,
                    'filename': output_filename,
                    'original': os.path.basename(input_path)
                }
            else:
                watermark_tasks[task_id] = {'status': 'error', 'error': stderr[:500] if stderr else 'FFmpeg failed'}
        except Exception as e:
            watermark_tasks[task_id] = {'status': 'error', 'error': str(e)}

    threading.Thread(target=do_remove).start()
    return jsonify({'task_id': task_id, 'original': os.path.basename(input_path)})


@app.route('/api/watermark/progress/<task_id>')
def watermark_progress(task_id):
    """Check watermark removal progress."""
    return jsonify(watermark_tasks.get(task_id, {'status': 'unknown'}))


@app.route('/api/watermark/upload', methods=['POST'])
def watermark_upload():
    """Upload a video file for watermark removal (returns file info)."""
    uploaded = request.files.get('file')
    if not uploaded or not uploaded.filename:
        return jsonify({'error': 'No file uploaded'}), 400

    task_id = str(uuid.uuid4())[:8]
    ext = uploaded.filename.rsplit('.', 1)[-1].lower() if '.' in uploaded.filename else 'mp4'
    filename = f'wm_upload_{task_id}.{ext}'
    filepath = os.path.join(DOWNLOAD_FOLDER, filename)
    uploaded.save(filepath)

    info = ffmpeg_get_media_info(filepath) if HAS_FFMPEG else None
    return jsonify({
        'success': True,
        'filename': filename,
        'original_name': uploaded.filename,
        'size': os.path.getsize(filepath),
        'info': info
    })


# ==================== Sora2 Bulk Download (WatermarkRemover-AI) ====================
def _is_sora_url(url):
    """Check if URL is a valid Sora video URL."""
    url = url.lower().strip()
    return ('sora.chatgpt.com' in url or
            ('chatgpt.com' in url and '/p/s_' in url) or
            'sora.com' in url)


def _sora_extract_video_id(url):
    """Extract Sora video/post ID from URL.
    Supports:
      - https://sora.chatgpt.com/p/s_xxxxx
      - https://sora.chatgpt.com/share/sdr_xxxxx
      - https://sora.com/p/s_xxxxx
    """
    url = url.strip()
    # Match /p/s_xxx pattern  (post ID)
    m = re.search(r'/p/(s_[a-zA-Z0-9_]+)', url)
    if m:
        return m.group(1), 'post'
    # Match /share/sdr_xxx or /share/xxx pattern
    m = re.search(r'/share/([a-zA-Z0-9_-]+)', url)
    if m:
        return m.group(1), 'share'
    # Fallback: any s_xxx in URL
    m = re.search(r'(s_[a-f0-9]{20,})', url)
    if m:
        return m.group(1), 'post'
    return None, None


def _sora_fetch_api(video_id, id_type='post'):
    """Call Sora API to get video metadata. Returns dict with video URLs.
    Prioritizes clean (no watermark) source over watermarked versions."""
    api_url = f'https://sora.chatgpt.com/backend/project_y/post/{video_id}'

    # Headers mimicking the Sora Android app (gets watermarked URLs without auth)
    headers_api = {
        'User-Agent': 'Mozilla/5.0 (compatible; Discordbot/2.0; +https://discordapp.com)',
        'Accept': 'application/json',
        'Accept-Encoding': 'gzip',
        'Accept-Language': 'en-US,en;q=0.9',
    }

    try:
        if HAS_CURL_CFFI:
            # Use curl_cffi for TLS fingerprint impersonation
            session = cffi_requests.Session(impersonate='chrome110')
            r = session.get(api_url, headers=headers_api, timeout=30)
            r.raise_for_status()
            data = r.json()
        else:
            with httpx.Client(timeout=30, follow_redirects=True) as c:
                r = c.get(api_url, headers=headers_api)
                r.raise_for_status()
                data = r.json()

        # Extract video URLs from response
        post = data.get('post', data)
        attachments = post.get('attachments', [])
        if not attachments:
            logging.warning(f'Sora API: no attachments for {video_id}')
            return None

        att = attachments[0]
        encodings = att.get('encodings', {})
        result = {
            'video_id': video_id,
            'width': att.get('width', 0),
            'height': att.get('height', 0),
            'n_frames': att.get('n_frames', 0),
            'title': att.get('title', ''),
            'prompt': att.get('prompt', ''),
            'has_watermark': True,  # Assume watermarked by default
        }

        # Priority: source (clean/no watermark) > source_wm (watermarked) > md > downloadable
        if 'source' in encodings and encodings['source'].get('path'):
            result['video_url'] = encodings['source']['path']
            result['quality'] = 'source'
            result['has_watermark'] = False  # source = no watermark
            logging.info(f'Sora API: got CLEAN source (no watermark) for {video_id}')
        elif 'source_wm' in encodings and encodings['source_wm'].get('path'):
            result['video_url'] = encodings['source_wm']['path']
            result['quality'] = 'source_wm'
            result['has_watermark'] = True
            logging.info(f'Sora API: got watermarked source for {video_id}')
        elif 'md' in encodings and encodings['md'].get('path'):
            result['video_url'] = encodings['md']['path']
            result['quality'] = 'md'
            result['has_watermark'] = True
            logging.info(f'Sora API: got medium quality for {video_id}')
        else:
            # Fallback to top-level url or downloadable_url
            result['video_url'] = att.get('downloadable_url') or att.get('url', '')
            result['quality'] = 'downloadable'
            result['has_watermark'] = True

        # Also grab thumbnail
        if 'thumbnail' in encodings and encodings['thumbnail'].get('path'):
            result['thumbnail'] = encodings['thumbnail']['path']

        return result if result.get('video_url') else None

    except Exception as e:
        logging.error(f'Sora API call failed for {video_id}: {e}')
        return None


def _sora_fetch_from_html(url):
    """Fallback: scrape Sora share page HTML for video URL via meta tags."""
    headers_html = {
        'User-Agent': 'Mozilla/5.0 (compatible; Discordbot/2.0; +https://discordapp.com)',
        'Accept': 'text/html,application/xhtml+xml',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    try:
        if HAS_CURL_CFFI:
            session = cffi_requests.Session(impersonate='chrome110')
            r = session.get(url, headers=headers_html, timeout=30)
            html = r.text
        else:
            with httpx.Client(timeout=30, follow_redirects=True) as c:
                r = c.get(url, headers=headers_html)
                html = r.text

        # Try og:video meta tag
        m = re.search(r'<meta[^>]+property=["\']og:video["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
        if m:
            return {'video_url': m.group(1), 'quality': 'og:video'}

        # Try og:video:url
        m = re.search(r'<meta[^>]+property=["\']og:video:url["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
        if m:
            return {'video_url': m.group(1), 'quality': 'og:video:url'}

        # Try video src in HTML
        m = re.search(r'<video[^>]+src=["\']([^"\']+)["\']', html, re.I)
        if m:
            return {'video_url': m.group(1), 'quality': 'html-video'}

        # Try source tag
        m = re.search(r'<source[^>]+src=["\']([^"\']+\.mp4[^"\']*)["\']', html, re.I)
        if m:
            return {'video_url': m.group(1), 'quality': 'html-source'}

        # Try JSON data in script tags (Next.js __NEXT_DATA__)
        m = re.search(r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(.+?)</script>', html, re.I | re.S)
        if m:
            try:
                nd = json.loads(m.group(1))
                # Navigate common Next.js data structure
                props = nd.get('props', {}).get('pageProps', {})
                post = props.get('post', props)
                atts = post.get('attachments', [])
                if atts:
                    enc = atts[0].get('encodings', {})
                    for k in ['source', 'source_wm', 'md']:
                        if k in enc and enc[k].get('path'):
                            return {'video_url': enc[k]['path'], 'quality': f'nextdata-{k}'}
                    du = atts[0].get('downloadable_url') or atts[0].get('url')
                    if du:
                        return {'video_url': du, 'quality': 'nextdata-url'}
            except Exception:
                pass

        logging.warning(f'Sora HTML scrape: no video URL found in {url}')
        return None

    except Exception as e:
        logging.error(f'Sora HTML scrape failed: {e}')
        return None


def _sora_download_video(url, task_id):
    """Download a Sora video. Tries API first, then HTML scrape, then yt-dlp fallback.
    Returns dict with 'path' and 'has_watermark' keys, or None on failure."""
    dl_filename = f'sora_input_{task_id}.mp4'
    dl_path = os.path.join(DOWNLOAD_FOLDER, dl_filename)
    video_url = None
    has_watermark = True  # Assume watermarked unless proven otherwise

    # --- Method 1: Sora API ---
    video_id, id_type = _sora_extract_video_id(url)
    if video_id:
        logging.info(f'Sora: trying API for {video_id} (type={id_type})')
        api_data = _sora_fetch_api(video_id, id_type)
        if api_data and api_data.get('video_url'):
            video_url = api_data['video_url']
            has_watermark = api_data.get('has_watermark', True)
            quality = api_data.get('quality', 'unknown')
            logging.info(f'Sora API: got video URL (quality={quality}, has_watermark={has_watermark})')

    # --- Method 2: HTML scrape fallback ---
    if not video_url:
        logging.info(f'Sora: trying HTML scrape for {url}')
        html_data = _sora_fetch_from_html(url)
        if html_data and html_data.get('video_url'):
            video_url = html_data['video_url']
            has_watermark = True  # HTML scrape doesn't indicate watermark status
            logging.info(f'Sora HTML: got video URL (quality={html_data.get("quality")})')

    # --- Method 3: Direct download from extracted URL ---
    if video_url:
        try:
            dl_headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'Referer': 'https://sora.chatgpt.com/',
            }
            if HAS_CURL_CFFI:
                session = cffi_requests.Session(impersonate='chrome110')
                r = session.get(video_url, headers=dl_headers, timeout=120)
                with open(dl_path, 'wb') as f:
                    f.write(r.content)
            else:
                with httpx.Client(timeout=120, follow_redirects=True) as c:
                    r = c.get(video_url, headers=dl_headers)
                    r.raise_for_status()
                    with open(dl_path, 'wb') as f:
                        f.write(r.content)

            if os.path.isfile(dl_path) and os.path.getsize(dl_path) > 10000:
                logging.info(f'Sora: downloaded {os.path.getsize(dl_path)} bytes to {dl_path}')
                return {'path': dl_path, 'has_watermark': has_watermark}
            else:
                logging.warning(f'Sora: downloaded file too small ({os.path.getsize(dl_path) if os.path.isfile(dl_path) else 0} bytes)')
                if os.path.isfile(dl_path):
                    os.remove(dl_path)
        except Exception as e:
            logging.error(f'Sora direct download failed: {e}')

    # --- Method 4: yt-dlp fallback (generic extractor) ---
    logging.info(f'Sora: trying yt-dlp fallback for {url}')
    try:
        opts = get_ydl_opts('sora', {
            'format': 'best[ext=mp4]/best',
            'outtmpl': dl_path,
            'quiet': True,
            'no_warnings': True,
        })
        with YoutubeDL(opts) as ydl:
            ydl.download([url])
        if os.path.isfile(dl_path):
            return {'path': dl_path, 'has_watermark': True}  # yt-dlp = assume watermarked
        for f in os.listdir(DOWNLOAD_FOLDER):
            if task_id in f and f.startswith('sora_input_'):
                return {'path': os.path.join(DOWNLOAD_FOLDER, f), 'has_watermark': True}
    except Exception as e:
        logging.error(f'Sora yt-dlp fallback failed: {e}')

    return None


def _sora_get_video_info(input_path):
    """Get video width and height using ffprobe."""
    if not HAS_FFMPEG:
        return None, None
    ffprobe = FFMPEG_PATHS['ffprobe']
    try:
        cmd = [
            ffprobe, '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height',
            '-of', 'csv=s=x:p=0',
            input_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            parts = result.stdout.strip().split('x')
            if len(parts) == 2:
                return int(parts[0]), int(parts[1])
    except Exception as e:
        logging.error(f'ffprobe error: {e}')
    return None, None


def _sora_remove_watermark(input_path, output_dir, task_id, **kwargs):
    """Remove Sora watermark using FFmpeg delogo filter.
    Sora watermarks are typically in the bottom-right corner.
    Uses multiple delogo regions to cover different watermark positions."""
    if not HAS_FFMPEG:
        logging.error('FFmpeg not available for watermark removal')
        return None

    ffmpeg = FFMPEG_PATHS['ffmpeg']
    base = os.path.splitext(os.path.basename(input_path))[0]
    output_file = os.path.join(output_dir, f'{base}_no_watermark.mp4')

    # Get video dimensions
    width, height = _sora_get_video_info(input_path)
    if not width or not height:
        # Default to common Sora resolutions
        width, height = 1920, 1080
        logging.warning(f'Could not detect resolution, assuming {width}x{height}')

    logging.info(f'Sora delogo: video={width}x{height}, input={input_path}')

    # Sora watermark positions (relative to video dimensions):
    # 1. Bottom-right: "sora" text watermark
    # 2. Bottom-left: possible ChatGPT/OpenAI branding
    # Calculate watermark regions
    wm_w = int(width * 0.12)   # ~12% of width
    wm_h = int(height * 0.06)  # ~6% of height

    # Bottom-right watermark (main Sora watermark)
    br_x = width - wm_w - int(width * 0.02)
    br_y = height - wm_h - int(height * 0.02)

    # Bottom-left watermark (OpenAI/ChatGPT small text)
    bl_x = int(width * 0.02)
    bl_y = height - wm_h - int(height * 0.02)

    # Build FFmpeg filter: apply delogo for both regions
    delogo_filter = (
        f'delogo=x={br_x}:y={br_y}:w={wm_w}:h={wm_h}:show=0,'
        f'delogo=x={bl_x}:y={bl_y}:w={wm_w}:h={wm_h}:show=0'
    )

    cmd = [
        ffmpeg, '-y',
        '-i', input_path,
        '-vf', delogo_filter,
        '-c:v', 'libx264',
        '-preset', 'medium',
        '-crf', '18',
        '-c:a', 'copy',
        '-movflags', '+faststart',
        output_file
    ]

    logging.info(f'FFmpeg delogo command: {" ".join(cmd)}')

    # Update progress
    task = sora_tasks.get(task_id)
    if task:
        task['ai_progress'] = 10

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding='utf-8',
        errors='replace',
    )

    # Parse FFmpeg progress from stderr
    # Get video duration first
    duration_sec = None
    for line in proc.stderr:
        line = line.strip()
        # Parse duration: "Duration: HH:MM:SS.ms"
        dur_match = re.search(r'Duration:\s*(\d{2}):(\d{2}):(\d{2})\.(\d+)', line)
        if dur_match and not duration_sec:
            h, m, s = int(dur_match.group(1)), int(dur_match.group(2)), int(dur_match.group(3))
            duration_sec = h * 3600 + m * 60 + s

        # Parse time progress: "time=HH:MM:SS.ms"
        time_match = re.search(r'time=(\d{2}):(\d{2}):(\d{2})\.(\d+)', line)
        if time_match and duration_sec and duration_sec > 0:
            h, m, s = int(time_match.group(1)), int(time_match.group(2)), int(time_match.group(3))
            current_sec = h * 3600 + m * 60 + s
            pct = min(int((current_sec / duration_sec) * 100), 99)
            if task:
                task['ai_progress'] = pct

    proc.wait()

    if proc.returncode != 0:
        logging.error(f'FFmpeg delogo failed (return code {proc.returncode})')
        return None

    if os.path.isfile(output_file) and os.path.getsize(output_file) > 10000:
        logging.info(f'Sora delogo success: {output_file} ({os.path.getsize(output_file)} bytes)')
        if task:
            task['ai_progress'] = 100
        return output_file

    logging.error('FFmpeg delogo: output file missing or too small')
    return None


def _sora_process_batch(task_id, urls, settings):
    """Process a batch of Sora URLs: download + watermark removal (only if needed)."""
    task = sora_tasks[task_id]
    results = []
    errors = []
    total = len(urls)

    output_dir = os.path.join(DOWNLOAD_FOLDER, f'sora_output_{task_id}')
    os.makedirs(output_dir, exist_ok=True)

    for i, url in enumerate(urls):
        url = url.strip()
        if not url:
            continue
        task['current'] = i + 1
        task['current_url'] = url
        task['status'] = 'downloading'
        task['ai_progress'] = 0
        # Overall percent: each video = 100/total, split into download (20%) + processing (80%)
        base_pct = int((i / total) * 100)
        task['percent'] = base_pct

        try:
            # Step 1: Download Sora video
            vid_id = f'{task_id}_{i}'
            dl_result = _sora_download_video(url, vid_id)
            if not dl_result or not os.path.isfile(dl_result.get('path', '')):
                errors.append({'url': url, 'error': 'Failed to download video from Sora'})
                continue

            input_path = dl_result['path']
            has_watermark = dl_result.get('has_watermark', True)

            task['percent'] = base_pct + int((1 / total) * 20)

            if has_watermark:
                # Step 2a: Remove watermark with FFmpeg delogo
                task['status'] = 'removing_watermark'
                logging.info(f'Sora: video has watermark, applying FFmpeg delogo removal')
                output_file = _sora_remove_watermark(
                    input_path, output_dir, task_id
                )
            else:
                # Step 2b: Already clean — just re-encode to clean MP4 (Full HD)
                task['status'] = 'removing_watermark'
                task['ai_progress'] = 50
                logging.info(f'Sora: video is CLEAN (no watermark), copying to output as clean MP4')
                base = os.path.splitext(os.path.basename(input_path))[0]
                output_file = os.path.join(output_dir, f'{base}_no_watermark.mp4')

                # Copy clean source directly (no re-encode needed for clean source)
                shutil.copy2(input_path, output_file)

                if os.path.isfile(output_file) and os.path.getsize(output_file) > 10000:
                    task['ai_progress'] = 100
                    logging.info(f'Sora: clean copy success: {output_file}')
                else:
                    output_file = None
                    logging.error('Sora: clean copy failed')

            if output_file and os.path.isfile(output_file):
                clean_filename = os.path.basename(output_file)
                results.append({
                    'url': url,
                    'clean_file': clean_filename,
                    'original_file': os.path.basename(input_path),
                    'output_dir': f'sora_output_{task_id}',
                    'success': True,
                    'was_clean': not has_watermark,
                })
            else:
                errors.append({'url': url, 'error': 'FFmpeg watermark removal failed'})

            task['percent'] = base_pct + int((1 / total) * 100)

        except Exception as e:
            logging.error(f'Sora process error: {e}')
            errors.append({'url': url, 'error': str(e)})

    task['status'] = 'completed'
    task['percent'] = 100
    task['results'] = results
    task['errors'] = errors


@app.route('/api/sora/download', methods=['POST'])
def sora_bulk_download():
    """Start bulk Sora2 video download + watermark removal."""
    if not HAS_FFMPEG:
        return jsonify({'error': 'FFmpeg not installed — please install static-ffmpeg'}), 500

    data = request.get_json() or {}
    urls_raw = data.get('urls', [])

    # Accept string (newline-separated) or list
    if isinstance(urls_raw, str):
        urls_raw = [u.strip() for u in urls_raw.split('\n') if u.strip()]

    # Validate URLs
    valid_urls = []
    invalid = []
    for u in urls_raw:
        u = u.strip()
        if not u:
            continue
        if _is_sora_url(u):
            valid_urls.append(u)
        else:
            invalid.append(u)

    if not valid_urls:
        return jsonify({'error': 'Please enter at least one Sora video URL', 'invalid': invalid}), 400

    settings = {}

    task_id = str(uuid.uuid4())[:8]
    sora_tasks[task_id] = {
        'status': 'starting',
        'total': len(valid_urls),
        'current': 0,
        'current_url': '',
        'percent': 0,
        'ai_progress': 0,
        'results': [],
        'errors': [],
        'invalid': invalid,
    }

    threading.Thread(target=_sora_process_batch, args=(task_id, valid_urls, settings)).start()
    return jsonify({
        'task_id': task_id,
        'total': len(valid_urls),
        'invalid': invalid,
    })


@app.route('/api/sora/status/<task_id>')
def sora_status(task_id):
    """Check Sora2 bulk download task status."""
    task = sora_tasks.get(task_id)
    if not task:
        return jsonify({'status': 'unknown'}), 404
    return jsonify(task)


@app.route('/api/sora/download-file/<task_dir>/<filename>')
def sora_download_file(task_dir, filename):
    """Download a processed Sora video file."""
    safe_dir = os.path.join(DOWNLOAD_FOLDER, task_dir)
    safe_file = os.path.join(safe_dir, filename)
    if not os.path.isfile(safe_file):
        return jsonify({'error': 'File not found'}), 404
    return send_file(safe_file, as_attachment=True, download_name=filename)


@app.route('/api/sora/download-original/<filename>')
def sora_download_original(filename):
    """Download the original (with watermark) Sora video."""
    safe_file = os.path.join(DOWNLOAD_FOLDER, filename)
    if not os.path.isfile(safe_file):
        return jsonify({'error': 'File not found'}), 404
    return send_file(safe_file, as_attachment=True, download_name=filename)


# ==================== Save Location ====================
@app.route('/api/save-location', methods=['GET'])
def get_save_location():
    """Get current download save folder path."""
    global DOWNLOAD_FOLDER
    exists = os.path.isdir(DOWNLOAD_FOLDER)
    try:
        file_count = sum(1 for f in os.listdir(DOWNLOAD_FOLDER) if os.path.isfile(os.path.join(DOWNLOAD_FOLDER, f))) if exists else 0
        total_size = sum(os.path.getsize(os.path.join(DOWNLOAD_FOLDER, f)) for f in os.listdir(DOWNLOAD_FOLDER) if os.path.isfile(os.path.join(DOWNLOAD_FOLDER, f))) if exists else 0
    except Exception:
        file_count = 0
        total_size = 0
    return jsonify({
        'path': DOWNLOAD_FOLDER,
        'exists': exists,
        'file_count': file_count,
        'total_size': total_size
    })


@app.route('/api/save-location', methods=['POST'])
def set_save_location():
    """Change download save folder path."""
    global DOWNLOAD_FOLDER
    data = request.get_json() or {}
    new_path = data.get('path', '').strip()
    if not new_path:
        return jsonify({'error': 'សូមបញ្ចូល path'}), 400

    # Normalize path
    new_path = os.path.normpath(new_path)

    # Try to create if doesn't exist
    try:
        os.makedirs(new_path, exist_ok=True)
    except Exception as e:
        return jsonify({'error': f'មិនអាចបង្កើត folder: {e}'}), 400

    if not os.path.isdir(new_path):
        return jsonify({'error': 'Path មិនមាន'}), 400

    # Test write permission
    try:
        test_file = os.path.join(new_path, '.write_test')
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
    except Exception:
        return jsonify({'error': 'មិនអាចសរសេរក្នុង folder នេះ'}), 400

    DOWNLOAD_FOLDER = new_path
    logging.info(f'Download folder changed to: {DOWNLOAD_FOLDER}')
    return jsonify({'success': True, 'path': DOWNLOAD_FOLDER})


@app.route('/api/save-location/open', methods=['POST'])
def open_save_location():
    """Open the download folder in system file explorer."""
    import subprocess
    if not os.path.isdir(DOWNLOAD_FOLDER):
        os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
    try:
        if os.name == 'nt':
            subprocess.Popen(['explorer', DOWNLOAD_FOLDER])
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', DOWNLOAD_FOLDER])
        else:
            subprocess.Popen(['xdg-open', DOWNLOAD_FOLDER])
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== Donate (Bakong KHQR) ====================
try:
    from bakong_khqr import KHQR
    _khqr_client = KHQR(BAKONG_TOKEN)
    logging.info('Bakong KHQR initialized')
except Exception as e:
    _khqr_client = None
    logging.warning(f'Bakong KHQR init failed: {e}')

# Store active QR sessions {md5: {amount, generated_at, ...}}
_donate_sessions = {}


def _send_telegram_notification(amount, tran_id):
    """Send Telegram notification on successful donation."""
    try:
        from datetime import datetime
        dt = datetime.now().strftime('%d-%b-%Y | %I:%M:%S %p')
        msg = (f"💝 ការបរិច្ចាគថ្មី:\n"
               f"💰 ចំនួនទឹកប្រាក់: {amount}$\n"
               f"🔢 លេខប្រតិបត្តិការ: {tran_id}\n"
               f"🕓 ពេលវេលា: {dt}\n"
               f"✅ ស្ថានភាព: បរិច្ចាគជោគជ័យ")
        url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
        httpx.post(url, json={'chat_id': TELEGRAM_CHAT_ID, 'text': msg}, timeout=10)
    except Exception as e:
        logging.error(f'Telegram notify error: {e}')


@app.route('/api/donate/generate-qr', methods=['POST'])
def donate_generate_qr():
    """Generate Bakong KHQR QR code for donation."""
    if not _khqr_client:
        return jsonify({'error': 'KHQR មិនទាន់រួចរាល់'}), 500

    data = request.get_json() or {}
    amount = data.get('amount', 1)
    try:
        amount = max(0.5, float(amount))
    except (ValueError, TypeError):
        amount = 1.0

    try:
        qr = _khqr_client.create_qr(
            bank_account=BAKONG_ACCOUNT,
            merchant_name=BAKONG_MERCHANT_NAME,
            merchant_city=BAKONG_MERCHANT_CITY,
            amount=amount,
            currency='USD',
            store_label='Donate',
            phone_number='',
            bill_number='',
            terminal_label='SMM'
        )
        md5 = _khqr_client.generate_md5(qr)

        # QR image via external API
        import urllib.parse
        qr_image_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={urllib.parse.quote(qr)}"

        # Store session
        import time
        _donate_sessions[md5] = {
            'amount': amount,
            'generated_at': time.time(),
            'paid': False
        }

        # Cleanup old sessions (> 5 min)
        cutoff = time.time() - 300
        expired = [k for k, v in _donate_sessions.items() if v['generated_at'] < cutoff]
        for k in expired:
            del _donate_sessions[k]

        return jsonify({
            'success': True,
            'qr_image_url': qr_image_url,
            'md5': md5,
            'amount': amount,
            'expiry': BAKONG_QR_EXPIRY,
            'merchant': BAKONG_MERCHANT_NAME
        })
    except Exception as e:
        logging.error(f'KHQR generate error: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/api/donate/check-status')
def donate_check_status():
    """Check Bakong KHQR payment status."""
    md5 = request.args.get('md5', '')
    if not md5 or not _khqr_client:
        return jsonify({'status': 'UNPAID'})

    session = _donate_sessions.get(md5)
    if not session:
        return jsonify({'status': 'UNPAID'})

    # Already confirmed paid
    if session.get('paid'):
        return jsonify({'status': 'PAID'})

    try:
        import time
        # Check expiry
        elapsed = time.time() - session['generated_at']
        if elapsed > BAKONG_QR_EXPIRY:
            return jsonify({'status': 'EXPIRED'})

        result = _khqr_client.check_payment(md5)
        if result and 'PAID' in str(result).upper():
            session['paid'] = True
            _send_telegram_notification(session['amount'], md5)
            return jsonify({'status': 'PAID'})

        return jsonify({'status': 'UNPAID'})
    except Exception as e:
        logging.error(f'KHQR check error: {e}')
        return jsonify({'status': 'UNPAID'})


if __name__ == '__main__':
    print("=" * 60)
    print("  Social Media Downloader — Multi-Platform")
    print("  TikTok | Douyin | YouTube | Instagram | Facebook")
    print("  X (Twitter) | Pinterest | Kuaishou")
    print("=" * 60)
    print("  Browser: http://localhost:5000")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5000)
