<?php
/**
 * Responsive top navigation bar.
 * Relies on auth.php being loaded before this file.
 */
$_navUser   = currentUser();
$_navIsAdmin = ($_navUser['role'] ?? '') === 'admin';

// Determine active page for highlighting
$_currentPath = rtrim(parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH), '/') ?: '/';
function _navActive(string $path): string {
    global $_currentPath;
    $normalized = rtrim($path, '/') ?: '/';
    // Exact match for root; prefix match for all others
    if ($normalized === '/') {
        return $_currentPath === '/' ? 'nav-active' : '';
    }
    return (strpos($_currentPath, $normalized) === 0) ? 'nav-active' : '';
}
?>
<nav class="admin-nav" role="navigation" aria-label="Main navigation">
    <div class="nav-inner">
        <!-- Logo -->
        <a href="/" class="nav-logo" aria-label="Home">
            <div class="nav-logo-icon"><i class="fas fa-download"></i></div>
            <span class="nav-logo-text">SoravDL</span>
        </a>

        <!-- Desktop links -->
        <ul class="nav-links" role="list">
            <li><a href="/" class="nav-link <?= _navActive('/index') ?>"><i class="fas fa-house"></i> Home</a></li>
            <?php if ($_navIsAdmin): ?>
            <li><a href="/admin" class="nav-link <?= _navActive('/admin') ?>"><i class="fas fa-shield-halved"></i> Admin</a></li>
            <?php endif; ?>
        </ul>

        <!-- Right side -->
        <div class="nav-right">
            <?php if ($_navUser): ?>
                <a href="/profile" class="nav-user-btn" title="My Profile">
                    <?php if (!empty($_navUser['avatar'])): ?>
                        <img src="<?= sanitize($_navUser['avatar']) ?>" alt="Avatar" class="nav-avatar">
                    <?php else: ?>
                        <img src="<?= sanitize(generateAvatar($_navUser['full_name'] ?: $_navUser['username'])) ?>"
                             alt="Avatar" class="nav-avatar">
                    <?php endif; ?>
                    <span class="nav-username"><?= sanitize($_navUser['username']) ?></span>
                </a>
                <a href="/logout" class="nav-btn nav-btn-ghost" title="Logout">
                    <i class="fas fa-right-from-bracket"></i>
                    <span class="sr-only">Logout</span>
                </a>
            <?php else: ?>
                <a href="/login"    class="nav-btn nav-btn-ghost">Login</a>
                <a href="/register" class="nav-btn nav-btn-primary">Register</a>
            <?php endif; ?>

            <!-- Mobile hamburger -->
            <button class="nav-hamburger" id="navHamburger" aria-label="Toggle menu" aria-expanded="false">
                <i class="fas fa-bars"></i>
            </button>
        </div>
    </div>

    <!-- Mobile menu -->
    <div class="nav-mobile" id="navMobile" hidden>
        <a href="/" class="nav-mobile-link"><i class="fas fa-house"></i> Home</a>
        <?php if ($_navIsAdmin): ?>
        <a href="/admin" class="nav-mobile-link"><i class="fas fa-shield-halved"></i> Admin</a>
        <?php endif; ?>
        <?php if ($_navUser): ?>
        <a href="/profile" class="nav-mobile-link"><i class="fas fa-user"></i> Profile</a>
        <a href="/logout"  class="nav-mobile-link"><i class="fas fa-right-from-bracket"></i> Logout</a>
        <?php else: ?>
        <a href="/login"    class="nav-mobile-link"><i class="fas fa-right-to-bracket"></i> Login</a>
        <a href="/register" class="nav-mobile-link"><i class="fas fa-user-plus"></i> Register</a>
        <?php endif; ?>
    </div>
</nav>

<script>
(function(){
    var btn  = document.getElementById('navHamburger');
    var menu = document.getElementById('navMobile');
    if (btn && menu) {
        btn.addEventListener('click', function(){
            var open = !menu.hidden;
            menu.hidden = open;
            btn.setAttribute('aria-expanded', String(!open));
        });
    }
})();
</script>
