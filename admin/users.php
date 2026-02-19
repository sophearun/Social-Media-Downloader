<?php
require_once __DIR__ . '/../config/app.php';
require_once __DIR__ . '/../includes/auth.php';
require_once __DIR__ . '/../includes/functions.php';
require_once __DIR__ . '/../config/db.php';

requireAdmin();

$pdo    = getDB();
$action = $_GET['action'] ?? 'list';
$id     = (int) ($_GET['id'] ?? 0);
$errors = [];
$success = '';

// ── DELETE ──────────────────────────────────────────────────
if ($action === 'delete') {
    if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
        header('Location: /admin/users');
        exit;
    }
    verifyCsrf();
    if ($id === (int) currentUser()['id']) {
        $errors[] = 'You cannot delete your own account.';
    } else {
        $pdo->prepare('DELETE FROM users WHERE id = ?')->execute([$id]);
        header('Location: /admin/users?msg=deleted');
        exit;
    }
}

// ── ADD / EDIT — POST ────────────────────────────────────────
if (in_array($action, ['add', 'edit'], true) && $_SERVER['REQUEST_METHOD'] === 'POST') {
    verifyCsrf();

    $username  = trim($_POST['username']  ?? '');
    $email     = trim($_POST['email']     ?? '');
    $full_name = trim($_POST['full_name'] ?? '');
    $bio       = trim($_POST['bio']       ?? '');
    $role      = in_array($_POST['role']   ?? '', ['admin', 'user'], true) ? $_POST['role'] : 'user';
    $status    = in_array($_POST['status'] ?? '', ['active', 'inactive', 'banned'], true) ? $_POST['status'] : 'active';
    $password  = $_POST['password'] ?? '';

    if ($action === 'add') {
        if (!preg_match('/^[a-zA-Z0-9_]{3,50}$/', $username)) {
            $errors[] = 'Username must be 3–50 alphanumeric characters / underscores.';
        }
        if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
            $errors[] = 'Invalid email address.';
        }
        if (strlen($password) < 8) {
            $errors[] = 'Password must be at least 8 characters.';
        }
        if (empty($errors)) {
            $chk = $pdo->prepare('SELECT id FROM users WHERE username = ? OR email = ? LIMIT 1');
            $chk->execute([$username, $email]);
            if ($chk->fetch()) {
                $errors[] = 'Username or email already exists.';
            }
        }
        if (empty($errors)) {
            $hash = password_hash($password, PASSWORD_BCRYPT);
            $pdo->prepare(
                'INSERT INTO users (username,email,password,full_name,bio,role,status) VALUES (?,?,?,?,?,?,?)'
            )->execute([$username, $email, $hash, $full_name, $bio, $role, $status]);
            header('Location: /admin/users?msg=added');
            exit;
        }
    } else { // edit
        if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
            $errors[] = 'Invalid email address.';
        }
        // Check email uniqueness (excluding self)
        if (empty($errors)) {
            $chk = $pdo->prepare('SELECT id FROM users WHERE email = ? AND id != ? LIMIT 1');
            $chk->execute([$email, $id]);
            if ($chk->fetch()) {
                $errors[] = 'That email is already in use by another account.';
            }
        }
        if (empty($errors)) {
            if ($password !== '') {
                if (strlen($password) < 8) {
                    $errors[] = 'Password must be at least 8 characters.';
                } else {
                    $hash = password_hash($password, PASSWORD_BCRYPT);
                    $pdo->prepare(
                        'UPDATE users SET email=?,full_name=?,bio=?,role=?,status=?,password=? WHERE id=?'
                    )->execute([$email, $full_name, $bio, $role, $status, $hash, $id]);
                }
            } else {
                $pdo->prepare(
                    'UPDATE users SET email=?,full_name=?,bio=?,role=?,status=? WHERE id=?'
                )->execute([$email, $full_name, $bio, $role, $status, $id]);
            }
            if (empty($errors)) {
                header('Location: /admin/users?msg=updated');
                exit;
            }
        }
    }
}

// ── Fetch user for edit form ─────────────────────────────────
$editUser = null;
if ($action === 'edit' && $id) {
    $stmt = $pdo->prepare('SELECT * FROM users WHERE id = ? LIMIT 1');
    $stmt->execute([$id]);
    $editUser = $stmt->fetch();
    if (!$editUser) {
        header('Location: /admin/users');
        exit;
    }
}

// ── List ─────────────────────────────────────────────────────
$search  = trim($_GET['q'] ?? '');
$page    = max(1, (int) ($_GET['page'] ?? 1));
$perPage = 15;
$offset  = ($page - 1) * $perPage;
$msg     = $_GET['msg'] ?? '';

if ($search) {
    $countStmt = $pdo->prepare('SELECT COUNT(*) FROM users WHERE username LIKE ? OR email LIKE ? OR full_name LIKE ?');
    $countStmt->execute(["%$search%", "%$search%", "%$search%"]);
    $total = (int) $countStmt->fetchColumn();

    $listStmt = $pdo->prepare(
        'SELECT * FROM users WHERE username LIKE ? OR email LIKE ? OR full_name LIKE ?
         ORDER BY created_at DESC LIMIT ? OFFSET ?'
    );
    $listStmt->execute(["%$search%", "%$search%", "%$search%", $perPage, $offset]);
} else {
    $total    = (int) $pdo->query('SELECT COUNT(*) FROM users')->fetchColumn();
    $listStmt = $pdo->prepare('SELECT * FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?');
    $listStmt->execute([$perPage, $offset]);
}
$users     = $listStmt->fetchAll();
$totalPages = (int) ceil($total / $perPage);

$pageTitle = 'Manage Users';
require_once __DIR__ . '/../includes/header.php';
require_once __DIR__ . '/../includes/nav.php';

// ── Flash messages ───────────────────────────────────────────
$msgMap = [
    'added'   => ['Saved', 'User added successfully.', 'success'],
    'updated' => ['Saved', 'User updated successfully.', 'success'],
    'deleted' => ['Deleted', 'User deleted.', 'error'],
];
?>

<main class="admin-main">
    <?php if ($msg && isset($msgMap[$msg])): [$mt, $mm, $mc] = $msgMap[$msg]; ?>
    <div class="alert alert-<?= $mc ?>" style="margin-bottom:1rem">
        <i class="fas fa-<?= $mc === 'success' ? 'circle-check' : 'circle-exclamation' ?>"></i> <?= sanitize($mm) ?>
    </div>
    <?php endif; ?>

    <?php if ($action === 'list'): ?>
    <!-- ════════════ USER LIST ════════════ -->
    <div class="page-header">
        <div>
            <h1 class="page-title"><i class="fas fa-users"></i> Manage Users</h1>
            <p class="page-subtitle"><?= $total ?> total users</p>
        </div>
        <a href="/admin/users/add" class="btn-primary"><i class="fas fa-user-plus"></i> Add User</a>
    </div>

    <!-- Search -->
    <form method="GET" action="/admin/users" class="search-form mb-4">
        <div class="input-icon-wrap" style="max-width:360px">
            <i class="fas fa-search input-prefix-icon"></i>
            <input type="text" name="q" class="form-input pl-input"
                   placeholder="Search by name, email, username..."
                   value="<?= sanitize($search) ?>">
        </div>
        <button type="submit" class="btn-primary">Search</button>
        <?php if ($search): ?>
        <a href="/admin/users" class="btn-ghost">Clear</a>
        <?php endif; ?>
    </form>

    <div class="acard">
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
                <?php if (empty($users)): ?>
                <tr><td colspan="7" class="text-center text-slate-500 py-8">No users found.</td></tr>
                <?php endif; ?>
                <?php foreach ($users as $u): ?>
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
                    <td>
                        <span class="badge badge-<?= $u['role'] === 'admin' ? 'purple' : 'blue' ?>">
                            <?= sanitize(ucfirst($u['role'])) ?>
                        </span>
                    </td>
                    <td>
                        <?php $sc = ['active' => 'green', 'inactive' => 'amber', 'banned' => 'red']; $s = $u['status'] ?? 'inactive'; ?>
                        <span class="badge badge-<?= $sc[$s] ?? 'blue' ?>"><?= sanitize(ucfirst($s)) ?></span>
                    </td>
                    <td class="text-slate-400 text-sm"><?= date('M d, Y', strtotime($u['created_at'])) ?></td>
                    <td>
                        <div class="table-actions">
                            <a href="/admin/users/edit/<?= (int) $u['id'] ?>" class="taction-btn taction-edit" title="Edit">
                                <i class="fas fa-pen"></i>
                            </a>
                            <?php if ((int) $u['id'] !== (int) currentUser()['id']): ?>
                            <form method="POST" action="/admin/users/delete/<?= (int) $u['id'] ?>" style="display:inline"
                                  onsubmit="return confirm('Delete user @<?= sanitize(addslashes($u['username'])) ?>?')">
                                <input type="hidden" name="csrf_token" value="<?= sanitize(csrfToken()) ?>">
                                <button type="submit" class="taction-btn taction-delete" title="Delete">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </form>
                            <?php endif; ?>
                        </div>
                    </td>
                </tr>
                <?php endforeach; ?>
                </tbody>
            </table>
        </div>

        <!-- Pagination -->
        <?php if ($totalPages > 1): ?>
        <div class="pagination">
            <?php for ($p = 1; $p <= $totalPages; $p++): ?>
            <a href="/admin/users?page=<?= $p ?><?= $search ? '&q=' . rawurlencode($search) : '' ?>"
               class="page-btn <?= $p === $page ? 'page-btn-active' : '' ?>"><?= $p ?></a>
            <?php endfor; ?>
        </div>
        <?php endif; ?>
    </div>

    <?php elseif ($action === 'add' || $action === 'edit'): ?>
    <!-- ════════════ ADD / EDIT FORM ════════════ -->
    <div class="page-header">
        <div>
            <a href="/admin/users" class="btn-ghost btn-sm mb-2"><i class="fas fa-arrow-left"></i> Back</a>
            <h1 class="page-title">
                <i class="fas fa-<?= $action === 'add' ? 'user-plus' : 'pen' ?>"></i>
                <?= $action === 'add' ? 'Add New User' : 'Edit User' ?>
            </h1>
        </div>
    </div>

    <?php if ($errors): ?>
    <div class="alert alert-error mb-4">
        <i class="fas fa-circle-exclamation"></i>
        <ul style="margin:0;padding-left:1.2rem">
            <?php foreach ($errors as $e): ?><li><?= sanitize($e) ?></li><?php endforeach; ?>
        </ul>
    </div>
    <?php endif; ?>

    <div class="acard" style="max-width:640px">
        <?php
        $fv = $editUser ?? [];
        // On POST error, restore submitted values
        if (!empty($_POST)) {
            $fv = array_merge($fv, [
                'username'  => $_POST['username']  ?? '',
                'email'     => $_POST['email']     ?? '',
                'full_name' => $_POST['full_name'] ?? '',
                'bio'       => $_POST['bio']       ?? '',
                'role'      => $_POST['role']      ?? 'user',
                'status'    => $_POST['status']    ?? 'active',
            ]);
        }
        $formAction = $action === 'add' ? '/admin/users/add' : '/admin/users/edit/' . (int) $id;
        ?>
        <form method="POST" action="<?= $formAction ?>" class="admin-form" novalidate>
            <input type="hidden" name="csrf_token" value="<?= sanitize(csrfToken()) ?>">

            <div class="form-grid-2">
                <div class="form-group">
                    <label for="full_name" class="form-label">Full Name</label>
                    <input type="text" id="full_name" name="full_name" class="form-input"
                           maxlength="100" value="<?= sanitize($fv['full_name'] ?? '') ?>">
                </div>
                <div class="form-group">
                    <label for="username" class="form-label">
                        Username <?= $action === 'add' ? '<span class="text-red-400">*</span>' : '' ?>
                    </label>
                    <?php if ($action === 'edit'): ?>
                    <input type="text" class="form-input" value="<?= sanitize($fv['username'] ?? '') ?>" disabled>
                    <?php else: ?>
                    <input type="text" id="username" name="username" class="form-input"
                           required maxlength="50" pattern="[a-zA-Z0-9_]+"
                           value="<?= sanitize($fv['username'] ?? '') ?>">
                    <?php endif; ?>
                </div>
            </div>

            <div class="form-group">
                <label for="email" class="form-label">Email <span class="text-red-400">*</span></label>
                <input type="email" id="email" name="email" class="form-input"
                       required maxlength="100" value="<?= sanitize($fv['email'] ?? '') ?>">
            </div>

            <div class="form-group">
                <label for="password" class="form-label">
                    Password
                    <?php if ($action === 'add'): ?><span class="text-red-400">*</span><?php else: ?>
                    <span class="text-slate-500">(leave blank to keep current)</span><?php endif; ?>
                </label>
                <input type="password" id="password" name="password" class="form-input"
                       <?= $action === 'add' ? 'required' : '' ?> minlength="8"
                       placeholder="<?= $action === 'add' ? 'Min. 8 characters' : 'Enter new password to change' ?>">
            </div>

            <div class="form-group">
                <label for="bio" class="form-label">Bio</label>
                <textarea id="bio" name="bio" rows="2" class="form-input" maxlength="500"><?= sanitize($fv['bio'] ?? '') ?></textarea>
            </div>

            <div class="form-grid-2">
                <div class="form-group">
                    <label for="role" class="form-label">Role</label>
                    <select id="role" name="role" class="form-input form-select">
                        <option value="user"  <?= ($fv['role'] ?? 'user') === 'user'  ? 'selected' : '' ?>>User</option>
                        <option value="admin" <?= ($fv['role'] ?? '') === 'admin' ? 'selected' : '' ?>>Admin</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="status" class="form-label">Status</label>
                    <select id="status" name="status" class="form-input form-select">
                        <option value="active"   <?= ($fv['status'] ?? 'active') === 'active'   ? 'selected' : '' ?>>Active</option>
                        <option value="inactive" <?= ($fv['status'] ?? '') === 'inactive' ? 'selected' : '' ?>>Inactive</option>
                        <option value="banned"   <?= ($fv['status'] ?? '') === 'banned'   ? 'selected' : '' ?>>Banned</option>
                    </select>
                </div>
            </div>

            <div class="form-actions">
                <a href="/admin/users" class="btn-ghost">Cancel</a>
                <button type="submit" class="btn-primary">
                    <i class="fas fa-floppy-disk"></i>
                    <?= $action === 'add' ? 'Create User' : 'Save Changes' ?>
                </button>
            </div>
        </form>
    </div>
    <?php endif; ?>
</main>

<?php require_once __DIR__ . '/../includes/footer.php'; ?>
