<?php
/**
 * Session-based authentication helpers.
 */

if (session_status() === PHP_SESSION_NONE) {
    session_start();
}

function isLoggedIn(): bool {
    return isset($_SESSION['user_id']);
}

function currentUser(): ?array {
    if (!isLoggedIn()) return null;
    return [
        'id'        => $_SESSION['user_id'],
        'username'  => $_SESSION['username']  ?? '',
        'email'     => $_SESSION['email']     ?? '',
        'full_name' => $_SESSION['full_name'] ?? '',
        'avatar'    => $_SESSION['avatar']    ?? '',
        'role'      => $_SESSION['role']      ?? 'user',
    ];
}

function loginUser(array $user): void {
    session_regenerate_id(true);
    $_SESSION['user_id']   = $user['id'];
    $_SESSION['username']  = $user['username'];
    $_SESSION['email']     = $user['email'];
    $_SESSION['full_name'] = $user['full_name'] ?? '';
    $_SESSION['avatar']    = $user['avatar']    ?? '';
    $_SESSION['role']      = $user['role']      ?? 'user';
}

function logoutUser(): void {
    session_unset();
    session_destroy();
}

function requireLogin(string $redirect = '/login'): void {
    if (!isLoggedIn()) {
        $target = urlencode($_SERVER['REQUEST_URI'] ?? '');
        header("Location: {$redirect}?next={$target}");
        exit;
    }
}

function requireAdmin(string $redirect = '/'): void {
    requireLogin();
    if (($_SESSION['role'] ?? '') !== 'admin') {
        header("Location: {$redirect}");
        exit;
    }
}

/** Generate a CSRF token and store it in the session. */
function csrfToken(): string {
    if (empty($_SESSION['csrf_token'])) {
        $_SESSION['csrf_token'] = bin2hex(random_bytes(32));
    }
    return $_SESSION['csrf_token'];
}

/** Verify a submitted CSRF token; die on failure. */
function verifyCsrf(): void {
    $submitted = $_POST['csrf_token'] ?? $_SERVER['HTTP_X_CSRF_TOKEN'] ?? '';
    if (!hash_equals($_SESSION['csrf_token'] ?? '', $submitted)) {
        http_response_code(403);
        die('Invalid CSRF token.');
    }
}
