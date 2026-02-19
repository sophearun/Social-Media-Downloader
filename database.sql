-- Social Media Downloader — Database Schema
-- Run: mysql -u root -p < database.sql

CREATE DATABASE IF NOT EXISTS social_downloader
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE social_downloader;

-- ─────────────────────────────────────────────
--  Users
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    username   VARCHAR(50)  NOT NULL UNIQUE,
    email      VARCHAR(100) NOT NULL UNIQUE,
    password   VARCHAR(255) NOT NULL,
    full_name  VARCHAR(100) DEFAULT '',
    bio        TEXT         DEFAULT '',
    avatar     VARCHAR(255) DEFAULT '',
    role       ENUM('admin','user')                    DEFAULT 'user',
    status     ENUM('active','inactive','banned')      DEFAULT 'active',
    created_at DATETIME     DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Default admin — password: password
INSERT INTO users (username, email, password, full_name, role) VALUES
('admin', 'admin@example.com',
 '$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi',
 'Administrator', 'admin')
ON DUPLICATE KEY UPDATE id = id;

-- ─────────────────────────────────────────────
--  Download History
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS download_history (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    user_id       INT,
    url           VARCHAR(500) NOT NULL,
    platform      VARCHAR(50),
    title         VARCHAR(300),
    filename      VARCHAR(300),
    downloaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
