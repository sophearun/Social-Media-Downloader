/**
 * Social Media Downloader — Multi-Platform
 * Frontend JavaScript
 */
(function () {
    'use strict';

    // ==================== Platform Config ====================
    const PLATFORM_INFO = {
        tiktok:      { name: 'TikTok',      icon: 'fab fa-tiktok',              color: '#fe2c55' },
        douyin:      { name: 'Douyin',       icon: 'fas fa-music',               color: '#00f0ff' },
        youtube:     { name: 'YouTube',      icon: 'fab fa-youtube',             color: '#ff0000' },
        instagram:   { name: 'Instagram',    icon: 'fab fa-instagram',           color: '#e4405f' },
        facebook:    { name: 'Facebook',     icon: 'fab fa-facebook',            color: '#1877f2' },
        twitter:     { name: 'X (Twitter)',  icon: 'fab fa-x-twitter',           color: '#aaa'    },
        pinterest:   { name: 'Pinterest',    icon: 'fab fa-pinterest',           color: '#bd081c' },
        kuaishou:    { name: 'Kuaishou',     icon: 'fas fa-video',               color: '#ff4906' },
        sora:        { name: 'Sora',         icon: 'fas fa-wand-magic-sparkles', color: '#a259ff' },
        xiaohongshu: { name: '小红书',        icon: 'fas fa-book',                color: '#ff2442' },
        threads:     { name: 'Threads',      icon: 'fab fa-threads',             color: '#000'    },
        linkedin:    { name: 'LinkedIn',     icon: 'fab fa-linkedin',            color: '#0077b5' },
        reddit:      { name: 'Reddit',       icon: 'fab fa-reddit',              color: '#ff4500' },
        bilibili:    { name: 'Bilibili',     icon: 'fab fa-bilibili',            color: '#00a1d6' },
        weibo:       { name: 'Weibo',        icon: 'fab fa-weibo',               color: '#e6162d' },
        lemon8:      { name: 'Lemon8',       icon: 'fas fa-lemon',               color: '#a8e600' },
        zhihu:       { name: 'Zhihu',        icon: 'fas fa-z',                   color: '#0084ff' },
        wechat:      { name: 'WeChat',       icon: 'fab fa-weixin',              color: '#07c160' },
        pipixia:     { name: 'Pipixia',      icon: 'fas fa-shrimp',              color: '#ff6699' },
    };

    function detectPlatform(url) {
        url = (url || '').toLowerCase();
        if (url.includes('tiktok.com'))    return 'tiktok';
        if (url.includes('douyin.com'))    return 'douyin';
        if (url.includes('youtube.com') || url.includes('youtu.be')) return 'youtube';
        if (url.includes('instagram.com')) return 'instagram';
        if (url.includes('facebook.com') || url.includes('fb.watch') || url.includes('fb.com')) return 'facebook';
        if (url.includes('twitter.com') || url.includes('x.com')) return 'twitter';
        if (url.includes('pinterest.com') || url.includes('pin.it')) return 'pinterest';
        if (url.includes('kuaishou.com') || url.includes('kwai.com')) return 'kuaishou';
        if (url.includes('sora') && url.includes('openai.com')) return 'sora';
        if (url.includes('sora.com')) return 'sora';
        if (url.includes('sora.chatgpt.com') || (url.includes('chatgpt.com') && url.includes('/p/s_'))) return 'sora';
        if (url.includes('xiaohongshu.com') || url.includes('xhslink.com')) return 'xiaohongshu';
        if (url.includes('threads.net'))   return 'threads';
        if (url.includes('linkedin.com'))  return 'linkedin';
        if (url.includes('reddit.com') || url.includes('redd.it')) return 'reddit';
        if (url.includes('bilibili.com') || url.includes('b23.tv')) return 'bilibili';
        if (url.includes('weibo.com') || url.includes('weibo.cn')) return 'weibo';
        if (url.includes('lemon8'))        return 'lemon8';
        if (url.includes('zhihu.com'))     return 'zhihu';
        if (url.includes('weixin.qq.com') || url.includes('mp.weixin')) return 'wechat';
        if (url.includes('pipix.com') || url.includes('pipixia')) return 'pipixia';
        return null;
    }

    // ==================== DOM References ====================
    const $ = id => document.getElementById(id);
    const show = el => { if (el) el.style.display = ''; };
    const hide = el => { if (el) el.style.display = 'none'; };

    // Safe JSON fetch helper — prevents "Unexpected token '<'" errors
    async function safeFetchJSON(url, opts) {
        const r = await fetch(url, opts);
        const ct = r.headers.get('content-type') || '';
        if (!ct.includes('application/json')) {
            const text = await r.text();
            throw new Error(`Server error (${r.status}). សូមពិនិត្យ server log.`);
        }
        const d = await r.json();
        if (!r.ok && d.error) throw new Error(d.error);
        return d;
    }

    // Tabs
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    // Single Download
    const urlInput = $('urlInput'), pasteBtn = $('pasteBtn'), clearBtn = $('clearBtn'), fetchBtn = $('fetchBtn');
    const platformBadge = $('platformBadge'), platformBadgeIcon = $('platformBadgeIcon'), platformBadgeName = $('platformBadgeName');
    const loadingSection = $('loadingSection'), errorSection = $('errorSection'), errorMessage = $('errorMessage'), retryBtn = $('retryBtn');
    const videoSection = $('videoSection'), videoThumbnail = $('videoThumbnail'), videoTitle = $('videoTitle');
    const videoAuthor = $('videoAuthor'), videoViews = $('videoViews'), videoLikes = $('videoLikes'), videoComments = $('videoComments');
    const videoDuration = $('videoDuration'), videoPlatformBadge = $('videoPlatformBadge');
    const dlVideoBtn = $('dlVideoBtn'), dlAudioBtn = $('dlAudioBtn'), getCommentsBtn = $('getCommentsBtn');
    const commentsSection = $('commentsSection'), commentCount = $('commentCount'), commentsList = $('commentsList'), closeCommentsBtn = $('closeCommentsBtn');
    const progressSection = $('progressSection'), progressBar = $('progressBar'), progressPercent = $('progressPercent'), progressStatus = $('progressStatus');
    const completeSection = $('completeSection'), downloadLink = $('downloadLink'), newDownloadBtn = $('newDownloadBtn');

    // Profile Grabber
    const profileUrlInput = $('profileUrlInput'), profilePasteBtn = $('profilePasteBtn'), profileClearBtn = $('profileClearBtn');
    const grabBtn = $('grabBtn'), maxVideosSelect = $('maxVideosSelect');
    const profileLoadingSection = $('profileLoadingSection'), profileLoadingText = $('profileLoadingText'), profileLoadingCount = $('profileLoadingCount');
    const profileErrorSection = $('profileErrorSection'), profileErrorMessage = $('profileErrorMessage'), profileRetryBtn = $('profileRetryBtn');
    const profileResultSection = $('profileResultSection');
    const profileAvatar = $('profileAvatar'), profileNickname = $('profileNickname'), profileUsername = $('profileUsername'), profileSignature = $('profileSignature');
    const statVideos = $('statVideos'), statFollowers = $('statFollowers'), statFollowing = $('statFollowing'), statLikes = $('statLikes');
    const toggleAnalyticsBtn = $('toggleAnalyticsBtn'), analyticsPanel = $('analyticsPanel');
    const sortSelect = $('sortSelect'), filterMinLikes = $('filterMinLikes'), filterMaxLikes = $('filterMaxLikes'), applyFilterBtn = $('applyFilterBtn');
    const videoCountLabel = $('videoCountLabel'), selectAllBtn = $('selectAllBtn');
    const downloadSelectedBtn = $('downloadSelectedBtn'), selectedCount = $('selectedCount');
    const videoGrid = $('videoGrid');
    const batchProgressSection = $('batchProgressSection'), batchBar = $('batchBar'), batchPercent = $('batchPercent');
    const batchTitle = $('batchTitle'), batchStatus = $('batchStatus');
    const batchOK = $('batchOK'), batchFail = $('batchFail'), batchTot = $('batchTot');

    // Search
    const searchInput = $('searchInput'), searchBtn = $('searchBtn');
    const searchLoadingSection = $('searchLoadingSection'), searchResultSection = $('searchResultSection');
    const searchCountLabel = $('searchCountLabel'), searchGrid = $('searchGrid');
    const searchCountSelect = $('searchCountSelect');
    const searchLoadMoreWrap = $('searchLoadMore'), searchLoadMoreBtn = $('searchLoadMoreBtn');

    // State
    let currentVideoInfo = null;
    let profileVideos = []; // original data
    let searchAllResults = []; // all search results
    let searchPageSize = 20; // items per page
    let searchShown = 0; // how many currently shown
    let displayedVideos = []; // after sort/filter
    let selectedSet = new Set();
    let allSelected = false;
    let pollTimer = null, profilePollTimer = null;

    // ==================== Utility ====================
    function fmtNum(n) {
        n = parseInt(n) || 0;
        if (n >= 1e6) return (n/1e6).toFixed(1) + 'M';
        if (n >= 1e3) return (n/1e3).toFixed(1) + 'K';
        return n.toString();
    }
    function fmtDur(s) {
        if (!s) return '';
        s = parseInt(s);
        const m = Math.floor(s/60), sec = s%60;
        return m + ':' + sec.toString().padStart(2,'0');
    }
    function fmtSpeed(b) {
        if (!b) return '';
        if (b >= 1048576) return (b/1048576).toFixed(1)+' MB/s';
        if (b >= 1024) return (b/1024).toFixed(1)+' KB/s';
        return b+' B/s';
    }
    function esc(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

    const placeholderThumb = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 90 160'%3E%3Crect fill='%23111' width='90' height='160'/%3E%3Ctext x='45' y='85' text-anchor='middle' fill='%23333' font-size='20'%3E▶%3C/text%3E%3C/svg%3E";

    // ==================== Tab Navigation ====================
    tabBtns.forEach(btn => btn.addEventListener('click', () => {
        tabBtns.forEach(b => b.classList.remove('active'));
        tabContents.forEach(c => c.classList.remove('active'));
        btn.classList.add('active');
        $('tab-' + btn.dataset.tab).classList.add('active');
    }));

    // Feature tabs
    document.querySelectorAll('.feat-tab').forEach(btn => btn.addEventListener('click', () => {
        document.querySelectorAll('.feat-tab').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.feat-content').forEach(c => c.classList.remove('active'));
        btn.classList.add('active');
        $('feat-' + btn.dataset.feat).classList.add('active');
    }));

    // ==================== Single Download ====================
    urlInput.addEventListener('input', () => {
        clearBtn.style.display = urlInput.value ? '' : 'none';
        const p = detectPlatform(urlInput.value);
        if (p) {
            const pi = PLATFORM_INFO[p];
            platformBadgeIcon.className = pi.icon;
            platformBadgeName.textContent = pi.name;
            platformBadge.style.display = '';
            platformBadge.style.color = pi.color;
            platformBadge.style.borderColor = pi.color + '33';
            platformBadge.style.background = pi.color + '12';
        } else { hide(platformBadge); }
    });

    pasteBtn.addEventListener('click', async () => {
        try { urlInput.value = await navigator.clipboard.readText(); urlInput.dispatchEvent(new Event('input')); } catch(e) {}
    });
    clearBtn.addEventListener('click', () => { urlInput.value = ''; urlInput.dispatchEvent(new Event('input')); resetSingle(); });
    fetchBtn.addEventListener('click', fetchInfo);
    retryBtn.addEventListener('click', fetchInfo);
    newDownloadBtn.addEventListener('click', () => { urlInput.value = ''; urlInput.dispatchEvent(new Event('input')); resetSingle(); });
    urlInput.addEventListener('keydown', e => { if (e.key === 'Enter') fetchInfo(); });

    urlInput.addEventListener('focus', async () => {
        if (urlInput.value) return;
        try {
            const t = await navigator.clipboard.readText();
            if (t && detectPlatform(t)) { urlInput.value = t; urlInput.dispatchEvent(new Event('input')); }
        } catch(e) {}
    });

    function resetSingle() {
        [loadingSection, errorSection, videoSection, progressSection, completeSection, commentsSection].forEach(hide);
        dlVideoBtn.disabled = false; dlAudioBtn.disabled = false;
    }

    async function fetchInfo() {
        const url = urlInput.value.trim();
        if (!url) { urlInput.focus(); return; }
        resetSingle(); show(loadingSection); fetchBtn.disabled = true;
        try {
            const d = await safeFetchJSON('/api/info', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({url}) });
            currentVideoInfo = d;
            videoThumbnail.src = d.thumbnail || '';
            videoTitle.textContent = d.title || 'Video';
            videoAuthor.textContent = d.author || 'Unknown';
            videoViews.textContent = fmtNum(d.view_count);
            videoLikes.textContent = fmtNum(d.like_count);
            videoComments.textContent = fmtNum(d.comment_count);
            videoDuration.textContent = fmtDur(d.duration);
            const pi = PLATFORM_INFO[d.platform] || {};
            videoPlatformBadge.innerHTML = `<i class="${pi.icon || 'fas fa-globe'}"></i> ${pi.name || ''}`;
            videoPlatformBadge.style.color = pi.color || '#fff';
            hide(loadingSection); show(videoSection);
        } catch(e) {
            hide(loadingSection); errorMessage.textContent = e.message; show(errorSection);
        } finally { fetchBtn.disabled = false; }
    }

    dlVideoBtn.addEventListener('click', () => startDL('video'));
    dlAudioBtn.addEventListener('click', () => startDL('audio'));

    // FFmpeg status check on page load
    (async function checkFFmpeg() {
        try {
            const r = await fetch('/api/ffmpeg/status');
            const d = await r.json();
            const el = document.getElementById('ffmpegStatus');
            if (el) {
                if (d.available) {
                    el.innerHTML = '<i class="fas fa-circle online"></i> FFmpeg ' + (d.version || '') + ' ready';
                } else {
                    el.innerHTML = '<i class="fas fa-circle offline"></i> FFmpeg not available';
                }
            }
        } catch(e) {}
    })();

    async function startDL(fmt) {
        if (!currentVideoInfo) return;
        dlVideoBtn.disabled = true; dlAudioBtn.disabled = true;
        hide(videoSection); hide(commentsSection); show(progressSection);
        progressBar.style.width = '0%'; progressPercent.textContent = '0%';
        progressStatus.textContent = 'កំពុងចាប់ផ្តើម...';
        try {
            const qualitySel = document.getElementById('qualitySelect');
            const formatSel = document.getElementById('formatSelect');
            const body = {url: currentVideoInfo.url, format: fmt};
            if (qualitySel && qualitySel.value) body.quality = qualitySel.value;
            if (formatSel && formatSel.value) body.output_format = formatSel.value;
            const d = await safeFetchJSON('/api/download', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body) });
            if (d.task_id) pollDL(d.task_id);
        } catch(e) { hide(progressSection); errorMessage.textContent = e.message||'Download error'; show(errorSection); }
    }

    function pollDL(tid) {
        if (pollTimer) clearInterval(pollTimer);
        pollTimer = setInterval(async () => {
            try {
                const r = await fetch(`/api/progress/${tid}`);
                const d = await r.json();
                if (d.status === 'downloading') {
                    progressBar.style.width = (d.percent||0)+'%'; progressPercent.textContent = (d.percent||0)+'%';
                    progressStatus.textContent = `${fmtSpeed(d.speed)} ${d.eta? '• '+d.eta+'s':''}`;
                } else if (d.status === 'processing') {
                    progressBar.style.width = '100%'; progressPercent.textContent = '100%'; progressStatus.textContent = 'កំពុងបំលែង...';
                } else if (d.status === 'completed') {
                    clearInterval(pollTimer); hide(progressSection);
                    downloadLink.href = `/api/file/${d.filename}`; downloadLink.download = d.filename; show(completeSection);
                } else if (d.status === 'error') {
                    clearInterval(pollTimer); hide(progressSection);
                    errorMessage.textContent = d.error || 'Download failed'; show(errorSection);
                }
            } catch(e) {}
        }, 800);
    }

    // ==================== Comments ====================
    getCommentsBtn.addEventListener('click', async () => {
        if (!currentVideoInfo) return;
        getCommentsBtn.disabled = true; getCommentsBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';
        try {
            const d = await safeFetchJSON('/api/comments', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({url: currentVideoInfo.url}) });
            commentCount.textContent = d.total || 0;
            commentsList.innerHTML = '';
            if (d.comments && d.comments.length > 0) {
                d.comments.forEach(c => {
                    const el = document.createElement('div'); el.className = 'comment-item';
                    el.innerHTML = `<img class="comment-avatar" src="${esc(c.author_thumbnail||'')}" onerror="this.style.display='none'" alt="">
                        <div class="comment-body"><div class="comment-author">${esc(c.author)}</div><div class="comment-text">${esc(c.text)}</div>
                        ${c.likes ? `<div class="comment-likes"><i class="fas fa-heart"></i>${fmtNum(c.likes)}</div>` : ''}</div>`;
                    commentsList.appendChild(el);
                });
            } else {
                commentsList.innerHTML = '<p style="text-align:center;color:#666;padding:20px;">មិនមាន comments ឬមិនអាចទាញយកបាន</p>';
            }
            show(commentsSection);
        } catch(e) {
            commentsList.innerHTML = '<p style="text-align:center;color:#f66;padding:20px;">Error loading comments</p>';
            show(commentsSection);
        } finally {
            getCommentsBtn.disabled = false; getCommentsBtn.innerHTML = '<i class="fas fa-comments"></i> Comments Scraping';
        }
    });
    closeCommentsBtn.addEventListener('click', () => hide(commentsSection));

    // ==================== Profile Grabber ====================
    // Platform selector
    $('profilePlatformBadges').addEventListener('click', e => {
        const btn = e.target.closest('.ps-badge');
        if (!btn) return;
        // Platform badges just visual — platform auto-detected from URL
        $('profilePlatformBadges').querySelectorAll('.ps-badge').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
    });

    profileUrlInput.addEventListener('input', () => {
        profileClearBtn.style.display = profileUrlInput.value ? '' : 'none';
        // Auto-select platform badge
        const p = detectPlatform(profileUrlInput.value);
        if (p) {
            $('profilePlatformBadges').querySelectorAll('.ps-badge').forEach(b => {
                b.classList.toggle('active', b.dataset.plat === p);
            });
        }
        // Show/hide Facebook cookie helper
        toggleFbCookieHelper(p);
    });
    profilePasteBtn.addEventListener('click', async () => {
        try { profileUrlInput.value = await navigator.clipboard.readText(); profileUrlInput.dispatchEvent(new Event('input')); } catch(e) {}
    });
    profileClearBtn.addEventListener('click', () => { profileUrlInput.value = ''; profileUrlInput.dispatchEvent(new Event('input')); resetProfile(); });
    grabBtn.addEventListener('click', startGrab);
    profileRetryBtn.addEventListener('click', startGrab);
    profileUrlInput.addEventListener('keydown', e => { if (e.key === 'Enter') startGrab(); });

    profileUrlInput.addEventListener('focus', async () => {
        if (profileUrlInput.value) return;
        try {
            const t = await navigator.clipboard.readText();
            if (t && detectPlatform(t)) { profileUrlInput.value = t; profileUrlInput.dispatchEvent(new Event('input')); }
        } catch(e) {}
    });

    function resetProfile() {
        [profileLoadingSection, profileErrorSection, profileResultSection, batchProgressSection, analyticsPanel].forEach(hide);
        profileVideos = []; displayedVideos = []; selectedSet.clear(); allSelected = false;
        videoGrid.innerHTML = '';
    }

    async function startGrab() {
        const url = profileUrlInput.value.trim();
        if (!url) { profileUrlInput.focus(); return; }
        resetProfile(); show(profileLoadingSection);
        profileLoadingText.textContent = 'កំពុងស្វែងរក Profile...'; hide(profileLoadingCount);
        grabBtn.disabled = true;
        try {
            const d = await safeFetchJSON('/api/profile/grab', { method:'POST', headers:{'Content-Type':'application/json'},
                body: JSON.stringify({ url, max_videos: parseInt(maxVideosSelect.value)||0 }) });
            if (d.task_id) pollProfile(d.task_id);
        } catch(e) {
            hide(profileLoadingSection); profileErrorMessage.innerHTML = esc(e.message||'Error').replace(/\n/g,'<br>'); show(profileErrorSection); grabBtn.disabled = false;
        }
    }

    function pollProfile(tid) {
        if (profilePollTimer) clearInterval(profilePollTimer);
        profilePollTimer = setInterval(async () => {
            try {
                const r = await fetch(`/api/profile/status/${tid}`);
                const d = await r.json();
                if (['starting','getting_profile','grabbing'].includes(d.status)) {
                    profileLoadingText.textContent = d.message || 'កំពុងស្វែងរក...';
                    if (d.total > 0) { profileLoadingCount.textContent = `${d.total} posts`; show(profileLoadingCount); }
                    if (d.profile && d.status === 'grabbing') showProfileInfo(d.profile);
                } else if (d.status === 'completed') {
                    clearInterval(profilePollTimer); hide(profileLoadingSection); grabBtn.disabled = false;
                    if (d.profile) showProfileInfo(d.profile);
                    profileVideos = d.videos || [];
                    displayedVideos = [...profileVideos];
                    renderGrid(displayedVideos); computeAnalytics(profileVideos);
                    show(profileResultSection);
                } else if (d.status === 'error') {
                    clearInterval(profilePollTimer); hide(profileLoadingSection);
                    profileErrorMessage.innerHTML = esc(d.message || 'Error').replace(/\n/g,'<br>'); show(profileErrorSection); grabBtn.disabled = false;
                }
            } catch(e) {}
        }, 1200);
    }

    function showProfileInfo(info) {
        if (!info) return;
        profileAvatar.src = info.avatar || '';
        profileAvatar.onerror = function(){ this.style.display='none'; };
        profileNickname.textContent = info.nickname || 'Unknown';
        profileUsername.textContent = '@' + (info.username || 'unknown');
        profileSignature.textContent = info.signature || '';
        statVideos.textContent = fmtNum(info.video_count);
        statFollowers.textContent = fmtNum(info.followers);
        statFollowing.textContent = fmtNum(info.following);
        statLikes.textContent = fmtNum(info.likes);
    }

    // ==================== Analytics ====================
    toggleAnalyticsBtn.addEventListener('click', () => {
        analyticsPanel.style.display = analyticsPanel.style.display === 'none' ? '' : 'none';
    });

    function computeAnalytics(videos) {
        if (!videos.length) return;
        const n = videos.length;
        const totalViews = videos.reduce((s,v) => s + (v.view_count||0), 0);
        const totalLikes = videos.reduce((s,v) => s + (v.like_count||0), 0);
        const totalComments = videos.reduce((s,v) => s + (v.comment_count||0), 0);
        const topViews = Math.max(...videos.map(v => v.view_count||0));
        const topLikes = Math.max(...videos.map(v => v.like_count||0));
        const engRate = totalViews > 0 ? ((totalLikes + totalComments) / totalViews * 100).toFixed(2) : 0;

        $('anaAvgViews').textContent = fmtNum(Math.round(totalViews/n));
        $('anaAvgLikes').textContent = fmtNum(Math.round(totalLikes/n));
        $('anaAvgComments').textContent = fmtNum(Math.round(totalComments/n));
        $('anaEngRate').textContent = engRate + '%';
        $('anaTopViews').textContent = fmtNum(topViews);
        $('anaTopLikes').textContent = fmtNum(topLikes);
    }

    // ==================== Sort & Filter ====================
    sortSelect.addEventListener('change', applySortFilter);
    applyFilterBtn.addEventListener('click', applySortFilter);

    function applySortFilter() {
        let vids = [...profileVideos];

        // Filter
        const minL = parseInt(filterMinLikes.value) || 0;
        const maxL = parseInt(filterMaxLikes.value) || 0;
        if (minL > 0) vids = vids.filter(v => (v.like_count||0) >= minL);
        if (maxL > 0) vids = vids.filter(v => (v.like_count||0) <= maxL);

        // Sort
        const sort = sortSelect.value;
        const sorters = {
            'likes_desc':      (a,b) => (b.like_count||0) - (a.like_count||0),
            'likes_asc':       (a,b) => (a.like_count||0) - (b.like_count||0),
            'views_desc':      (a,b) => (b.view_count||0) - (a.view_count||0),
            'views_asc':       (a,b) => (a.view_count||0) - (b.view_count||0),
            'comments_desc':   (a,b) => (b.comment_count||0) - (a.comment_count||0),
            'date_desc':       (a,b) => (b.create_time||0) - (a.create_time||0),
            'date_asc':        (a,b) => (a.create_time||0) - (b.create_time||0),
            'engagement_desc': (a,b) => ((b.like_count||0)+(b.comment_count||0)+(b.share_count||0)) - ((a.like_count||0)+(a.comment_count||0)+(a.share_count||0)),
        };
        if (sorters[sort]) vids.sort(sorters[sort]);

        displayedVideos = vids;
        selectedSet.clear(); allSelected = false;
        renderGrid(displayedVideos);
    }

    // ==================== Video Grid ====================
    function renderGrid(videos) {
        videoGrid.innerHTML = '';
        selectedSet.clear(); allSelected = false; updateSelCount();
        videoCountLabel.textContent = `${videos.length} posts`;

        if (!videos.length) {
            videoGrid.innerHTML = '<div style="text-align:center;padding:40px;color:#555;grid-column:1/-1;"><i class="fas fa-inbox" style="font-size:36px;margin-bottom:8px;display:block;"></i>រកមិនឃើញវីដេអូ</div>';
            return;
        }
        videos.forEach((v, i) => videoGrid.appendChild(createGridItem(v, i)));
    }

    function createGridItem(video, idx) {
        const el = document.createElement('div');
        el.className = 'vg-item';
        el.dataset.idx = idx;
        const pi = PLATFORM_INFO[video.platform] || {};
        const thumb = video.thumbnail || placeholderThumb;
        const isPhoto = video.type === 'photo';
        const typeIcon = isPhoto ? 'fas fa-image' : (video.type === 'reel' ? 'fas fa-film' : 'fas fa-video');
        const typeLabel = isPhoto ? 'Photo' : (video.type === 'reel' ? 'Reel' : 'Video');
        const typeColor = isPhoto ? '#00b894' : (video.type === 'reel' ? '#e17055' : pi.color || '#fff');

        el.innerHTML = `
            <div class="item-check"><i class="fas fa-check"></i></div>
            <span class="item-plat" style="color:${pi.color||'#fff'}"><i class="${pi.icon||'fas fa-globe'}"></i></span>
            <span class="item-type" style="background:${typeColor}"><i class="${typeIcon}"></i> ${typeLabel}</span>
            <img class="item-thumb" src="${esc(thumb)}" alt="" loading="lazy" onerror="this.src='${placeholderThumb}'" style="${isPhoto ? 'aspect-ratio:auto;max-height:280px;' : ''}">
            <button class="item-translate" title="Translate" onclick="event.stopPropagation();window.open('https://translate.google.com/?sl=auto&tl=en&text='+encodeURIComponent(this.dataset.text),'_blank')" data-text="${esc(video.title||'')}"><i class="fas fa-language"></i></button>
            <div class="item-body">
                <div class="item-title">${esc(video.title||'Post')}</div>
                <div class="item-stats">
                    ${video.view_count ? `<span><i class="fas fa-eye"></i>${fmtNum(video.view_count)}</span>` : ''}
                    ${video.like_count ? `<span><i class="fas fa-heart"></i>${fmtNum(video.like_count)}</span>` : ''}
                    ${video.comment_count ? `<span><i class="fas fa-comment"></i>${fmtNum(video.comment_count)}</span>` : ''}
                    ${video.duration ? `<span><i class="fas fa-clock"></i>${fmtDur(video.duration)}</span>` : ''}
                    ${isPhoto && video.width ? `<span><i class="fas fa-expand"></i>${video.width}x${video.height}</span>` : ''}
                </div>
            </div>
            <button class="item-dl" data-idx="${idx}"><i class="fas fa-download"></i> ${isPhoto ? 'ទាញយករូបភាព' : 'ទាញយក'}</button>`;

        el.addEventListener('click', e => {
            if (e.target.closest('.item-dl') || e.target.closest('.item-translate')) return;
            toggleSel(idx, el);
        });

        el.querySelector('.item-dl').addEventListener('click', e => {
            e.stopPropagation();
            dlSingleProfile(video, el.querySelector('.item-dl'));
        });

        return el;
    }

    function toggleSel(idx, el) {
        if (selectedSet.has(idx)) { selectedSet.delete(idx); el.classList.remove('selected'); }
        else { selectedSet.add(idx); el.classList.add('selected'); }
        updateSelCount();
    }

    function updateSelCount() {
        selectedCount.textContent = selectedSet.size;
        downloadSelectedBtn.disabled = selectedSet.size === 0;
    }

    selectAllBtn.addEventListener('click', () => {
        const items = videoGrid.querySelectorAll('.vg-item');
        allSelected = !allSelected;
        items.forEach((el, i) => {
            if (allSelected) { selectedSet.add(i); el.classList.add('selected'); }
            else { selectedSet.delete(i); el.classList.remove('selected'); }
        });
        selectAllBtn.innerHTML = allSelected ? '<i class="fas fa-times"></i> មិនជ្រើស' : '<i class="fas fa-check-double"></i> ជ្រើសរើស';
        updateSelCount();
    });

    // ==================== Profile: Single Download ====================
    async function dlSingleProfile(video, btn) {
        if (!video.url) return;
        btn.disabled = true; btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        try {
            const r = await fetch('/api/profile/download', { method:'POST', headers:{'Content-Type':'application/json'},
                body: JSON.stringify({url: video.url, video_id: video.id, type: video.type||'video', source: video.source||''}) });
            const d = await r.json();
            if (d.task_id) pollItemDL(d.task_id, btn);
        } catch(e) {
            btn.disabled = false; btn.innerHTML = '<i class="fas fa-times"></i> Error';
            setTimeout(() => { btn.innerHTML = '<i class="fas fa-download"></i> ទាញយក'; }, 2000);
        }
    }

    function pollItemDL(tid, btn) {
        const t = setInterval(async () => {
            try {
                const r = await fetch(`/api/progress/${tid}`);
                const d = await r.json();
                if (d.status === 'downloading') { btn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> ${d.percent||0}%`; }
                else if (d.status === 'completed') {
                    clearInterval(t); btn.classList.add('done'); btn.innerHTML = '<i class="fas fa-check"></i> Done';
                    const a = document.createElement('a'); a.href = `/api/file/${d.filename}`; a.download = d.filename;
                    document.body.appendChild(a); a.click(); document.body.removeChild(a);
                } else if (d.status === 'error') {
                    clearInterval(t); btn.disabled = false; btn.innerHTML = '<i class="fas fa-times"></i> Error';
                    setTimeout(() => { btn.innerHTML = '<i class="fas fa-download"></i> ទាញយក'; btn.classList.remove('done'); }, 3000);
                }
            } catch(e) {}
        }, 1000);
    }

    // ==================== Profile: Batch Download ====================
    downloadSelectedBtn.addEventListener('click', startBatch);

    async function startBatch() {
        if (selectedSet.size === 0) return;
        const videos = Array.from(selectedSet).map(i => displayedVideos[i]).filter(v => v && v.url);
        if (!videos.length) return;

        show(batchProgressSection); downloadSelectedBtn.disabled = true;
        batchBar.style.width = '0%'; batchPercent.textContent = '0%';
        batchTitle.textContent = `កំពុងទាញយក ${videos.length} posts...`;
        batchStatus.textContent = 'កំពុងចាប់ផ្តើម...';
        batchOK.textContent = '0'; batchFail.textContent = '0'; batchTot.textContent = videos.length;

        try {
            const r = await fetch('/api/profile/download-all', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({videos}) });
            const d = await r.json();
            if (d.task_id) pollBatch(d.task_id);
        } catch(e) { batchTitle.textContent = 'Error'; downloadSelectedBtn.disabled = false; }
    }

    function pollBatch(tid) {
        const t = setInterval(async () => {
            try {
                const r = await fetch(`/api/progress/${tid}`);
                const d = await r.json();
                batchBar.style.width = (d.percent||0)+'%'; batchPercent.textContent = Math.round(d.percent||0)+'%';
                batchOK.textContent = d.completed||0; batchFail.textContent = d.failed||0;
                if (d.status === 'batch_starting' || !d.status || d.status === 'downloading') {
                    batchStatus.textContent = d.current || 'កំពុងទាញយក...';
                } else if (d.status === 'batch_completed') {
                    clearInterval(t); batchBar.style.width = '100%'; batchPercent.textContent = '100%';
                    batchTitle.textContent = 'ទាញយករួចរាល់!';
                    batchStatus.textContent = `${d.completed||0}/${d.total||0} posts`;
                    downloadSelectedBtn.disabled = false;
                    if (d.files && d.files.length) {
                        d.files.forEach((f, i) => setTimeout(() => {
                            const a = document.createElement('a'); a.href = `/api/file/${f}`; a.download = f;
                            document.body.appendChild(a); a.click(); document.body.removeChild(a);
                        }, i*500));
                    }
                }
            } catch(e) {}
        }, 1500);
    }

    // ==================== Search ====================
    searchBtn.addEventListener('click', doSearch);
    searchInput.addEventListener('keydown', e => { if (e.key === 'Enter') doSearch(); });

    // Search platform badge click
    const searchPlatBadges = $('searchPlatformBadges');
    if (searchPlatBadges) {
        searchPlatBadges.addEventListener('click', e => {
            const badge = e.target.closest('.ps-badge');
            if (!badge) return;
            searchPlatBadges.querySelectorAll('.ps-badge').forEach(b => b.classList.remove('active'));
            badge.classList.add('active');
            // Update placeholder based on platform
            const plat = badge.dataset.plat;
            const placeholders = {
                youtube: 'ស្វែងរកពាក្យគន្លឹះ / Hashtag / Keyword Explore...',
                tiktok: 'ស្វែងរក TikTok Videos, Hashtag...',
                facebook: 'ស្វែងរក Facebook Pages, Videos...',
                twitter: 'ស្វែងរក X/Twitter Videos, Keywords...',
                pinterest: 'ស្វែងរក Pinterest Pins, Keywords...'
            };
            searchInput.placeholder = placeholders[plat] || placeholders.youtube;
        });
    }

    // Search type selector
    const searchTypeBtns = document.querySelectorAll('.search-type-btn');
    searchTypeBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            searchTypeBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        });
    });

    async function doSearch() {
        const q = searchInput.value.trim();
        if (!q) { searchInput.focus(); return; }
        hide(searchResultSection); show(searchLoadingSection); searchBtn.disabled = true;
        if (searchLoadMoreWrap) hide(searchLoadMoreWrap);

        // Determine search platform
        let searchPlat = 'youtube';
        const activeSearchBadge = $('searchPlatformBadges').querySelector('.ps-badge.active');
        if (activeSearchBadge) searchPlat = activeSearchBadge.dataset.plat;

        // Determine search type
        let searchType = 'keyword';
        const activeTypeBtn = document.querySelector('.search-type-btn.active');
        if (activeTypeBtn) searchType = activeTypeBtn.dataset.stype;

        // Get count
        const searchCount = searchCountSelect ? parseInt(searchCountSelect.value) || 0 : 20;
        searchPageSize = (searchCount > 0 && searchCount <= 50) ? searchCount : 20;

        try {
            const r = await fetch('/api/search', { method:'POST', headers:{'Content-Type':'application/json'},
                body: JSON.stringify({ query: q, platform: searchPlat, count: searchCount, search_type: searchType }) });
            
            // Handle non-JSON responses
            const contentType = r.headers.get('content-type') || '';
            if (!contentType.includes('application/json')) {
                throw new Error(`Server error (${r.status}). សូមព្យាយាមម្តងទៀត`);
            }
            const d = await r.json();
            if (d.error && !d.results) {
                throw new Error(d.error);
            }
            hide(searchLoadingSection); searchBtn.disabled = false;
            searchCountLabel.textContent = `${d.total||0} results (${searchPlat})`;
            searchGrid.innerHTML = '';
            searchAllResults = d.results || [];
            searchShown = 0;
            if (searchAllResults.length) {
                showMoreSearchResults();
            } else {
                searchGrid.innerHTML = '<div style="text-align:center;padding:40px;color:#555;grid-column:1/-1;"><i class="fas fa-search" style="font-size:2em;margin-bottom:10px;display:block;opacity:.4"></i>រកមិនឃើញលទ្ធផល</div>';
            }
            show(searchResultSection);
        } catch(e) {
            hide(searchLoadingSection); searchBtn.disabled = false;
            searchGrid.innerHTML = `<div style="text-align:center;padding:40px;color:#f66;grid-column:1/-1;">${esc(e.message||'Error')}</div>`;
            show(searchResultSection);
        }
    }

    function showMoreSearchResults() {
        const end = Math.min(searchShown + searchPageSize, searchAllResults.length);
        for (let i = searchShown; i < end; i++) {
            const el = createGridItem(searchAllResults[i], i);
            searchGrid.appendChild(el);
        }
        searchShown = end;
        // Show/hide load more button
        if (searchLoadMoreWrap) {
            if (searchShown < searchAllResults.length) {
                show(searchLoadMoreWrap);
                searchLoadMoreBtn.innerHTML = `<i class="fas fa-chevron-down"></i> មើលបន្ត... (${searchShown}/${searchAllResults.length})`;
            } else {
                hide(searchLoadMoreWrap);
            }
        }
    }

    if (searchLoadMoreBtn) {
        searchLoadMoreBtn.addEventListener('click', showMoreSearchResults);
    }

    // ==================== Facebook Cookie Helper ====================
    let fbCookiesLoaded = false;

    function toggleFbCookieHelper(platform) {
        const helper = $('fbCookieHelper');
        if (!helper) return;
        if (platform === 'facebook' || platform === 'instagram') {
            // Check cookie status from server
            if (!fbCookiesLoaded) {
                fetch('/api/cookies/status').then(r => r.json()).then(d => {
                    fbCookiesLoaded = true;
                    if (d.has_cookies && d.platforms.includes(platform)) {
                        const st = $('cookieStatus');
                        if (st) { st.textContent = '✓ Cookies configured'; st.className = 'cookie-status'; }
                        hide(helper); // Already has cookies, no need to show
                    } else {
                        show(helper);
                    }
                }).catch(() => show(helper));
            } else {
                show(helper);
            }
        } else {
            hide(helper);
        }
    }

    // Cookie file upload
    const cookieFileInput = $('cookieFileInput');
    if (cookieFileInput) {
        cookieFileInput.addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (!file) return;
            const st = $('cookieStatus');
            try {
                const formData = new FormData();
                formData.append('file', file);
                const r = await fetch('/api/cookies/upload', { method: 'POST', body: formData });
                const d = await r.json();
                if (d.success) {
                    if (st) { st.textContent = '✓ ' + d.message; st.className = 'cookie-status'; }
                    fbCookiesLoaded = false; // Reset so next check picks up new cookies
                } else {
                    if (st) { st.textContent = '✗ ' + (d.error || 'Upload failed'); st.className = 'cookie-status error'; }
                }
            } catch(err) {
                if (st) { st.textContent = '✗ Upload error'; st.className = 'cookie-status error'; }
            }
        });
    }

    // Also show/hide cookie helper when profile platform badges are clicked
    $('profilePlatformBadges').addEventListener('click', e => {
        const btn = e.target.closest('.ps-badge');
        if (btn) toggleFbCookieHelper(btn.dataset.plat);
    });

    // ==================== Donate (Bakong KHQR) ====================
    const donateBtn = $('donateBtn'), donateModal = $('donateModal');
    const donateClose = $('donateModalClose');
    const donateFormView = $('donateFormView'), donateQRView = $('donateQRView');
    const donateAmountInput = $('donateAmount');
    const donateGenerateBtn = $('donateGenerateBtn');
    const donateError = $('donateError');
    const soundSuccess = $('soundSuccess'), soundExpired = $('soundExpired');

    let donateCheckInterval = null;
    let donateCountdownInterval = null;

    function donateReset() {
        // Reset to form view
        if (donateFormView) donateFormView.style.display = 'block';
        if (donateQRView) donateQRView.style.display = 'none';
        if (donateError) { donateError.style.display = 'none'; donateError.textContent = ''; }
        if (donateGenerateBtn) {
            donateGenerateBtn.disabled = false;
            donateGenerateBtn.innerHTML = '<i class="fas fa-qrcode"></i> បង្កើត QR Code';
        }
        const newBtn = $('khqrNewPayment');
        if (newBtn) newBtn.style.display = 'none';
        clearInterval(donateCheckInterval);
        clearInterval(donateCountdownInterval);
    }

    if (donateBtn && donateModal) {
        // Open modal
        donateBtn.addEventListener('click', () => {
            donateReset();
            donateModal.style.display = 'flex';
        });

        // Close modal
        donateClose.addEventListener('click', () => {
            donateModal.style.display = 'none';
            donateReset();
        });
        donateModal.querySelector('.donate-modal-overlay').addEventListener('click', () => {
            donateModal.style.display = 'none';
            donateReset();
        });

        // Amount preset buttons
        donateModal.querySelectorAll('.donate-amount').forEach(btn => {
            btn.addEventListener('click', () => {
                donateModal.querySelectorAll('.donate-amount').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                if (donateAmountInput) donateAmountInput.value = btn.dataset.amount;
            });
        });

        // Custom amount sync
        if (donateAmountInput) {
            donateAmountInput.addEventListener('input', () => {
                donateModal.querySelectorAll('.donate-amount').forEach(b => {
                    b.classList.toggle('active', b.dataset.amount === donateAmountInput.value);
                });
            });
        }

        // Generate QR
        if (donateGenerateBtn) {
            donateGenerateBtn.addEventListener('click', async () => {
                const amount = (donateAmountInput ? donateAmountInput.value : '2') || '2';
                if (parseFloat(amount) < 0.5) {
                    if (donateError) { donateError.textContent = '⚠️ ចំនួនតិចបំផុត $0.50'; donateError.style.display = 'block'; }
                    return;
                }

                donateGenerateBtn.disabled = true;
                donateGenerateBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> កំពុងបង្កើត...';
                if (donateError) donateError.style.display = 'none';

                try {
                    const r = await fetch('/api/donate/generate-qr', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ amount: parseFloat(amount) })
                    });
                    const d = await r.json();

                    if (!d.success) {
                        if (donateError) { donateError.textContent = d.error || 'Error generating QR'; donateError.style.display = 'block'; }
                        donateGenerateBtn.disabled = false;
                        donateGenerateBtn.innerHTML = '<i class="fas fa-qrcode"></i> បង្កើត QR Code';
                        return;
                    }

                    // Switch to QR view
                    donateFormView.style.display = 'none';
                    donateQRView.style.display = 'block';

                    // Set QR data
                    const khqrImg = $('khqrImage');
                    const khqrAmount = $('khqrAmount');
                    const khqrMerchant = $('khqrMerchant');
                    const khqrCountdown = $('khqrCountdown');
                    const khqrStatus = $('khqrStatus');
                    const khqrScanMsg = $('khqrScanMsg');
                    const newPaymentBtn = $('khqrNewPayment');

                    if (khqrImg) khqrImg.src = d.qr_image_url;
                    if (khqrAmount) khqrAmount.textContent = d.amount + ' USD';
                    if (khqrMerchant) khqrMerchant.textContent = d.merchant || 'SMMMEGA';

                    const md5 = d.md5;
                    const expiry = (d.expiry || 120) * 1000;
                    const startTime = Date.now();
                    let isExpired = false;
                    let isPaid = false;

                    // Countdown timer
                    donateCountdownInterval = setInterval(() => {
                        const elapsed = Date.now() - startTime;
                        const remaining = expiry - elapsed;
                        if (remaining <= 0) {
                            clearInterval(donateCountdownInterval);
                            clearInterval(donateCheckInterval);
                            isExpired = true;
                            if (khqrCountdown) {
                                khqrCountdown.textContent = 'QR expired!';
                                khqrCountdown.classList.add('expired');
                            }
                            if (khqrStatus && !isPaid) {
                                khqrStatus.innerHTML = '<i class="fas fa-times-circle"></i> ផុតកំណត់';
                                khqrStatus.classList.add('status-expired');
                            }
                            if (newPaymentBtn) newPaymentBtn.style.display = 'block';
                            try { if (soundExpired) soundExpired.play(); } catch(e) {}
                            return;
                        }
                        const m = Math.floor(remaining / 60000);
                        const s = Math.floor((remaining % 60000) / 1000);
                        if (khqrCountdown) {
                            khqrCountdown.textContent = `ពេលវេលាដែលនៅសល់: ${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
                        }
                    }, 1000);

                    // Check payment status every 5s
                    donateCheckInterval = setInterval(async () => {
                        if (isExpired || isPaid) return;
                        try {
                            const sr = await fetch(`/api/donate/check-status?md5=${encodeURIComponent(md5)}`);
                            const sd = await sr.json();

                            if (sd.status === 'PAID') {
                                isPaid = true;
                                clearInterval(donateCheckInterval);
                                clearInterval(donateCountdownInterval);

                                if (khqrStatus) {
                                    khqrStatus.innerHTML = '<i class="fas fa-check-circle"></i> ✅ បង់ប្រាក់ជោគជ័យ!';
                                    khqrStatus.classList.remove('status-expired');
                                    khqrStatus.classList.add('status-paid');
                                }
                                if (khqrCountdown) khqrCountdown.style.display = 'none';
                                if (khqrScanMsg) {
                                    khqrScanMsg.textContent = `អ្នកបានបរិច្ចាគ ${d.amount}$ ដោយជោគជ័យ។ អរគុណ! ❤️`;
                                    khqrScanMsg.style.display = 'block';
                                }
                                if (newPaymentBtn) newPaymentBtn.style.display = 'block';
                                try { if (soundSuccess) soundSuccess.play(); } catch(e) {}
                            } else if (sd.status === 'EXPIRED') {
                                isExpired = true;
                                clearInterval(donateCheckInterval);
                                clearInterval(donateCountdownInterval);
                                if (khqrCountdown) {
                                    khqrCountdown.textContent = 'QR expired!';
                                    khqrCountdown.classList.add('expired');
                                }
                                if (khqrStatus) {
                                    khqrStatus.innerHTML = '<i class="fas fa-times-circle"></i> ផុតកំណត់';
                                    khqrStatus.classList.add('status-expired');
                                }
                                if (newPaymentBtn) newPaymentBtn.style.display = 'block';
                                try { if (soundExpired) soundExpired.play(); } catch(e) {}
                            }
                        } catch(e) { /* network error, keep trying */ }
                    }, 5000);

                    // New payment button
                    if (newPaymentBtn) {
                        newPaymentBtn.onclick = () => { donateReset(); };
                    }

                } catch (e) {
                    if (donateError) { donateError.textContent = '⚠️ កំហុសក្នុងការតភ្ជាប់'; donateError.style.display = 'block'; }
                    donateGenerateBtn.disabled = false;
                    donateGenerateBtn.innerHTML = '<i class="fas fa-qrcode"></i> បង្កើត QR Code';
                }
            });
        }
    }

    // ==================== Watermark Remover ====================
    const wmUrlInput = $('wmUrlInput');
    const wmPasteBtn = $('wmPasteBtn');
    const wmFileInput = $('wmFileInput');
    const wmUploadArea = $('wmUploadArea');
    const wmFileName = $('wmFileName');
    const wmRemoveBtn = $('wmRemoveBtn');
    const wmProcessing = $('wmProcessing');
    const wmProcessText = $('wmProcessText');
    const wmProgressFill = $('wmProgressFill');
    const wmProgressLabel = $('wmProgressLabel');
    const wmErrorSection = $('wmErrorSection');
    const wmErrorMsg = $('wmErrorMsg');
    const wmRetryBtn = $('wmRetryBtn');
    const wmSuccessSection = $('wmSuccessSection');
    const wmOrigVideo = $('wmOrigVideo');
    const wmResultVideo = $('wmResultVideo');
    const wmDownloadLink = $('wmDownloadLink');
    const wmNewBtn = $('wmNewBtn');

    let wmSelectedFile = null;

    if (wmPasteBtn) {
        wmPasteBtn.addEventListener('click', async () => {
            try {
                const t = await navigator.clipboard.readText();
                if (t && wmUrlInput) wmUrlInput.value = t;
            } catch(e) {}
        });
    }

    if (wmFileInput) {
        wmFileInput.addEventListener('change', () => {
            if (wmFileInput.files.length > 0) {
                wmSelectedFile = wmFileInput.files[0];
                if (wmFileName) wmFileName.textContent = wmSelectedFile.name;
                if (wmUploadArea) wmUploadArea.classList.add('has-file');
            }
        });
    }

    // Position buttons
    document.querySelectorAll('.wm-pos-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.wm-pos-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        });
    });

    function wmReset() {
        if (wmProcessing) wmProcessing.style.display = 'none';
        if (wmErrorSection) wmErrorSection.style.display = 'none';
        if (wmSuccessSection) wmSuccessSection.style.display = 'none';
        if (wmRemoveBtn) {
            wmRemoveBtn.disabled = false;
            wmRemoveBtn.querySelector('span').textContent = 'លុប Watermark';
        }
        if (wmProgressFill) wmProgressFill.style.width = '0%';
        if (wmProgressLabel) wmProgressLabel.textContent = '0%';
    }

    function wmShowError(msg) {
        wmReset();
        if (wmErrorSection) wmErrorSection.style.display = '';
        if (wmErrorMsg) wmErrorMsg.textContent = msg;
    }

    if (wmRetryBtn) wmRetryBtn.addEventListener('click', wmReset);
    if (wmNewBtn) wmNewBtn.addEventListener('click', () => {
        wmReset();
        wmSelectedFile = null;
        if (wmFileInput) wmFileInput.value = '';
        if (wmFileName) wmFileName.textContent = 'ចុចដើម្បីជ្រើសរើសវីដេអូ ឬ អូសដាក់ទីនេះ';
        if (wmUploadArea) wmUploadArea.classList.remove('has-file');
        if (wmUrlInput) wmUrlInput.value = '';
    });

    // Drag & drop
    if (wmUploadArea) {
        wmUploadArea.addEventListener('dragover', e => { e.preventDefault(); wmUploadArea.classList.add('dragover'); });
        wmUploadArea.addEventListener('dragleave', () => wmUploadArea.classList.remove('dragover'));
        wmUploadArea.addEventListener('drop', e => {
            e.preventDefault();
            wmUploadArea.classList.remove('dragover');
            if (e.dataTransfer.files.length > 0) {
                wmSelectedFile = e.dataTransfer.files[0];
                wmFileInput.files = e.dataTransfer.files;
                if (wmFileName) wmFileName.textContent = wmSelectedFile.name;
                wmUploadArea.classList.add('has-file');
            }
        });
    }

    // Remove watermark
    if (wmRemoveBtn) {
        wmRemoveBtn.addEventListener('click', async () => {
            const url = wmUrlInput ? wmUrlInput.value.trim() : '';
            const file = wmSelectedFile;

            if (!url && !file) {
                wmShowError('សូមផ្តល់ URL ឬ Upload ឯកសារវីដេអូ');
                return;
            }

            const position = document.querySelector('.wm-pos-btn.active')?.dataset.pos || 'bottom-left';
            const method = $('wmMethod') ? $('wmMethod').value : 'blur';
            const blurStrength = $('wmBlurStrength') ? $('wmBlurStrength').value : '20';

            wmReset();
            wmRemoveBtn.disabled = true;
            wmRemoveBtn.querySelector('span').textContent = 'កំពុងដំណើរការ...';
            if (wmProcessing) wmProcessing.style.display = '';

            const formData = new FormData();
            formData.append('position', position);
            formData.append('method', method);
            formData.append('blur_strength', blurStrength);

            if (file) {
                formData.append('file', file);
                if (wmProcessText) wmProcessText.textContent = 'កំពុង Upload និង លុប Watermark...';
            } else {
                formData.append('url', url);
                if (wmProcessText) wmProcessText.textContent = 'កំពុងទាញយក និង លុប Watermark...';
            }

            try {
                const r = await fetch('/api/watermark/remove', { method: 'POST', body: formData });
                const d = await r.json();

                if (d.error) {
                    wmShowError(d.error);
                    return;
                }

                const taskId = d.task_id;
                const origFile = d.original;

                // Poll progress
                if (wmProcessText) wmProcessText.textContent = 'កំពុងលុប Watermark...';
                const pollInterval = setInterval(async () => {
                    try {
                        const pr = await fetch(`/api/watermark/progress/${taskId}`);
                        const pd = await pr.json();

                        if (pd.status === 'completed') {
                            clearInterval(pollInterval);
                            if (wmProcessing) wmProcessing.style.display = 'none';
                            if (wmSuccessSection) wmSuccessSection.style.display = '';

                            // Set videos for comparison
                            if (wmOrigVideo && origFile) wmOrigVideo.src = `/api/file/${encodeURIComponent(origFile)}`;
                            if (wmResultVideo && pd.filename) wmResultVideo.src = `/api/file/${encodeURIComponent(pd.filename)}`;
                            if (wmDownloadLink && pd.filename) wmDownloadLink.href = `/api/file/${encodeURIComponent(pd.filename)}`;

                            wmRemoveBtn.disabled = false;
                            wmRemoveBtn.querySelector('span').textContent = 'លុប Watermark';
                        } else if (pd.status === 'error') {
                            clearInterval(pollInterval);
                            wmShowError(pd.error || 'កំហុសក្នុងការលុប Watermark');
                        } else {
                            // Update progress
                            const pct = pd.percent || 0;
                            if (wmProgressFill) wmProgressFill.style.width = pct + '%';
                            if (wmProgressLabel) wmProgressLabel.textContent = pct + '%';
                        }
                    } catch(e) { /* keep polling */ }
                }, 2000);

            } catch(e) {
                wmShowError('កំហុសក្នុងការតភ្ជាប់ Server');
            }
        });
    }

    // ==================== Save Location ====================
    const saveLocPath = document.getElementById('saveLocPath');
    const saveLocStats = document.getElementById('saveLocStats');
    const saveLocEditBtn = document.getElementById('saveLocEditBtn');
    const saveLocOpenBtn = document.getElementById('saveLocOpenBtn');
    const saveLocEdit = document.getElementById('saveLocEdit');
    const saveLocInput = document.getElementById('saveLocInput');
    const saveLocSaveBtn = document.getElementById('saveLocSaveBtn');
    const saveLocCancelBtn = document.getElementById('saveLocCancelBtn');

    function formatBytes(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
        if (bytes < 1073741824) return (bytes / 1048576).toFixed(1) + ' MB';
        return (bytes / 1073741824).toFixed(2) + ' GB';
    }

    async function loadSaveLocation() {
        try {
            const r = await fetch('/api/save-location');
            const d = await r.json();
            if (saveLocPath) {
                saveLocPath.textContent = d.path;
                saveLocPath.title = d.path;
            }
            if (saveLocStats) {
                saveLocStats.innerHTML = `<span>${d.file_count} ឯកសារ</span> · <span>${formatBytes(d.total_size)}</span>`;
            }
            if (saveLocInput) saveLocInput.value = d.path;
        } catch(e) {}
    }

    // Load on init
    loadSaveLocation();

    // Edit button
    if (saveLocEditBtn) {
        saveLocEditBtn.addEventListener('click', () => {
            if (saveLocEdit) saveLocEdit.style.display = '';
            if (saveLocInput) {
                saveLocInput.value = saveLocPath ? saveLocPath.textContent : '';
                saveLocInput.focus();
            }
        });
    }

    // Cancel
    if (saveLocCancelBtn) {
        saveLocCancelBtn.addEventListener('click', () => {
            if (saveLocEdit) saveLocEdit.style.display = 'none';
        });
    }

    // Save
    if (saveLocSaveBtn) {
        saveLocSaveBtn.addEventListener('click', async () => {
            const newPath = saveLocInput ? saveLocInput.value.trim() : '';
            if (!newPath) return;
            saveLocSaveBtn.disabled = true;
            saveLocSaveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> កំពុង...';
            try {
                const r = await fetch('/api/save-location', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ path: newPath })
                });
                const d = await r.json();
                if (d.success) {
                    if (saveLocEdit) saveLocEdit.style.display = 'none';
                    loadSaveLocation();
                } else {
                    alert(d.error || 'កំហុស');
                }
            } catch(e) {
                alert('កំហុសក្នុងការតភ្ជាប់');
            } finally {
                saveLocSaveBtn.disabled = false;
                saveLocSaveBtn.innerHTML = '<i class="fas fa-check"></i> រក្សាទុក';
            }
        });
    }

    // Presets
    document.querySelectorAll('.save-loc-preset').forEach(btn => {
        btn.addEventListener('click', () => {
            if (saveLocInput) saveLocInput.value = btn.dataset.path;
        });
    });

    // Open folder
    if (saveLocOpenBtn) {
        saveLocOpenBtn.addEventListener('click', async () => {
            try {
                await fetch('/api/save-location/open', { method: 'POST' });
            } catch(e) {}
        });
    }

    // ==================== Sora2 No Watermark Downloader (soravdl-style) ====================
    const sora2UrlInput = document.getElementById('sora2UrlInput');
    const sora2UrlCount = document.getElementById('sora2UrlCount');
    const sora2PasteBtn = document.getElementById('sora2PasteBtn');
    const sora2ClearBtn = document.getElementById('sora2ClearBtn');
    const sora2DownloadBtn = document.getElementById('sora2DownloadBtn');
    const sora2Processing = document.getElementById('sora2Processing');
    const sora2ProcessTitle = document.getElementById('sora2ProcessTitle');
    const sora2ProcessText = document.getElementById('sora2ProcessText');
    const sora2ProgressFill = document.getElementById('sora2ProgressFill');
    const sora2ProgressLabel = document.getElementById('sora2ProgressLabel');
    const sora2CurrentUrl = document.getElementById('sora2CurrentUrl');
    const sora2ErrorSection = document.getElementById('sora2ErrorSection');
    const sora2ErrorMsg = document.getElementById('sora2ErrorMsg');
    const sora2RetryBtn = document.getElementById('sora2RetryBtn');
    const sora2ResultsSection = document.getElementById('sora2ResultsSection');
    const sora2ResultsSummary = document.getElementById('sora2ResultsSummary');
    const sora2ResultsGrid = document.getElementById('sora2ResultsGrid');
    const sora2DownloadAllBtn = document.getElementById('sora2DownloadAllBtn');
    const sora2NewBatchBtn = document.getElementById('sora2NewBatchBtn');

    // Count URLs
    function sora2CountUrls() {
        if (!sora2UrlInput || !sora2UrlCount) return 0;
        const lines = sora2UrlInput.value.split('\n').filter(l => l.trim());
        const count = lines.length;
        sora2UrlCount.textContent = count + ' URL' + (count !== 1 ? 's' : '');
        return count;
    }
    if (sora2UrlInput) sora2UrlInput.addEventListener('input', sora2CountUrls);

    // Paste
    if (sora2PasteBtn) {
        sora2PasteBtn.addEventListener('click', async () => {
            try {
                const txt = await navigator.clipboard.readText();
                if (txt && sora2UrlInput) {
                    sora2UrlInput.value = sora2UrlInput.value ? sora2UrlInput.value + '\n' + txt : txt;
                    sora2CountUrls();
                }
            } catch(e) {}
        });
    }

    // Clear
    if (sora2ClearBtn) {
        sora2ClearBtn.addEventListener('click', () => {
            if (sora2UrlInput) sora2UrlInput.value = '';
            sora2CountUrls();
        });
    }

    function sora2Reset() {
        const card = document.querySelector('.sora2-card');
        if (card) card.style.display = '';
        if (sora2Processing) sora2Processing.style.display = 'none';
        if (sora2ErrorSection) sora2ErrorSection.style.display = 'none';
        if (sora2ResultsSection) sora2ResultsSection.style.display = 'none';
        if (sora2DownloadBtn) {
            sora2DownloadBtn.disabled = false;
            sora2DownloadBtn.querySelector('span').textContent = 'Download Without Watermark';
        }
    }

    function sora2ShowError(msg) {
        const card = document.querySelector('.sora2-card');
        if (card) card.style.display = 'none';
        if (sora2Processing) sora2Processing.style.display = 'none';
        if (sora2ErrorSection) sora2ErrorSection.style.display = '';
        if (sora2ErrorMsg) sora2ErrorMsg.textContent = msg;
    }

    function sora2ShowResults(data) {
        const card = document.querySelector('.sora2-card');
        if (card) card.style.display = 'none';
        if (sora2Processing) sora2Processing.style.display = 'none';
        if (sora2ResultsSection) sora2ResultsSection.style.display = '';

        const results = data.results || [];
        const errors = data.errors || [];
        const total = results.length + errors.length;

        if (sora2ResultsSummary) {
            sora2ResultsSummary.textContent = `Download complete! ${results.length}/${total} video${results.length !== 1 ? 's' : ''} saved in HD with no watermark.`;
        }

        if (sora2ResultsGrid) {
            sora2ResultsGrid.innerHTML = '';

            // Success cards
            results.forEach((item, idx) => {
                const resultCard = document.createElement('div');
                resultCard.className = 'sora2-result-card success';
                const shortUrl = item.url.length > 55 ? item.url.substring(0, 55) + '...' : item.url;
                const cleanUrl = `/api/sora/download-file/${item.output_dir}/${encodeURIComponent(item.clean_file)}`;
                const origUrl = `/api/sora/download-original/${encodeURIComponent(item.original_file)}`;
                resultCard.innerHTML = `
                    <div class="sora2-result-index">${idx + 1}</div>
                    <div class="sora2-result-info">
                        <div class="sora2-result-url" title="${item.url}">${shortUrl}</div>
                        <div class="sora2-result-status"><i class="fas fa-circle-check"></i> No Watermark — Clean MP4 HD</div>
                    </div>
                    <div class="sora2-result-actions">
                        <a href="${cleanUrl}" class="sora2-dl-btn" download><i class="fas fa-download"></i> No Watermark</a>
                        <a href="${origUrl}" class="sora2-dl-btn orig" download><i class="fas fa-film"></i> Original</a>
                    </div>
                `;
                sora2ResultsGrid.appendChild(resultCard);
            });

            // Error cards
            errors.forEach((item, idx) => {
                const errCard = document.createElement('div');
                errCard.className = 'sora2-result-card error';
                const shortUrl = item.url.length > 55 ? item.url.substring(0, 55) + '...' : item.url;
                errCard.innerHTML = `
                    <div class="sora2-result-index">${results.length + idx + 1}</div>
                    <div class="sora2-result-info">
                        <div class="sora2-result-url" title="${item.url}">${shortUrl}</div>
                        <div class="sora2-result-status error"><i class="fas fa-times-circle"></i> ${item.error}</div>
                    </div>
                `;
                sora2ResultsGrid.appendChild(errCard);
            });
        }

        // Play success sound
        const snd = document.getElementById('soundSuccess');
        if (snd) { snd.currentTime = 0; snd.play().catch(()=>{}); }
    }

    // Retry
    if (sora2RetryBtn) sora2RetryBtn.addEventListener('click', sora2Reset);
    if (sora2NewBatchBtn) sora2NewBatchBtn.addEventListener('click', sora2Reset);

    // Download All
    if (sora2DownloadAllBtn) {
        sora2DownloadAllBtn.addEventListener('click', () => {
            const links = document.querySelectorAll('.sora2-result-card.success .sora2-dl-btn:first-child');
            links.forEach((a, i) => {
                setTimeout(() => { a.click(); }, i * 800);
            });
        });
    }

    // Main download button
    if (sora2DownloadBtn) {
        sora2DownloadBtn.addEventListener('click', async () => {
            const urlText = sora2UrlInput ? sora2UrlInput.value.trim() : '';

            if (!urlText) {
                sora2ShowError('Please enter at least one Sora video URL');
                return;
            }

            // Show processing
            const card = document.querySelector('.sora2-card');
            if (card) card.style.display = 'none';
            if (sora2Processing) sora2Processing.style.display = '';
            if (sora2ErrorSection) sora2ErrorSection.style.display = 'none';
            if (sora2ResultsSection) sora2ResultsSection.style.display = 'none';
            if (sora2ProcessTitle) sora2ProcessTitle.textContent = 'Processing your video...';

            try {
                const r = await fetch('/api/sora/download', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ urls: urlText })
                });
                const d = await r.json();

                if (!r.ok || d.error) {
                    sora2ShowError(d.error || 'Unknown error occurred');
                    return;
                }

                const taskId = d.task_id;
                const total = d.total;
                if (sora2ProgressLabel) sora2ProgressLabel.textContent = `0 / ${total}`;

                // Poll status
                const pollInterval = setInterval(async () => {
                    try {
                        const sr = await fetch(`/api/sora/status/${taskId}`);
                        const sd = await sr.json();

                        if (sd.status === 'completed') {
                            clearInterval(pollInterval);
                            sora2ShowResults(sd);
                            return;
                        }

                        // Update progress
                        const pct = sd.percent || 0;
                        const cur = sd.current || 0;
                        const tot = sd.total || total;
                        const aiProg = sd.ai_progress || 0;
                        if (sora2ProgressFill) sora2ProgressFill.style.width = pct + '%';
                        if (sora2ProgressLabel) sora2ProgressLabel.textContent = `${cur} / ${tot}`;

                        // Show step info
                        const stepLabel = sd.status === 'downloading' ? 'Downloading HD video...' :
                                         sd.status === 'removing_watermark' ? `Removing watermark... (${aiProg}%)` :
                                         'Processing...';
                        if (sora2ProcessText) sora2ProcessText.textContent = `Video ${cur}/${tot} — ${stepLabel}`;
                        if (sora2ProcessTitle) sora2ProcessTitle.textContent = stepLabel;

                        if (sora2CurrentUrl && sd.current_url) {
                            const short = sd.current_url.length > 60 ? sd.current_url.substring(0, 60) + '...' : sd.current_url;
                            sora2CurrentUrl.textContent = short;
                        }

                    } catch(e) { /* keep polling */ }
                }, 2000);

            } catch(e) {
                sora2ShowError('Network error. Please try again.');
            }
        });
    }

})();
