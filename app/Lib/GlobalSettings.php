<?php

declare(strict_types=1);

namespace App\Lib;

use App\Core\DB;

/**
 * GlobalSettings — acesso simplificado à tabela global_settings.
 */
class GlobalSettings
{
    private static array $cache = [];

    /**
     * Obtém o valor de uma configuração global.
     */
    public static function get(string $key, string $default = ''): string
    {
        if (!isset(self::$cache[$key])) {
            $row = DB::fetchOne('SELECT value FROM global_settings WHERE `key` = ?', [$key]);
            self::$cache[$key] = $row ? (string)($row['value'] ?? '') : $default;
        }
        return self::$cache[$key] !== '' ? self::$cache[$key] : $default;
    }

    /**
     * Define o valor de uma configuração global.
     */
    public static function set(string $key, string $value): void
    {
        DB::query(
            'INSERT INTO global_settings (`key`, `value`) VALUES (?, ?)
             ON DUPLICATE KEY UPDATE `value` = VALUES(`value`)',
            [$key, $value]
        );
        self::$cache[$key] = $value;
    }

    /**
     * Retorna todas as configurações como array associativo key => value.
     */
    public static function all(): array
    {
        $rows = DB::fetchAll('SELECT `key`, `value`, `description` FROM global_settings ORDER BY `key`');
        $result = [];
        foreach ($rows as $row) {
            $result[$row['key']] = [
                'value'       => $row['value'] ?? '',
                'description' => $row['description'] ?? '',
            ];
        }
        return $result;
    }

    /**
     * Limpa o cache em memória (útil após atualizar configurações).
     */
    public static function clearCache(): void
    {
        self::$cache = [];
    }
}
