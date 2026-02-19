<?php

declare(strict_types=1);

namespace App\Core;

/**
 * Response — HTTP response helpers.
 */
class Response
{
    public static function redirect(string $url, int $code = 302): never
    {
        header("Location: $url", true, $code);
        exit;
    }

    public static function json(mixed $data, int $code = 200): never
    {
        http_response_code($code);
        header('Content-Type: application/json; charset=utf-8');
        echo json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
        exit;
    }

    public static function text(string $body, int $code = 200): never
    {
        http_response_code($code);
        header('Content-Type: text/plain; charset=utf-8');
        echo $body;
        exit;
    }

    public static function abort(int $code = 404, string $message = 'Not Found'): never
    {
        http_response_code($code);
        echo "<h1>$code — $message</h1>";
        exit;
    }

    public static function view(string $template, array $data = []): void
    {
        extract($data, EXTR_SKIP);
        $file = APP_ROOT . '/app/Views/' . ltrim($template, '/') . '.php';
        if (!file_exists($file)) {
            self::abort(500, "View not found: $template");
        }
        require $file;
    }

    public static function back(string $fallback = '/'): never
    {
        $ref = $_SERVER['HTTP_REFERER'] ?? $fallback;
        self::redirect($ref);
    }
}
