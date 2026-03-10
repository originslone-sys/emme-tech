<?php
session_start();

// Database Configuration
define('DB_HOST', 'localhost');
define('DB_NAME', 'paguecontas_db');
define('DB_USER', 'root');
define('DB_PASS', '');

// App Configuration
define('APP_NAME', 'PagueContas');
define('APP_URL', 'https://seudominio.com/paguecontas');
define('APP_VERSION', '1.0.0');

// Cashback Configuration
define('CASHBACK_PERCENT', 5);

// Currency
define('CURRENCY', 'BRL');
define('CURRENCY_SYMBOL', 'R$');

// PDO Connection
try {
    $pdo = new PDO(
        "mysql:host=" . DB_HOST . ";dbname=" . DB_NAME . ";charset=utf8mb4",
        DB_USER,
        DB_PASS,
        [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            PDO::ATTR_EMULATE_PREPARES => false
        ]
    );
} catch (PDOException $e) {
    die("Erro de conexão: " . $e->getMessage());
}

// Helper Functions
function formatMoney($value) {
    return CURRENCY_SYMBOL . ' ' . number_format($value, 2, ',', '.');
}

function generateToken($length = 32) {
    return bin2hex(random_bytes($length));
}

function sanitize($data) {
    return htmlspecialchars(trim($data), ENT_QUOTES, 'UTF-8');
}

function isLoggedIn() {
    return isset($_SESSION['user_id']);
}

function isAdmin() {
    return isset($_SESSION['is_admin']) && $_SESSION['is_admin'] === true;
}

function redirect($url) {
    header("Location: $url");
    exit;
}

function jsonResponse($data, $code = 200) {
    http_response_code($code);
    header('Content-Type: application/json');
    echo json_encode($data);
    exit;
}
