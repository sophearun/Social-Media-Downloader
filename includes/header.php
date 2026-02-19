<?php
/**
 * HTML <head> + session bootstrap.
 * Usage: require_once __DIR__.'/../includes/header.php';
 * Variables accepted from caller:
 *   $pageTitle  - overrides default title
 *   $bodyClass  - extra class(es) on <body>
 */

require_once __DIR__ . '/../config/app.php';
require_once __DIR__ . '/../includes/auth.php';
require_once __DIR__ . '/../includes/functions.php';

$pageTitle = $pageTitle ?? APP_NAME;
$bodyClass = $bodyClass ?? '';
?>
<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="theme-color" content="#030712">
    <title><?= sanitize($pageTitle) ?> — <?= sanitize(APP_NAME) ?></title>

    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
    tailwind.config = {
        darkMode: 'class',
        theme: {
            extend: {
                colors: {
                    primary:  { DEFAULT: '#8b5cf6', hover: '#a78bfa', dark: '#7c3aed' },
                    accent:   { DEFAULT: '#22d3ee', hover: '#67e8f9' },
                    surface:  { DEFAULT: '#0f172a', card: '#1e293b', input: '#0f172a' },
                },
                fontFamily: {
                    sans:    ['Inter', 'system-ui', 'sans-serif'],
                    display: ['Koulen', 'sans-serif'],
                },
            }
        }
    }
    </script>

    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Koulen&display=swap" rel="stylesheet">

    <!-- Font Awesome -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">

    <!-- Admin / shared CSS -->
    <link rel="stylesheet" href="<?= APP_URL ?>/assets/css/admin.css">

    <style>
        body { background: #030712; color: #f1f5f9; font-family: 'Inter', sans-serif; }
    </style>
</head>
<body class="min-h-screen <?= sanitize($bodyClass) ?>">
<div class="bg-animation" aria-hidden="true">
    <div class="bg-circle c1"></div>
    <div class="bg-circle c2"></div>
    <div class="bg-circle c3"></div>
</div>
