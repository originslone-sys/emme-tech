<?php

declare(strict_types=1);

namespace App\Core;

/**
 * Request — HTTP request helpers.
 */
class Request
{
    public static function method(): string
    {
        return strtoupper($_SERVER['REQUEST_METHOD'] ?? 'GET');
    }

    public static function isPost(): bool
    {
        return self::method() === 'POST';
    }

    public static function isGet(): bool
    {
        return self::method() === 'GET';
    }

    public static function path(): string
    {
        $uri = $_SERVER['REQUEST_URI'] ?? '/';
        $pos = strpos($uri, '?');
        return $pos !== false ? substr($uri, 0, $pos) : $uri;
    }

    public static function get(string $key, mixed $default = null): mixed
    {
        return isset($_GET[$key]) ? self::sanitize($_GET[$key]) : $default;
    }

    public static function post(string $key, mixed $default = null): mixed
    {
        return isset($_POST[$key]) ? self::sanitize($_POST[$key]) : $default;
    }

    public static function input(string $key, mixed $default = null): mixed
    {
        return self::post($key) ?? self::get($key) ?? $default;
    }

    public static function all(): array
    {
        $data = [];
        foreach ($_POST as $k => $v) {
            $data[$k] = self::sanitize($v);
        }
        return $data;
    }

    public static function json(): array
    {
        $raw = file_get_contents('php://input');
        return json_decode($raw ?: '{}', true) ?? [];
    }

    public static function rawBody(): string
    {
        return file_get_contents('php://input') ?: '';
    }

    public static function header(string $name): string
    {
        $key = 'HTTP_' . strtoupper(str_replace('-', '_', $name));
        return $_SERVER[$key] ?? $_SERVER[$name] ?? '';
    }

    public static function ip(): string
    {
        foreach (['HTTP_CF_CONNECTING_IP', 'HTTP_X_FORWARDED_FOR', 'REMOTE_ADDR'] as $k) {
            if (!empty($_SERVER[$k])) {
                return explode(',', $_SERVER[$k])[0];
            }
        }
        return '';
    }

    public static function userAgent(): string
    {
        return $_SERVER['HTTP_USER_AGENT'] ?? '';
    }

    public static function queryParam(string $key, mixed $default = null): mixed
    {
        return self::get($key, $default);
    }

    private static function sanitize(mixed $value): mixed
    {
        if (is_array($value)) {
            return array_map([self::class, 'sanitize'], $value);
        }
        if (is_string($value)) {
            return trim($value);
        }
        return $value;
    }
}
