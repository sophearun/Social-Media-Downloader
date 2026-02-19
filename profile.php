<?php
require_once __DIR__ . '/config/app.php';
require_once __DIR__ . '/includes/auth.php';
require_once __DIR__ . '/includes/functions.php';
require_once __DIR__ . '/config/db.php';

requireLogin();

$user = currentUser();
$pdo  = getDB();

// Fetch fresh data
$stmt = $pdo->prepare('SELECT * FROM users WHERE id = ? LIMIT 1');
$stmt->execute([$user['id']]);
$dbUser = $stmt->fetch();

if (!$dbUser) {
    logoutUser();
    header('Location: /login');
    exit;
}

// Download history
$hist = $pdo->prepare(
    'SELECT * FROM download_history WHERE user_id = ? ORDER BY downloaded_at DESC LIMIT 20'
);
$hist->execute([$user['id']]);
$history = $hist->fetchAll();

$pageTitle = 'Profile';
require_once __DIR__ . '/includes/header.php';
require_once __DIR__ . '/includes/nav.php';
?>

<main class="admin-main" style="max-width:900px;margin:0 auto">
    <!-- Profile Header Card -->
    <div class="acard mb-6">
        <div class="profile-hero">
            <div class="profile-avatar-wrap">
                <?php
                $avatarSrc = !empty($dbUser['avatar'])
                    ? sanitize($dbUser['avatar'])
                    : sanitize(generateAvatar($dbUser['full_name'] ?: $dbUser['username'], 120));
                ?>
                <img src="<?= $avatarSrc ?>" alt="Avatar" class="profile-avatar-img">
            </div>
            <div class="profile-info">
                <h1 class="profile-name"><?= sanitize($dbUser['full_name'] ?: $dbUser['username']) ?></h1>
                <p class="profile-username">@<?= sanitize($dbUser['username']) ?></p>
                <p class="profile-email"><i class="fas fa-envelope"></i> <?= sanitize($dbUser['email']) ?></p>
                <?php if (!empty($dbUser['bio'])): ?>
                <p class="profile-bio"><?= sanitize($dbUser['bio']) ?></p>
                <?php endif; ?>
                <div class="profile-meta">
                    <span class="badge badge-<?= $dbUser['role'] === 'admin' ? 'purple' : 'blue' ?>">
                        <i class="fas fa-<?= $dbUser['role'] === 'admin' ? 'shield-halved' : 'user' ?>"></i>
                        <?= sanitize(ucfirst($dbUser['role'])) ?>
                    </span>
                    <span class="badge badge-green">
                        <i class="fas fa-circle" style="font-size:.5rem"></i>
                        <?= sanitize(ucfirst($dbUser['status'])) ?>
                    </span>
                    <span class="text-slate-400 text-sm">
                        <i class="fas fa-calendar"></i>
                        Joined <?= date('M Y', strtotime($dbUser['created_at'])) ?>
                    </span>
                </div>
            </div>
            <div class="profile-actions">
                <a href="/profile/edit" class="btn-primary">
                    <i class="fas fa-pen"></i> Edit Profile
                </a>
            </div>
        </div>
    </div>

    <!-- Download History -->
    <div class="acard">
        <div class="acard-header">
            <h2 class="acard-title"><i class="fas fa-clock-rotate-left"></i> Download History</h2>
            <span class="badge badge-blue"><?= count($history) ?> recent</span>
        </div>
        <?php if (empty($history)): ?>
        <div class="empty-state">
            <i class="fas fa-download empty-icon"></i>
            <p>No downloads yet. <a href="/">Start downloading</a></p>
        </div>
        <?php else: ?>
        <div class="table-wrap">
            <table class="admin-table">
                <thead>
                    <tr>
                        <th>Platform</th>
                        <th>Title / URL</th>
                        <th>Downloaded</th>
                    </tr>
                </thead>
                <tbody>
                    <?php foreach ($history as $h): ?>
                    <tr>
                        <td>
                            <span class="badge badge-blue"><?= sanitize($h['platform'] ?? 'unknown') ?></span>
                        </td>
                        <td>
                            <div class="text-sm font-medium"><?= sanitize(substr($h['title'] ?? '', 0, 60)) ?></div>
                            <div class="text-xs text-slate-500 truncate" style="max-width:260px">
                                <?= sanitize($h['url']) ?>
                            </div>
                        </td>
                        <td class="text-slate-400 text-sm"><?= sanitize(timeAgo($h['downloaded_at'])) ?></td>
                    </tr>
                    <?php endforeach; ?>
                </tbody>
            </table>
        </div>
        <?php endif; ?>
    </div>
</main>

<?php require_once __DIR__ . '/includes/footer.php'; ?>
