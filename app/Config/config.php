<?php
/**
 * Config — carrega o .env e define constantes globais.
 */

declare(strict_types=1);

// ----------------------------------------------------------------
// .env loader (sem composer/dotenv)
// ----------------------------------------------------------------
function loadEnv(string $path): void
{
    if (!file_exists($path)) {
        throw new RuntimeException(".env file not found at: $path");
    }
    $lines = file($path, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
    foreach ($lines as $line) {
        $line = trim($line);
        if ($line === '' || str_starts_with($line, '#')) {
            continue;
        }
        if (!str_contains($line, '=')) {
            continue;
        }
        [$key, $value] = explode('=', $line, 2);
        $key   = trim($key);
        $value = trim($value);
        // Remove aspas
        if (
            (str_starts_with($value, '"') && str_ends_with($value, '"')) ||
            (str_starts_with($value, "'") && str_ends_with($value, "'"))
        ) {
            $value = substr($value, 1, -1);
        }
        if (!array_key_exists($key, $_ENV)) {
            $_ENV[$key]    = $value;
            $_SERVER[$key] = $value;
            putenv("$key=$value");
        }
    }
}

// ----------------------------------------------------------------
// Helper: env()
// ----------------------------------------------------------------
function env(string $key, mixed $default = null): mixed
{
    $val = $_ENV[$key] ?? getenv($key);
    if ($val === false) {
        return $default;
    }
    return match (strtolower((string)$val)) {
        'true', '(true)'   => true,
        'false', '(false)' => false,
        'null', '(null)'   => null,
        default            => $val,
    };
}

// ----------------------------------------------------------------
// Carregar .env
// ----------------------------------------------------------------
$envFile = dirname(__DIR__, 2) . '/.env';
loadEnv($envFile);

// ----------------------------------------------------------------
// Timezone
// ----------------------------------------------------------------
date_default_timezone_set(env('APP_TIMEZONE', 'America/Sao_Paulo'));

// ----------------------------------------------------------------
// Error reporting
// ----------------------------------------------------------------
if (env('APP_DEBUG', false)) {
    ini_set('display_errors', '1');
    error_reporting(E_ALL);
} else {
    ini_set('display_errors', '0');
    error_reporting(E_ALL & ~E_NOTICE & ~E_DEPRECATED);
}

// ----------------------------------------------------------------
// Constantes
// ----------------------------------------------------------------
defined('APP_ROOT') || define('APP_ROOT', dirname(__DIR__, 2));
define('APP_URL',     rtrim((string)env('APP_URL', 'http://localhost'), '/'));
define('APP_DEBUG',   (bool)env('APP_DEBUG', false));
define('MASTER_KEY',  (string)env('MASTER_KEY', ''));
define('STORAGE_PATH', (string)env('STORAGE_PATH', APP_ROOT . '/storage'));
define('LOG_PATH',    (string)env('LOG_PATH', STORAGE_PATH . '/logs/app.log'));
define('UPLOAD_DIR',  STORAGE_PATH . '/uploads');
