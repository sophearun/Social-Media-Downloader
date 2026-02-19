<?php
require_once __DIR__ . '/config/app.php';
require_once __DIR__ . '/includes/auth.php';
require_once __DIR__ . '/includes/functions.php';
require_once __DIR__ . '/config/db.php';

if (isLoggedIn()) {
    header('Location: /');
    exit;
}

$errors  = [];
$success = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    verifyCsrf();

    $username  = trim($_POST['username']  ?? '');
    $email     = trim($_POST['email']     ?? '');
    $password  = $_POST['password']       ?? '';
    $password2 = $_POST['password2']      ?? '';
    $full_name = trim($_POST['full_name'] ?? '');

    // Validate
    if ($username === '') {
        $errors[] = 'Username is required.';
    } elseif (!preg_match('/^[a-zA-Z0-9_]{3,50}$/', $username)) {
        $errors[] = 'Username must be 3–50 characters (letters, numbers, underscores).';
    }

    if ($email === '') {
        $errors[] = 'Email is required.';
    } elseif (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
        $errors[] = 'Enter a valid email address.';
    }

    if (strlen($password) < 8) {
        $errors[] = 'Password must be at least 8 characters.';
    } elseif ($password !== $password2) {
        $errors[] = 'Passwords do not match.';
    }

    if (empty($errors)) {
        $pdo = getDB();

        // Check uniqueness
        $stmt = $pdo->prepare('SELECT id FROM users WHERE username = ? OR email = ? LIMIT 1');
        $stmt->execute([$username, $email]);
        if ($stmt->fetch()) {
            $errors[] = 'Username or email is already taken.';
        } else {
            $hash = password_hash($password, PASSWORD_BCRYPT);
            $ins  = $pdo->prepare(
                'INSERT INTO users (username, email, password, full_name, role, status) VALUES (?,?,?,?,?,?)'
            );
            $ins->execute([$username, $email, $hash, $full_name, 'user', 'active']);
            $success = 'Account created! You can now <a href="/login">sign in</a>.';
        }
    }
}

$pageTitle = 'Register';
require_once __DIR__ . '/includes/header.php';
?>

<div class="auth-page">
    <div class="auth-card" style="max-width:440px">
        <div class="auth-logo">
            <div class="auth-logo-icon"><i class="fas fa-user-plus"></i></div>
            <h1 class="auth-title">Create Account</h1>
            <p class="auth-subtitle">Join <?= sanitize(APP_NAME) ?></p>
        </div>

        <?php if ($errors): ?>
        <div class="alert alert-error">
            <i class="fas fa-circle-exclamation"></i>
            <ul style="margin:0;padding-left:1.2rem">
                <?php foreach ($errors as $e): ?>
                <li><?= sanitize($e) ?></li>
                <?php endforeach; ?>
            </ul>
        </div>
        <?php endif; ?>

        <?php if ($success): ?>
        <div class="alert alert-success">
            <i class="fas fa-circle-check"></i> <?= $success /* trusted internal string */ ?>
        </div>
        <?php endif; ?>

        <form method="POST" action="/register" class="auth-form" novalidate>
            <input type="hidden" name="csrf_token" value="<?= sanitize(csrfToken()) ?>">

            <div class="form-group">
                <label for="full_name" class="form-label">Full Name <span class="text-slate-500">(optional)</span></label>
                <div class="input-icon-wrap">
                    <i class="fas fa-id-card input-prefix-icon"></i>
                    <input type="text" id="full_name" name="full_name"
                           class="form-input pl-input"
                           placeholder="Your full name"
                           value="<?= sanitize($_POST['full_name'] ?? '') ?>"
                           maxlength="100">
                </div>
            </div>

            <div class="form-group">
                <label for="username" class="form-label">Username <span class="text-red-400">*</span></label>
                <div class="input-icon-wrap">
                    <i class="fas fa-at input-prefix-icon"></i>
                    <input type="text" id="username" name="username"
                           class="form-input pl-input"
                           placeholder="Choose a username"
                           value="<?= sanitize($_POST['username'] ?? '') ?>"
                           autocomplete="username" required maxlength="50">
                </div>
            </div>

            <div class="form-group">
                <label for="email" class="form-label">Email <span class="text-red-400">*</span></label>
                <div class="input-icon-wrap">
                    <i class="fas fa-envelope input-prefix-icon"></i>
                    <input type="email" id="email" name="email"
                           class="form-input pl-input"
                           placeholder="your@email.com"
                           value="<?= sanitize($_POST['email'] ?? '') ?>"
                           autocomplete="email" required maxlength="100">
                </div>
            </div>

            <div class="form-group">
                <label for="password" class="form-label">Password <span class="text-red-400">*</span></label>
                <div class="input-icon-wrap">
                    <i class="fas fa-lock input-prefix-icon"></i>
                    <input type="password" id="password" name="password"
                           class="form-input pl-input"
                           placeholder="Min. 8 characters"
                           autocomplete="new-password" required minlength="8">
                    <button type="button" class="input-suffix-btn" onclick="togglePwd('password')" tabindex="-1" aria-label="Toggle visibility">
                        <i class="fas fa-eye" id="password-eye"></i>
                    </button>
                </div>
            </div>

            <div class="form-group">
                <label for="password2" class="form-label">Confirm Password <span class="text-red-400">*</span></label>
                <div class="input-icon-wrap">
                    <i class="fas fa-lock input-prefix-icon"></i>
                    <input type="password" id="password2" name="password2"
                           class="form-input pl-input"
                           placeholder="Repeat password"
                           autocomplete="new-password" required minlength="8">
                    <button type="button" class="input-suffix-btn" onclick="togglePwd('password2')" tabindex="-1" aria-label="Toggle visibility">
                        <i class="fas fa-eye" id="password2-eye"></i>
                    </button>
                </div>
            </div>

            <button type="submit" class="btn-primary btn-full">
                <i class="fas fa-user-plus"></i> Create Account
            </button>
        </form>

        <p class="auth-footer-text">
            Already have an account?
            <a href="/login" class="form-link">Sign in</a>
        </p>
    </div>
</div>

<script>
function togglePwd(id) {
    var inp = document.getElementById(id);
    var eye = document.getElementById(id + '-eye');
    if (inp.type === 'password') {
        inp.type = 'text';
        eye.className = 'fas fa-eye-slash';
    } else {
        inp.type = 'password';
        eye.className = 'fas fa-eye';
    }
}
</script>

<?php require_once __DIR__ . '/includes/footer.php'; ?>
