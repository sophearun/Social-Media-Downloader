<?php
/**
 * index.php — PHP entry point for the Social Media Downloader.
 * Serves the same UI as templates/index.html but with PHP auth links
 * and corrected static asset paths.
 */
require_once __DIR__ . '/config/app.php';
require_once __DIR__ . '/includes/auth.php';
require_once __DIR__ . '/includes/functions.php';

$_user    = currentUser();
$_isAdmin = ($_user['role'] ?? '') === 'admin';
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="theme-color" content="#030712">
    <title>Social Media Downloader — Multi-Platform</title>
    <link rel="stylesheet" href="/static/css/style.css">
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
    tailwind.config = {
        darkMode: 'class',
        theme: {
            extend: {
                colors: {
                    primary: { DEFAULT: '#8b5cf6', hover: '#a78bfa', dark: '#7c3aed' },
                    accent:  { DEFAULT: '#22d3ee', hover: '#67e8f9' },
                    surface: { DEFAULT: '#0f172a', card: '#1e293b', input: '#0f172a' },
                },
                fontFamily: {
                    sans:    ['Inter', 'Battambang', 'Khmer', 'system-ui', 'sans-serif'],
                    display: ['Koulen', 'Battambang', 'Khmer', 'sans-serif'],
                },
                borderRadius: { '2xl': '16px', xl: '12px', lg: '10px' },
            }
        }
    }
    </script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Khmer&family=Koulen&family=Battambang:wght@300;400;700;900&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <style>
    /* Auth pill in header */
    .auth-bar{display:flex;align-items:center;gap:.5rem;margin-left:auto}
    .auth-pill{display:inline-flex;align-items:center;gap:.4rem;padding:.35rem .85rem;border-radius:999px;font-size:.78rem;font-weight:600;text-decoration:none;transition:all .2s;border:1px solid transparent}
    .auth-pill-ghost{border-color:rgba(148,163,184,.18);color:#94a3b8}
    .auth-pill-ghost:hover{border-color:rgba(139,92,246,.5);color:#a78bfa;text-decoration:none}
    .auth-pill-primary{background:linear-gradient(135deg,#8b5cf6,#6d28d9);color:#fff}
    .auth-pill-primary:hover{background:linear-gradient(135deg,#a78bfa,#8b5cf6);text-decoration:none}
    .auth-avatar{width:28px;height:28px;border-radius:50%;object-fit:cover;border:2px solid rgba(139,92,246,.4)}
    </style>
</head>
<body>
    <div class="bg-animation">
        <div class="bg-circle c1"></div>
        <div class="bg-circle c2"></div>
        <div class="bg-circle c3"></div>
    </div>

    <div class="container">
        <!-- Header -->
        <header class="header">
            <div class="logo">
                <div class="logo-icon"><i class="fas fa-download"></i></div>
                <div class="logo-text">
                    <h1>Social Media Downloader</h1>
                    <p class="subtitle">កម្មវិធីទាញយកវីដេអូពីបណ្តាញសង្គម</p>
                </div>
            </div>

            <!-- Auth bar -->
            <div class="auth-bar">
                <?php if ($_user): ?>
                    <?php if ($_isAdmin): ?>
                    <a href="/admin" class="auth-pill auth-pill-ghost" title="Admin Panel">
                        <i class="fas fa-shield-halved"></i> <span class="hidden sm:inline">Admin</span>
                    </a>
                    <?php endif; ?>
                    <a href="/profile" class="auth-pill auth-pill-ghost">
                        <img src="<?= sanitize(!empty($_user['avatar']) ? $_user['avatar'] : generateAvatar($_user['full_name'] ?: $_user['username'], 28)) ?>"
                             alt="Avatar" class="auth-avatar">
                        <span class="hidden sm:inline"><?= sanitize($_user['username']) ?></span>
                    </a>
                    <a href="/logout" class="auth-pill auth-pill-ghost" title="Logout">
                        <i class="fas fa-right-from-bracket"></i>
                    </a>
                <?php else: ?>
                    <a href="/login"    class="auth-pill auth-pill-ghost"><i class="fas fa-right-to-bracket"></i> Login</a>
                    <a href="/register" class="auth-pill auth-pill-primary"><i class="fas fa-user-plus"></i> Register</a>
                <?php endif; ?>
            </div>

            <button id="donateBtn" class="donate-btn" title="ជួយគាំទ្រ">
                <i class="fas fa-heart"></i>
                <span>Donate</span>
            </button>
            <div class="platform-icons">
                <span class="pi" style="color:#fe2c55" title="TikTok"><i class="fab fa-tiktok"></i></span>
                <span class="pi" style="color:#ff0000" title="YouTube"><i class="fab fa-youtube"></i></span>
                <span class="pi" style="color:#e4405f" title="Instagram"><i class="fab fa-instagram"></i></span>
                <span class="pi" style="color:#1877f2" title="Facebook"><i class="fab fa-facebook"></i></span>
                <span class="pi" style="color:#fff"    title="X / Twitter"><i class="fab fa-x-twitter"></i></span>
                <span class="pi" style="color:#bd081c" title="Pinterest"><i class="fab fa-pinterest"></i></span>
                <span class="pi" style="color:#00f0ff" title="Douyin"><i class="fas fa-music"></i></span>
                <span class="pi" style="color:#ff2442" title="Xiaohongshu"><i class="fas fa-book"></i></span>
                <span class="pi" style="color:#000"    title="Threads"><i class="fab fa-threads"></i></span>
                <span class="pi" style="color:#0077b5" title="LinkedIn"><i class="fab fa-linkedin"></i></span>
            </div>
        </header>

        <!-- Tab Navigation -->
        <nav class="tab-nav">
            <button class="tab-btn active" data-tab="download"><i class="fas fa-download"></i><span>ទាញយក</span></button>
            <button class="tab-btn" data-tab="profile"><i class="fas fa-user-circle"></i><span>Profile Grabber</span></button>
            <button class="tab-btn" data-tab="watermark"><i class="fas fa-eraser"></i><span>Watermark Remover</span></button>
            <button class="tab-btn" data-tab="sora2"><i class="fas fa-wand-magic-sparkles"></i><span>Sora2 Download</span></button>
            <button class="tab-btn" data-tab="search"><i class="fas fa-search"></i><span>Search</span></button>
        </nav>

        <!-- ===== TAB 1: Single Download ===== -->
        <div id="tab-download" class="tab-content active">
            <section class="input-section">
                <div class="input-card">
                    <div class="input-wrapper">
                        <div class="input-icon"><i class="fas fa-link"></i></div>
                        <input type="text" id="urlInput"
                               placeholder="បិទភ្ជាប់តំណវីដេអូ (TikTok, YouTube, IG, FB, X, Douyin, Xiaohongshu, Bilibili...)"
                               autocomplete="off">
                        <button id="pasteBtn" class="icon-btn" title="Paste"><i class="fas fa-paste"></i></button>
                        <button id="clearBtn" class="icon-btn" title="Clear" style="display:none"><i class="fas fa-times"></i></button>
                    </div>
                    <div id="platformBadge" class="detected-platform" style="display:none">
                        <i id="platformBadgeIcon" class=""></i> <span id="platformBadgeName"></span>
                    </div>
                    <button id="fetchBtn" class="primary-btn"><i class="fas fa-search"></i><span>ស្វែងរកវីដេអូ</span></button>
                </div>
            </section>

            <section id="loadingSection" class="state-section" style="display:none">
                <div class="state-card">
                    <div class="spinner"><div class="spinner-ring"></div><i class="fas fa-download spinner-icon"></i></div>
                    <p class="state-text">កំពុងស្វែងរកវីដេអូ...</p>
                </div>
            </section>

            <section id="errorSection" class="state-section" style="display:none">
                <div class="state-card error">
                    <i class="fas fa-circle-exclamation state-icon error-icon"></i>
                    <p id="errorText" class="state-text"></p>
                    <button id="retryBtn" class="primary-btn"><i class="fas fa-rotate-right"></i><span>ព្យាយាមម្តងទៀត</span></button>
                </div>
            </section>

            <section id="resultSection" style="display:none">
                <!-- Media Info Card -->
                <div class="media-card">
                    <div class="media-thumb-wrap">
                        <img id="mediaThumbnail" src="" alt="Thumbnail" class="media-thumb">
                        <div id="mediaDuration" class="media-duration" style="display:none"></div>
                        <div id="platformTag" class="platform-tag" style="display:none">
                            <i id="platformTagIcon" class=""></i><span id="platformTagName"></span>
                        </div>
                    </div>
                    <div class="media-info">
                        <h3 id="mediaTitle" class="media-title"></h3>
                        <div class="media-meta">
                            <span id="mediaAuthor" class="meta-item"><i class="fas fa-user"></i><span></span></span>
                            <span id="mediaViews"  class="meta-item"><i class="fas fa-eye"></i><span></span></span>
                            <span id="mediaLikes"  class="meta-item"><i class="fas fa-heart"></i><span></span></span>
                        </div>
                        <p id="mediaDesc" class="media-desc" style="display:none"></p>
                    </div>
                </div>

                <!-- Download Options -->
                <div class="dl-options">
                    <h4 class="dl-options-title"><i class="fas fa-download"></i> ជ្រើសរើសទម្រង់ទាញយក</h4>
                    <div class="dl-grid">
                        <button class="dl-btn dl-btn-video" id="dlVideo">
                            <div class="bl"><i class="fas fa-video"></i> Video</div>
                            <div class="br"><span class="dl-quality">Best Quality</span></div>
                        </button>
                        <button class="dl-btn dl-btn-audio" id="dlAudio">
                            <div class="bl"><i class="fas fa-music"></i> Audio</div>
                            <div class="br"><span class="dl-quality">MP3 192K</span></div>
                        </button>
                    </div>
                    <div id="formatListWrap" class="format-list-wrap" style="display:none">
                        <h5 class="format-list-title">ជ្រើសរើសគុណភាព</h5>
                        <div id="formatList" class="format-list"></div>
                    </div>
                </div>

                <!-- Download Progress -->
                <div id="dlProgressSection" class="progress-section" style="display:none">
                    <div class="progress-card">
                        <div class="progress-header">
                            <span id="progStatus" class="prog-status">Preparing…</span>
                            <span id="progPct" class="prog-pct">0%</span>
                        </div>
                        <div class="progress-bar-wrap">
                            <div id="progressBar" class="progress-bar" style="width:0%"></div>
                        </div>
                        <p id="progDetail" class="prog-detail"></p>
                    </div>
                </div>
            </section>
        </div>

        <!-- ===== TAB 2: Profile Grabber ===== -->
        <div id="tab-profile" class="tab-content">
            <section class="input-section">
                <div class="input-card">
                    <div class="input-wrapper">
                        <div class="input-icon"><i class="fas fa-user-circle"></i></div>
                        <input type="text" id="profileUrl" placeholder="បញ្ចូល URL គណនី (TikTok, Instagram, YouTube...)" autocomplete="off">
                        <button id="clearProfileBtn" class="icon-btn" style="display:none"><i class="fas fa-times"></i></button>
                    </div>
                    <button id="fetchProfileBtn" class="primary-btn"><i class="fas fa-user-circle"></i><span>ស្វែងរក Profile</span></button>
                </div>
            </section>
            <section id="profileLoading" class="state-section" style="display:none">
                <div class="state-card">
                    <div class="spinner"><div class="spinner-ring"></div><i class="fas fa-user spinner-icon"></i></div>
                    <p class="state-text">កំពុងទាញយក Profile...</p>
                </div>
            </section>
            <section id="profileError" class="state-section" style="display:none">
                <div class="state-card error">
                    <i class="fas fa-circle-exclamation state-icon error-icon"></i>
                    <p id="profileErrorText" class="state-text"></p>
                </div>
            </section>
            <section id="profileResult" style="display:none">
                <div class="pcard">
                    <div class="pcard-header">
                        <img id="pAvatar" src="" alt="Avatar" class="p-avatar">
                        <div class="pcard-info">
                            <h2 id="pName" class="p-name"></h2>
                            <p id="pUsername" class="p-username"></p>
                            <p id="pBio" class="p-bio"></p>
                            <div class="pstats">
                                <div class="pstat"><span id="pFollowers" class="pstat-val">0</span><span class="pstat-label">Followers</span></div>
                                <div class="pstat"><span id="pFollowing" class="pstat-val">0</span><span class="pstat-label">Following</span></div>
                                <div class="pstat"><span id="pVideos" class="pstat-val">0</span><span class="pstat-label">Videos</span></div>
                                <div class="pstat"><span id="pLikes" class="pstat-val">0</span><span class="pstat-label">Likes</span></div>
                            </div>
                            <button id="dlAvatarBtn" class="primary-btn" style="margin-top:1rem">
                                <i class="fas fa-download"></i><span>ទាញយក Avatar</span>
                            </button>
                        </div>
                    </div>
                </div>
            </section>
        </div>

        <!-- ===== TAB 3: Watermark Remover ===== -->
        <div id="tab-watermark" class="tab-content">
            <section class="input-section">
                <div class="input-card">
                    <div class="input-wrapper">
                        <div class="input-icon"><i class="fas fa-eraser"></i></div>
                        <input type="text" id="wmUrl" placeholder="បញ្ចូល TikTok / Douyin URL (Remove Watermark)" autocomplete="off">
                        <button id="clearWmBtn" class="icon-btn" style="display:none"><i class="fas fa-times"></i></button>
                    </div>
                    <button id="fetchWmBtn" class="primary-btn"><i class="fas fa-eraser"></i><span>លុប Watermark</span></button>
                </div>
            </section>
            <section id="wmLoading" class="state-section" style="display:none">
                <div class="state-card">
                    <div class="spinner"><div class="spinner-ring"></div><i class="fas fa-eraser spinner-icon"></i></div>
                    <p class="state-text">កំពុងលុប Watermark...</p>
                </div>
            </section>
            <section id="wmError" class="state-section" style="display:none">
                <div class="state-card error">
                    <i class="fas fa-circle-exclamation state-icon error-icon"></i>
                    <p id="wmErrorText" class="state-text"></p>
                </div>
            </section>
            <section id="wmResult" style="display:none">
                <div class="media-card">
                    <div class="media-thumb-wrap">
                        <img id="wmThumbnail" src="" alt="Thumbnail" class="media-thumb">
                    </div>
                    <div class="media-info">
                        <h3 id="wmTitle" class="media-title"></h3>
                        <div class="dl-grid" style="margin-top:1rem">
                            <button id="wmDownloadBtn" class="dl-btn dl-btn-video">
                                <div class="bl"><i class="fas fa-video"></i> ទាញយក (គ្មាន Watermark)</div>
                            </button>
                        </div>
                    </div>
                </div>
            </section>
        </div>

        <!-- ===== TAB 4: Sora2 Download ===== -->
        <div id="tab-sora2" class="tab-content">
            <section class="input-section">
                <div class="input-card">
                    <div class="input-wrapper">
                        <div class="input-icon"><i class="fas fa-wand-magic-sparkles"></i></div>
                        <input type="text" id="soraUrl" placeholder="បញ្ចូល Sora Video URL..." autocomplete="off">
                        <button id="clearSoraBtn" class="icon-btn" style="display:none"><i class="fas fa-times"></i></button>
                    </div>
                    <button id="fetchSoraBtn" class="primary-btn"><i class="fas fa-wand-magic-sparkles"></i><span>ទាញយក Sora</span></button>
                </div>
            </section>
            <section id="soraLoading" class="state-section" style="display:none">
                <div class="state-card">
                    <div class="spinner"><div class="spinner-ring"></div><i class="fas fa-wand-magic-sparkles spinner-icon"></i></div>
                    <p class="state-text">កំពុងទាញយក Sora...</p>
                </div>
            </section>
            <section id="soraError" class="state-section" style="display:none">
                <div class="state-card error">
                    <i class="fas fa-circle-exclamation state-icon error-icon"></i>
                    <p id="soraErrorText" class="state-text"></p>
                </div>
            </section>
            <section id="soraResult" style="display:none">
                <div class="media-card">
                    <div class="media-thumb-wrap">
                        <img id="soraThumbnail" src="" alt="Thumbnail" class="media-thumb">
                    </div>
                    <div class="media-info">
                        <h3 id="soraTitle" class="media-title"></h3>
                        <div class="dl-grid" style="margin-top:1rem" id="soraFormats"></div>
                    </div>
                </div>
            </section>
        </div>

        <!-- ===== TAB 5: Search ===== -->
        <div id="tab-search" class="tab-content">
            <section class="input-section">
                <div class="input-card">
                    <div class="input-wrapper">
                        <div class="input-icon"><i class="fas fa-search"></i></div>
                        <input type="text" id="searchQuery" placeholder="ស្វែងរកវីដេអូ YouTube..." autocomplete="off">
                        <button id="clearSearchBtn" class="icon-btn" style="display:none"><i class="fas fa-times"></i></button>
                    </div>
                    <div class="search-opts">
                        <select id="searchPlatform" class="search-select">
                            <option value="youtube">YouTube</option>
                            <option value="tiktok">TikTok</option>
                        </select>
                        <select id="searchCount" class="search-select">
                            <option value="5">5 results</option>
                            <option value="10" selected>10 results</option>
                            <option value="20">20 results</option>
                        </select>
                    </div>
                    <button id="searchBtn" class="primary-btn"><i class="fas fa-search"></i><span>ស្វែងរក</span></button>
                </div>
            </section>
            <section id="searchLoading" class="state-section" style="display:none">
                <div class="state-card">
                    <div class="spinner"><div class="spinner-ring"></div><i class="fas fa-search spinner-icon"></i></div>
                    <p class="state-text">កំពុងស្វែងរក...</p>
                </div>
            </section>
            <section id="searchError" class="state-section" style="display:none">
                <div class="state-card error">
                    <i class="fas fa-circle-exclamation state-icon error-icon"></i>
                    <p id="searchErrorText" class="state-text"></p>
                </div>
            </section>
            <section id="searchResults" style="display:none">
                <div id="searchList" class="search-list"></div>
            </section>
        </div>

        <!-- ===== Donate Modal ===== -->
        <div id="donateModal" class="modal-overlay" style="display:none">
            <div class="modal-box donate-modal">
                <button id="closeDonate" class="modal-close"><i class="fas fa-times"></i></button>

                <!-- Step 1: Amount Selection -->
                <div id="donateFormView">
                    <div class="donate-header">
                        <div class="donate-icon"><i class="fas fa-heart"></i></div>
                        <h3 class="donate-title">ជួយគាំទ្រ</h3>
                        <p class="donate-subtitle">ជ្រើសរើសចំនួនទឹកប្រាក់</p>
                    </div>
                    <div class="donate-body">
                        <div class="amount-grid" id="amountGrid">
                            <button class="amount-btn" data-amount="1">$1</button>
                            <button class="amount-btn active" data-amount="2">$2</button>
                            <button class="amount-btn" data-amount="5">$5</button>
                            <button class="amount-btn" data-amount="10">$10</button>
                            <button class="amount-btn" data-amount="20">$20</button>
                            <button class="amount-btn" data-amount="50">$50</button>
                        </div>
                        <div class="custom-amount-wrap">
                            <input type="number" id="customAmount" placeholder="ចំនួន Custom (USD)" min="0.5" step="0.5" class="custom-amount-input">
                        </div>
                        <button id="generateQRBtn" class="donate-submit">
                            <i class="fas fa-qrcode"></i> បង្កើត KHQR
                        </button>
                        <div class="donate-methods">
                            <span><i class="fas fa-shield-halved"></i> Secured by Bakong KHQR</span>
                        </div>
                    </div>
                </div>

                <!-- Step 2: QR Code Display -->
                <div id="donateQRView" style="display:none">
                    <div class="donate-body" style="padding-top:20px">
                        <div class="khqr-card">
                            <div class="khqr-header"><span>KHQR</span></div>
                            <div class="khqr-info">
                                <div class="khqr-name" id="khqrMerchant">SMMMEGA</div>
                                <div class="khqr-amount" id="khqrAmount">2 USD</div>
                            </div>
                            <div class="khqr-divider"></div>
                            <div class="khqr-qr-wrap">
                                <img id="khqrImage" src="" alt="KHQR Code">
                            </div>
                            <div class="khqr-scan-instruction" id="khqrScanMsg" style="display:none"></div>
                            <div class="khqr-countdown" id="khqrCountdown">ពេលវេលាដែលនៅសល់: 02:00</div>
                            <div class="khqr-status" id="khqrStatus">
                                <i class="fas fa-spinner fa-spin"></i> ស្ថានភាពបង់ប្រាក់: UNPAID
                            </div>
                        </div>
                        <button class="donate-submit khqr-new-btn" id="khqrNewPayment" style="display:none;margin-top:12px">
                            <i class="fas fa-redo"></i> បង់ប្រាក់ថ្មី
                        </button>
                        <div class="donate-methods" style="margin-top:12px">
                            <span><i class="fas fa-shield-halved"></i> Secured by Bakong KHQR</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Sound Effects -->
        <audio id="soundSuccess" src="/static/sound/success.mp3" preload="auto"></audio>
        <audio id="soundExpired" src="/static/sound/expired.mp3" preload="auto"></audio>

        <footer class="footer">
            <p>Powered by <a href="https://web.facebook.com/Mr.SOPHEARUN/" target="_blank" rel="noopener">RIN SOPHEARUN</a></p>
            <p>&copy; <?= date('Y') ?> Social Media Downloader — Multi-Platform</p>
        </footer>
    </div>

    <script src="/static/js/app.js"></script>
</body>
</html>
