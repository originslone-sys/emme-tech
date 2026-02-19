<?php

declare(strict_types=1);

namespace App\Lib;

use RuntimeException;

/**
 * Crypto — AES-256-GCM encrypt/decrypt for sensitive tokens.
 */
class Crypto
{
    private const CIPHER = 'aes-256-gcm';
    private const TAG_LEN = 16;

    private static function masterKey(): string
    {
        $hex = MASTER_KEY;
        if (strlen($hex) !== 64) {
            throw new RuntimeException('MASTER_KEY must be 64 hex characters (32 bytes).');
        }
        return hex2bin($hex);
    }

    public static function encrypt(string $plaintext): string
    {
        $key    = self::masterKey();
        $iv     = random_bytes(12); // 96-bit nonce for GCM
        $tag    = '';
        $cipher = openssl_encrypt($plaintext, self::CIPHER, $key, OPENSSL_RAW_DATA, $iv, $tag, '', self::TAG_LEN);

        if ($cipher === false) {
            throw new RuntimeException('Encryption failed.');
        }

        // Format: base64(iv + tag + ciphertext)
        return base64_encode($iv . $tag . $cipher);
    }

    public static function decrypt(string $encoded): string
    {
        $key  = self::masterKey();
        $data = base64_decode($encoded, true);

        if ($data === false || strlen($data) < 12 + self::TAG_LEN + 1) {
            throw new RuntimeException('Invalid encrypted data.');
        }

        $iv         = substr($data, 0, 12);
        $tag        = substr($data, 12, self::TAG_LEN);
        $ciphertext = substr($data, 12 + self::TAG_LEN);

        $plain = openssl_decrypt($ciphertext, self::CIPHER, $key, OPENSSL_RAW_DATA, $iv, $tag);

        if ($plain === false) {
            throw new RuntimeException('Decryption failed — data may be tampered or key wrong.');
        }

        return $plain;
    }

    /**
     * Safely decrypt — returns null on failure instead of throwing.
     */
    public static function tryDecrypt(string $encoded): ?string
    {
        try {
            return self::decrypt($encoded);
        } catch (\Throwable) {
            return null;
        }
    }
}
