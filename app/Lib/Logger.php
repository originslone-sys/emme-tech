<?php

declare(strict_types=1);

namespace App\Lib;

/**
 * Logger — simple file-based PSR-3 inspired logger.
 */
class Logger
{
    private static string $logPath = '';

    private static function path(): string
    {
        if (self::$logPath === '') {
            self::$logPath = LOG_PATH;
            $dir = dirname(self::$logPath);
            if (!is_dir($dir)) {
                mkdir($dir, 0775, true);
            }
        }
        return self::$logPath;
    }

    private static function write(string $level, string $message, array $context = []): void
    {
        $timestamp = date('Y-m-d H:i:s');
        $ctx       = empty($context) ? '' : ' ' . json_encode($context, JSON_UNESCAPED_UNICODE);
        $line      = "[$timestamp] [$level] $message$ctx" . PHP_EOL;
        file_put_contents(self::path(), $line, FILE_APPEND | LOCK_EX);
    }

    public static function info(string $message, array $context = []): void
    {
        self::write('INFO', $message, $context);
    }

    public static function debug(string $message, array $context = []): void
    {
        if (APP_DEBUG) {
            self::write('DEBUG', $message, $context);
        }
    }

    public static function warning(string $message, array $context = []): void
    {
        self::write('WARNING', $message, $context);
    }

    public static function error(string $message, array $context = []): void
    {
        self::write('ERROR', $message, $context);
    }

    /**
     * Read last N lines of the log file.
     */
    public static function tail(int $lines = 100): string
    {
        $file = self::path();
        if (!file_exists($file)) return '';

        $content = file($file, FILE_IGNORE_NEW_LINES);
        $slice   = array_slice($content ?: [], -$lines);
        return implode("\n", $slice);
    }
}
