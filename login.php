<?php
require_once __DIR__ . '/config/app.php';
require_once __DIR__ . '/includes/auth.php';
require_once __DIR__ . '/includes/functions.php';
require_once __DIR__ . '/config/db.php';

// Already logged in
if (isLoggedIn()) {
    header('Location: /');
    exit;
}

$error   = '';
$success = '';
$next    = preg_replace('/[^a-zA-Z0-9\/_\-?=&%]/', '', $_GET['next'] ?? '/');

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    verifyCsrf();

    $username = trim($_POST['username'] ?? '');
    $password = $_POST['password']      ?? '';

    if ($username === '' || $password === '') {
        $error = 'Please enter both username and password.';
    } else {
        $pdo  = getDB();
        $stmt = $pdo->prepare('SELECT * FROM users WHERE (username = ? OR email = ?) AND status = "active" LIMIT 1');
        $stmt->execute([$username, $username]);
        $user = $stmt->fetch();

        if ($user && password_verify($password, $user['password'])) {
            loginUser($user);
            header('Location: ' . ($next ?: '/'));
            exit;
        } else {
            $error = 'Invalid credentials. Please try again.';
        }
    }
}

$pageTitle = 'Login';
require_once __DIR__ . '/includes/header.php';
?>

<div class="auth-page">
    <div class="auth-card">
        <div class="auth-logo">
            <div class="auth-logo-icon"><i class="fas fa-download"></i></div>
            <h1 class="auth-title"><?= sanitize(APP_NAME) ?></h1>
            <p class="auth-subtitle">Sign in to your account</p>
        </div>

        <?php if ($error): ?>
        <div class="alert alert-error">
            <i class="fas fa-circle-exclamation"></i> <?= sanitize($error) ?>
        </div>
        <?php endif; ?>

        <form method="POST" action="/login<?= $next ? '?next=' . rawurlencode($next) : '' ?>" class="auth-form" novalidate>
            <input type="hidden" name="csrf_token" value="<?= sanitize(csrfToken()) ?>">

            <div class="form-group">
                <label for="username" class="form-label">Username or Email</label>
                <div class="input-icon-wrap">
                    <i class="fas fa-user input-prefix-icon"></i>
                    <input type="text" id="username" name="username"
                           class="form-input pl-input"
                           placeholder="Enter username or email"
                           value="<?= sanitize($_POST['username'] ?? '') ?>"
                           autocomplete="username" required>
                </div>
            </div>

            <div class="form-group">
                <label for="password" class="form-label">Password</label>
                <div class="input-icon-wrap">
                    <i class="fas fa-lock input-prefix-icon"></i>
                    <input type="password" id="password" name="password"
                           class="form-input pl-input"
                           placeholder="Enter password"
                           autocomplete="current-password" required>
                    <button type="button" class="input-suffix-btn" onclick="togglePwd('password')" tabindex="-1" aria-label="Toggle password visibility">
                        <i class="fas fa-eye" id="password-eye"></i>
                    </button>
                </div>
            </div>

            <div class="form-row-split">
                <label class="checkbox-label">
                    <input type="checkbox" name="remember" class="checkbox">
                    <span>Remember me</span>
                </label>
                <a href="#" class="form-link">Forgot password?</a>
            </div>

            <button type="submit" class="btn-primary btn-full">
                <i class="fas fa-right-to-bracket"></i> Sign In
            </button>
        </form>

        <p class="auth-footer-text">
            Don't have an account?
            <a href="/register" class="form-link">Create one</a>
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
