#!/usr/bin/env php
<?php
/**
 * cron-combo.php — Runs cron-scheduler and outbox-sender sequentially.
 *
 * Use when the hosting plan is limited to 2 cron slots.
 * Pair with cron-runner.php as the second slot.
 *
 * Crontab: * * * * * php /home/u.../public_html/bin/cron-combo.php >> /home/u.../public_html/storage/logs/cron-combo.log 2>&1
 */

declare(strict_types=1);

$php = PHP_BINARY;
$dir = __DIR__;

echo '[' . date('Y-m-d H:i:s') . '] cron-combo: starting cron-scheduler' . PHP_EOL;
passthru("$php $dir/cron-scheduler.php");

echo '[' . date('Y-m-d H:i:s') . '] cron-combo: starting outbox-sender' . PHP_EOL;
passthru("$php $dir/outbox-sender.php");

echo '[' . date('Y-m-d H:i:s') . '] cron-combo: done' . PHP_EOL;
