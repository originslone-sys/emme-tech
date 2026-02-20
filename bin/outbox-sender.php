#!/usr/bin/env php
<?php
/**
 * outbox-sender.php — Envia mensagens pendentes da tabela outbox.
 * Suporta WhatsApp Cloud API e WhatsApp Web (Evolution API).
 *
 * Crontab: * * * * * php /var/www/emme-tech/bin/outbox-sender.php
 */

declare(strict_types=1);

define('APP_ROOT', dirname(__DIR__));
require APP_ROOT . '/app/Config/config.php';

use App\Core\DB;
use App\Lib\Crypto;
use App\Lib\EvolutionAPI;
use App\Lib\Logger;
use App\Lib\WhatsApp;

spl_autoload_register(function (string $class): void {
    $path = str_replace('\\', '/', $class);
    $file = APP_ROOT . '/app/' . substr($path, 4) . '.php';
    if (file_exists($file)) require_once $file;
});

$maxSend     = 50;
$maxAttempts = 3;
$sent        = 0;
$failed      = 0;

Logger::info('outbox-sender: starting');

$lockFile = STORAGE_PATH . '/cache/outbox-sender.lock';
if (file_exists($lockFile) && (time() - filemtime($lockFile)) < 120) {
    exit(0);
}
touch($lockFile);

$items = DB::fetchAll(
    "SELECT o.*,
            a.whatsapp_mode,
            a.whatsapp_phone_number_id,
            a.whatsapp_access_token_encrypted,
            a.evo_instance_name
     FROM outbox o
     JOIN agents a ON a.id = o.agent_id
     WHERE o.status = 'pending'
       AND o.attempts < ?
     ORDER BY o.created_at ASC
     LIMIT ?",
    [$maxAttempts, $maxSend]
);

foreach ($items as $item) {
    $itemId = (int)$item['id'];

    DB::query(
        'UPDATE outbox SET attempts = attempts + 1, last_attempt_at = NOW() WHERE id = ?',
        [$itemId]
    );

    try {
        $mode = $item['whatsapp_mode'] ?? 'cloud_api';

        if ($mode === 'whatsapp_web') {
            // ---- Evolution API ----
            $instanceName = $item['evo_instance_name'] ?? '';
            if (!$instanceName) {
                throw new \RuntimeException("Agent missing Evolution API instance name");
            }

            $evo = EvolutionAPI::fromSettings();
            $evo->sendText($instanceName, $item['phone'], $item['content']);

        } else {
            // ---- WhatsApp Cloud API ----
            $phoneId  = $item['whatsapp_phone_number_id'] ?? '';
            $tokenEnc = $item['whatsapp_access_token_encrypted'] ?? '';

            if (!$phoneId || !$tokenEnc) {
                throw new \RuntimeException("Agent missing WhatsApp Cloud API credentials");
            }

            $token = Crypto::tryDecrypt($tokenEnc);
            if (!$token) {
                throw new \RuntimeException("Cannot decrypt WhatsApp token");
            }

            $wa = new WhatsApp($phoneId, $token);

            if ($item['message_type'] === 'template') {
                $vars = [];
                if ($item['template_vars']) {
                    $decoded = json_decode($item['template_vars'], true);
                    $vars    = is_array($decoded) ? $decoded : [];
                }
                if (!$item['template_name']) {
                    throw new \RuntimeException("Template name is required for template messages");
                }
                $result = $wa->sendTemplate($item['phone'], $item['template_name'], $vars);
            } else {
                $result = $wa->sendText($item['phone'], $item['content']);
            }

            $waMessageId = $result['messages'][0]['id'] ?? null;
            if ($item['message_id'] && $waMessageId) {
                DB::query(
                    'UPDATE messages SET whatsapp_message_id = ? WHERE id = ?',
                    [$waMessageId, $item['message_id']]
                );
            }
        }

        DB::query(
            "UPDATE outbox SET status = 'sent', sent_at = NOW(), error = NULL WHERE id = ?",
            [$itemId]
        );

        if ($item['message_id']) {
            DB::query("UPDATE messages SET status = 'sent' WHERE id = ?", [$item['message_id']]);
        }

        $sent++;
        Logger::info('outbox-sender: sent', [
            'outbox_id' => $itemId,
            'phone'     => $item['phone'],
            'mode'      => $mode,
        ]);
        usleep(100000); // 100ms

    } catch (\Throwable $e) {
        $isFinal = (int)$item['attempts'] + 1 >= $maxAttempts;
        $status  = $isFinal ? 'failed' : 'pending';

        DB::query(
            'UPDATE outbox SET status = ?, error = ? WHERE id = ?',
            [$status, substr($e->getMessage(), 0, 500), $itemId]
        );

        if ($item['message_id']) {
            DB::query("UPDATE messages SET status = 'failed' WHERE id = ?", [$item['message_id']]);
        }

        $failed++;
        Logger::error('outbox-sender: failed to send', [
            'outbox_id' => $itemId,
            'phone'     => $item['phone'],
            'error'     => $e->getMessage(),
        ]);
    }
}

Logger::info("outbox-sender: finished (sent=$sent, failed=$failed)");

if (file_exists($lockFile)) unlink($lockFile);
