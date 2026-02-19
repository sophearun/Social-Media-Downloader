<?php
/**
 * Page footer.
 */
?>
<footer class="site-footer">
    <div class="footer-inner">
        <p class="footer-copy">
            &copy; <?= date('Y') ?> <strong><?= sanitize(APP_NAME) ?></strong>.
            Built with <i class="fas fa-heart" style="color:#ef4444"></i> &amp; yt-dlp.
        </p>
        <p class="footer-links">
            <a href="/">Home</a>
            <span aria-hidden="true">&middot;</span>
            <a href="/login">Login</a>
            <span aria-hidden="true">&middot;</span>
            <a href="/register">Register</a>
        </p>
    </div>
</footer>
</body>
</html>
