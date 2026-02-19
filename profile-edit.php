<?php
require_once __DIR__ . '/config/app.php';
require_once __DIR__ . '/includes/auth.php';
require_once __DIR__ . '/includes/functions.php';
require_once __DIR__ . '/config/db.php';

requireLogin();

$user   = currentUser();
$pdo    = getDB();
$errors = [];
$success = '';

// Fetch fresh record
$stmt = $pdo->prepare('SELECT * FROM users WHERE id = ? LIMIT 1');
$stmt->execute([$user['id']]);
$dbUser = $stmt->fetch();

if (!$dbUser) {
    logoutUser();
    header('Location: /login');
    exit;
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    verifyCsrf();

    $full_name = trim($_POST['full_name'] ?? '');
    $email     = trim($_POST['email']     ?? '');
    $bio       = trim($_POST['bio']       ?? '');
    $newPwd    = $_POST['new_password']      ?? '';
    $curPwd    = $_POST['current_password']  ?? '';
    $cfmPwd    = $_POST['confirm_password']  ?? '';

    // Validate
    if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
        $errors[] = 'Enter a valid email address.';
    }

    // Check email uniqueness (excluding self)
    if (empty($errors)) {
        $chk = $pdo->prepare('SELECT id FROM users WHERE email = ? AND id != ? LIMIT 1');
        $chk->execute([$email, $user['id']]);
        if ($chk->fetch()) {
            $errors[] = 'That email is already used by another account.';
        }
    }

    // Password change (optional)
    $newHash = null;
    if ($newPwd !== '') {
        if (!password_verify($curPwd, $dbUser['password'])) {
            $errors[] = 'Current password is incorrect.';
        } elseif (strlen($newPwd) < 8) {
            $errors[] = 'New password must be at least 8 characters.';
        } elseif ($newPwd !== $cfmPwd) {
            $errors[] = 'New passwords do not match.';
        } else {
            $newHash = password_hash($newPwd, PASSWORD_BCRYPT);
        }
    }

    // Avatar upload
    $avatarPath = $dbUser['avatar'];
    if (isset($_FILES['avatar']) && $_FILES['avatar']['error'] === UPLOAD_ERR_OK) {
        $finfo    = new finfo(FILEINFO_MIME_TYPE);
        $allowed  = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
        $mime     = $finfo->file($_FILES['avatar']['tmp_name']);
        if (!in_array($mime, $allowed, true)) {
            $errors[] = 'Avatar must be a JPEG, PNG, GIF or WebP image.';
        } elseif ($_FILES['avatar']['size'] > 2 * 1024 * 1024) {
            $errors[] = 'Avatar must be under 2 MB.';
        } else {
            if (!is_dir(AVATAR_DIR)) mkdir(AVATAR_DIR, 0750, true);
            $ext        = pathinfo($_FILES['avatar']['name'], PATHINFO_EXTENSION);
            $newName    = 'avatar_' . $user['id'] . '_' . time() . '.' . $ext;
            $destPath   = AVATAR_DIR . $newName;
            if (move_uploaded_file($_FILES['avatar']['tmp_name'], $destPath)) {
                $avatarPath = '/uploads/avatars/' . $newName;
            } else {
                $errors[] = 'Failed to upload avatar.';
            }
        }
    }

    if (empty($errors)) {
        if ($newHash) {
            $upd = $pdo->prepare(
                'UPDATE users SET full_name=?, email=?, bio=?, avatar=?, password=? WHERE id=?'
            );
            $upd->execute([$full_name, $email, $bio, $avatarPath, $newHash, $user['id']]);
        } else {
            $upd = $pdo->prepare(
                'UPDATE users SET full_name=?, email=?, bio=?, avatar=? WHERE id=?'
            );
            $upd->execute([$full_name, $email, $bio, $avatarPath, $user['id']]);
        }

        // Refresh session
        $stmt2 = $pdo->prepare('SELECT * FROM users WHERE id = ? LIMIT 1');
        $stmt2->execute([$user['id']]);
        loginUser($stmt2->fetch());

        $success = 'Profile updated successfully.';
        // Refresh local var
        $dbUser['full_name'] = $full_name;
        $dbUser['email']     = $email;
        $dbUser['bio']       = $bio;
        $dbUser['avatar']    = $avatarPath;
    }
}

$pageTitle = 'Edit Profile';
require_once __DIR__ . '/includes/header.php';
require_once __DIR__ . '/includes/nav.php';
?>

<main class="admin-main" style="max-width:680px;margin:0 auto">
    <div class="acard-header mb-4" style="padding:0">
        <div>
            <a href="/profile" class="btn-ghost btn-sm"><i class="fas fa-arrow-left"></i> Back to Profile</a>
        </div>
    </div>

    <div class="acard">
        <div class="acard-header">
            <h1 class="acard-title"><i class="fas fa-pen"></i> Edit Profile</h1>
        </div>

        <?php if ($errors): ?>
        <div class="alert alert-error">
            <i class="fas fa-circle-exclamation"></i>
            <ul style="margin:0;padding-left:1.2rem">
                <?php foreach ($errors as $e): ?><li><?= sanitize($e) ?></li><?php endforeach; ?>
            </ul>
        </div>
        <?php endif; ?>

        <?php if ($success): ?>
        <div class="alert alert-success"><i class="fas fa-circle-check"></i> <?= sanitize($success) ?></div>
        <?php endif; ?>

        <form method="POST" action="/profile/edit" enctype="multipart/form-data" class="admin-form" novalidate>
            <input type="hidden" name="csrf_token" value="<?= sanitize(csrfToken()) ?>">

            <!-- Avatar -->
            <div class="form-group avatar-upload-group">
                <label class="form-label">Profile Photo</label>
                <div class="avatar-preview-wrap">
                    <?php
                    $previewSrc = !empty($dbUser['avatar'])
                        ? sanitize($dbUser['avatar'])
                        : sanitize(generateAvatar($dbUser['full_name'] ?: $dbUser['username'], 80));
                    ?>
                    <img src="<?= $previewSrc ?>" alt="Avatar" class="avatar-preview" id="avatarPreview">
                    <label for="avatar" class="avatar-upload-btn">
                        <i class="fas fa-camera"></i> Change Photo
                        <input type="file" id="avatar" name="avatar" accept="image/*" class="sr-only"
                               onchange="previewAvatar(this)">
                    </label>
                </div>
                <p class="form-hint">JPEG, PNG, GIF or WebP · Max 2 MB</p>
            </div>

            <div class="form-grid-2">
                <div class="form-group">
                    <label for="full_name" class="form-label">Full Name</label>
                    <input type="text" id="full_name" name="full_name"
                           class="form-input" maxlength="100"
                           value="<?= sanitize($dbUser['full_name'] ?? '') ?>">
                </div>
                <div class="form-group">
                    <label class="form-label">Username</label>
                    <input type="text" class="form-input" value="<?= sanitize($dbUser['username']) ?>" disabled>
                    <p class="form-hint">Username cannot be changed.</p>
                </div>
            </div>

            <div class="form-group">
                <label for="email" class="form-label">Email <span class="text-red-400">*</span></label>
                <input type="email" id="email" name="email"
                       class="form-input" maxlength="100" required
                       value="<?= sanitize($dbUser['email'] ?? '') ?>">
            </div>

            <div class="form-group">
                <label for="bio" class="form-label">Bio</label>
                <textarea id="bio" name="bio" rows="3" class="form-input" maxlength="500"
                          placeholder="Tell something about yourself..."><?= sanitize($dbUser['bio'] ?? '') ?></textarea>
            </div>

            <hr class="form-divider">
            <h3 class="form-section-title"><i class="fas fa-lock"></i> Change Password</h3>
            <p class="form-hint mb-3">Leave blank to keep your current password.</p>

            <div class="form-group">
                <label for="current_password" class="form-label">Current Password</label>
                <div class="input-icon-wrap">
                    <i class="fas fa-lock input-prefix-icon"></i>
                    <input type="password" id="current_password" name="current_password"
                           class="form-input pl-input" autocomplete="current-password">
                </div>
            </div>

            <div class="form-grid-2">
                <div class="form-group">
                    <label for="new_password" class="form-label">New Password</label>
                    <input type="password" id="new_password" name="new_password"
                           class="form-input" minlength="8" autocomplete="new-password"
                           placeholder="Min. 8 characters">
                </div>
                <div class="form-group">
                    <label for="confirm_password" class="form-label">Confirm New Password</label>
                    <input type="password" id="confirm_password" name="confirm_password"
                           class="form-input" autocomplete="new-password">
                </div>
            </div>

            <div class="form-actions">
                <a href="/profile" class="btn-ghost">Cancel</a>
                <button type="submit" class="btn-primary">
                    <i class="fas fa-floppy-disk"></i> Save Changes
                </button>
            </div>
        </form>
    </div>
</main>

<script>
function previewAvatar(input) {
    if (input.files && input.files[0]) {
        var reader = new FileReader();
        reader.onload = function(e) {
            document.getElementById('avatarPreview').src = e.target.result;
        };
        reader.readAsDataURL(input.files[0]);
    }
}
</script>

<?php require_once __DIR__ . '/includes/footer.php'; ?>
