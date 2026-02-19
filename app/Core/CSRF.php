<?php

declare(strict_types=1);

namespace App\Core;

/**
 * CSRF — token generation and verification.
 */
class CSRF
{
    private const KEY = '_csrf_token';

    public static function token(): string
    {
        Session::start();
        if (!Session::has(self::KEY)) {
            Session::set(self::KEY, bin2hex(random_bytes(32)));
        }
        return Session::get(self::KEY);
    }

    public static function field(): string
    {
        $token = self::token();
        return '<input type="hidden" name="_csrf" value="' . htmlspecialchars($token, ENT_QUOTES) . '">';
    }

    public static function verify(string $token): bool
    {
        $stored = Session::get(self::KEY, '');
        return hash_equals($stored, $token);
    }

    /**
     * Verify from request and die with 403 if invalid.
     */
    public static function verifyRequest(): void
    {
        $token = $_POST['_csrf'] ?? $_SERVER['HTTP_X_CSRF_TOKEN'] ?? '';
        if (!self::verify($token)) {
            http_response_code(403);
            die('CSRF token mismatch.');
        }
    }
}
