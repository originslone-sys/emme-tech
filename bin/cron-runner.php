#!/usr/bin/env php
<?php
/**
 * cron-runner.php — Executes pending jobs from the jobs queue.
 * Run every minute via system cron.
 *
 * Crontab: * * * * * php /var/www/emme-tech/bin/cron-runner.php
 */

declare(strict_types=1);

define('APP_ROOT', dirname(__DIR__));
require APP_ROOT . '/app/Config/config.php';

use App\Core\DB;
use App\Lib\Logger;

// Prevent overlapping runs
$lockFile = STORAGE_PATH . '/cache/cron-runner.lock';
if (file_exists($lockFile) && (time() - filemtime($lockFile)) < (int)env('JOB_LOCK_TIMEOUT', 300)) {
    exit(0); // Already running
}
touch($lockFile);

function releaseLock(string $file): void {
    if (file_exists($file)) unlink($file);
}

register_shutdown_function('releaseLock', $lockFile);

spl_autoload_register(function (string $class): void {
    $file = APP_ROOT . '/' . str_replace(['App\\', '\\'], ['app/', '/'], $class) . '.php';
    if (file_exists($file)) require_once $file;
});

$maxJobs    = 20; // Process at most N jobs per run
$maxAttempts = (int)env('JOB_MAX_ATTEMPTS', 3);
$retryDelay  = (int)env('JOB_RETRY_DELAY_SECONDS', 60);
$processed  = 0;

Logger::info('cron-runner: starting');

while ($processed < $maxJobs) {
    // Pick one pending job with FOR UPDATE to prevent concurrent processing
    DB::beginTransaction();
    try {
        $job = DB::fetchOne(
            "SELECT * FROM jobs
             WHERE status = 'pending'
               AND attempts < max_attempts
               AND run_at <= NOW()
             ORDER BY id ASC
             LIMIT 1
             FOR UPDATE SKIP LOCKED"
        );

        if (!$job) {
            DB::commit();
            break;
        }

        // Mark as processing
        DB::query(
            "UPDATE jobs SET status = 'processing', started_at = NOW(), attempts = attempts + 1 WHERE id = ?",
            [$job['id']]
        );

        DB::commit();
    } catch (\Throwable $e) {
        DB::rollBack();
        Logger::error('cron-runner: failed to lock job', ['error' => $e->getMessage()]);
        break;
    }

    $payload = json_decode($job['payload'], true) ?? [];
    $jobClass = 'App\\Jobs\\' . $job['job_class'];

    try {
        if (!class_exists($jobClass)) {
            throw new \RuntimeException("Job class not found: $jobClass");
        }

        $handler = new $jobClass();
        $handler->handle($payload);

        DB::query(
            "UPDATE jobs SET status = 'done', finished_at = NOW(), error = NULL WHERE id = ?",
            [$job['id']]
        );

        Logger::info('cron-runner: job done', ['id' => $job['id'], 'class' => $job['job_class']]);
    } catch (\Throwable $e) {
        $nextAttempt = $job['attempts'] >= $maxAttempts - 1 ? 'failed' : 'pending';
        $runAt       = date('Y-m-d H:i:s', time() + $retryDelay * (int)pow(2, $job['attempts']));

        DB::query(
            "UPDATE jobs SET status = ?, error = ?, finished_at = NOW(), run_at = ? WHERE id = ?",
            [$nextAttempt, substr($e->getMessage(), 0, 1000), $runAt, $job['id']]
        );

        Logger::error('cron-runner: job failed', [
            'id'    => $job['id'],
            'class' => $job['job_class'],
            'error' => $e->getMessage(),
        ]);
    }

    $processed++;
}

Logger::info("cron-runner: finished ($processed jobs processed)");
releaseLock($lockFile);
