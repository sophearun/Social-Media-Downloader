<?php
require_once __DIR__ . '/../config/app.php';
require_once __DIR__ . '/../includes/auth.php';
require_once __DIR__ . '/../includes/functions.php';
require_once __DIR__ . '/../config/db.php';

requireAdmin();

$pdo = getDB();

// Stats
$totalUsers   = (int) $pdo->query('SELECT COUNT(*) FROM users')->fetchColumn();
$activeUsers  = (int) $pdo->query('SELECT COUNT(*) FROM users WHERE status = "active"')->fetchColumn();
$adminUsers   = (int) $pdo->query('SELECT COUNT(*) FROM users WHERE role = "admin"')->fetchColumn();
$dlToday      = (int) $pdo->query('SELECT COUNT(*) FROM download_history WHERE DATE(downloaded_at) = CURDATE()')->fetchColumn();
$dlTotal      = (int) $pdo->query('SELECT COUNT(*) FROM download_history')->fetchColumn();

// Recent users
$recent = $pdo->query('SELECT * FROM users ORDER BY created_at DESC LIMIT 10')->fetchAll();

$pageTitle = 'Admin Dashboard';
require_once __DIR__ . '/../includes/header.php';
require_once __DIR__ . '/../includes/nav.php';
?>

<main class="admin-main">
    <!-- Page header -->
    <div class="page-header">
        <div>
            <h1 class="page-title"><i class="fas fa-shield-halved"></i> Admin Dashboard</h1>
            <p class="page-subtitle">Welcome back, <?= sanitize(currentUser()['username']) ?></p>
        </div>
        <a href="/admin/users/add" class="btn-primary">
            <i class="fas fa-user-plus"></i> Add User
        </a>
    </div>

    <!-- Stats -->
    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-icon stat-purple"><i class="fas fa-users"></i></div>
            <div>
                <div class="stat-val"><?= $totalUsers ?></div>
                <div class="stat-label">Total Users</div>
            </div>
        </div>
        <div class="stat-card">
            <div class="stat-icon stat-green"><i class="fas fa-user-check"></i></div>
            <div>
                <div class="stat-val"><?= $activeUsers ?></div>
                <div class="stat-label">Active Users</div>
            </div>
        </div>
        <div class="stat-card">
            <div class="stat-icon stat-cyan"><i class="fas fa-download"></i></div>
            <div>
                <div class="stat-val"><?= $dlToday ?></div>
                <div class="stat-label">Downloads Today</div>
            </div>
        </div>
        <div class="stat-card">
            <div class="stat-icon stat-amber"><i class="fas fa-clock-rotate-left"></i></div>
            <div>
                <div class="stat-val"><?= formatNumber($dlTotal) ?></div>
                <div class="stat-label">Total Downloads</div>
            </div>
        </div>
    </div>

    <!-- Quick actions -->
    <div class="quick-actions mb-6">
        <a href="/admin/users" class="qaction-card">
            <i class="fas fa-users qaction-icon"></i>
            <span>Manage Users</span>
        </a>
        <a href="/admin/users/add" class="qaction-card">
            <i class="fas fa-user-plus qaction-icon"></i>
            <span>Add New User</span>
        </a>
        <a href="/" class="qaction-card">
            <i class="fas fa-download qaction-icon"></i>
            <span>Downloader</span>
        </a>
    </div>

    <!-- Recent users -->
    <div class="acard">
        <div class="acard-header">
            <h2 class="acard-title"><i class="fas fa-users"></i> Recent Users</h2>
            <a href="/admin/users" class="btn-ghost btn-sm">View All</a>
        </div>
        <div class="table-wrap">
            <table class="admin-table">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>User</th>
                        <th>Email</th>
                        <th>Role</th>
                        <th>Status</th>
                        <th>Joined</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                <?php foreach ($recent as $u): ?>
                <tr>
                    <td class="text-slate-500"><?= (int) $u['id'] ?></td>
                    <td>
                        <div class="user-cell">
                            <img src="<?= sanitize(!empty($u['avatar']) ? $u['avatar'] : generateAvatar($u['full_name'] ?: $u['username'], 36)) ?>"
                                 alt="" class="user-avatar-sm">
                            <div>
                                <div class="font-medium"><?= sanitize($u['full_name'] ?: $u['username']) ?></div>
                                <div class="text-slate-500 text-xs">@<?= sanitize($u['username']) ?></div>
                            </div>
                        </div>
                    </td>
                    <td class="text-slate-400"><?= sanitize($u['email']) ?></td>
                    <td><span class="badge badge-<?= $u['role'] === 'admin' ? 'purple' : 'blue' ?>"><?= sanitize(ucfirst($u['role'])) ?></span></td>
                    <td>
                        <?php
                        $sc = ['active' => 'green', 'inactive' => 'amber', 'banned' => 'red'];
                        $s  = $u['status'] ?? 'inactive';
                        ?>
                        <span class="badge badge-<?= $sc[$s] ?? 'blue' ?>"><?= sanitize(ucfirst($s)) ?></span>
                    </td>
                    <td class="text-slate-400 text-sm"><?= date('M d, Y', strtotime($u['created_at'])) ?></td>
                    <td>
                        <div class="table-actions">
                            <a href="/admin/users/edit/<?= (int) $u['id'] ?>" class="taction-btn taction-edit" title="Edit">
                                <i class="fas fa-pen"></i>
                            </a>
                            <form method="POST" action="/admin/users/delete/<?= (int) $u['id'] ?>" style="display:inline"
                                  onsubmit="return confirm('Delete user <?= sanitize(addslashes($u['username'])) ?>?')">
                                <input type="hidden" name="csrf_token" value="<?= sanitize(csrfToken()) ?>">
                                <button type="submit" class="taction-btn taction-delete" title="Delete">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </form>
                        </div>
                    </td>
                </tr>
                <?php endforeach; ?>
                </tbody>
            </table>
        </div>
    </div>
</main>

<?php require_once __DIR__ . '/../includes/footer.php'; ?>
