<?php

declare(strict_types=1);

namespace App\Controllers\Webhook;

use App\Core\DB;
use App\Core\Response;
use App\Lib\Logger;
use App\Lib\WhatsApp;

class WhatsAppController
{
    /**
     * GET /webhook/whatsapp — Webhook verification.
     */
    public function verify(): void
    {
        $mode      = $_GET['hub_mode']         ?? '';
        $token     = $_GET['hub_verify_token'] ?? '';
        $challenge = $_GET['hub_challenge']    ?? '';

        $configToken = (string)env('WA_VERIFY_TOKEN', '');

        if ($mode === 'subscribe' && $token === $configToken) {
            Logger::info('WhatsApp webhook verified');
            echo $challenge;
            exit;
        }

        http_response_code(403);
        echo 'Forbidden';
        exit;
    }

    /**
     * POST /webhook/whatsapp — Incoming events.
     */
    public function receive(): void
    {
        $rawBody  = file_get_contents('php://input') ?: '';
        $signature = $_SERVER['HTTP_X_HUB_SIGNATURE_256'] ?? '';
        $appSecret = (string)env('WA_APP_SECRET', '');

        // Validate signature if app secret is configured
        if ($appSecret && !WhatsApp::verifySignature($rawBody, $signature, $appSecret)) {
            Logger::warning('WhatsApp webhook signature mismatch', ['sig' => $signature]);
            http_response_code(401);
            echo 'Signature mismatch';
            exit;
        }

        $payload = json_decode($rawBody, true);
        if (!$payload) {
            http_response_code(400);
            echo 'Bad request';
            exit;
        }

        // Always respond 200 immediately
        http_response_code(200);
        echo 'OK';

        // Process asynchronously via jobs
        try {
            $this->processPayload($payload);
        } catch (\Throwable $e) {
            Logger::error('WhatsApp webhook processing error', ['error' => $e->getMessage()]);
        }

        // Make sure output is flushed before heavy processing
        if (function_exists('fastcgi_finish_request')) {
            fastcgi_finish_request();
        }
    }

    private function processPayload(array $payload): void
    {
        $entries = $payload['entry'] ?? [];

        foreach ($entries as $entry) {
            $changes = $entry['changes'] ?? [];

            foreach ($changes as $change) {
                $value = $change['value'] ?? [];

                // Handle messages
                $messages = $value['messages'] ?? [];
                foreach ($messages as $msg) {
                    $this->handleInboundMessage($value, $msg);
                }

                // Handle status updates
                $statuses = $value['statuses'] ?? [];
                foreach ($statuses as $status) {
                    $this->handleStatusUpdate($status);
                }
            }
        }
    }

    private function handleInboundMessage(array $value, array $msg): void
    {
        $phoneNumberId = $value['metadata']['phone_number_id'] ?? '';
        $msgId         = $msg['id'] ?? '';
        $from          = $msg['from'] ?? '';
        $type          = $msg['type'] ?? 'text';
        $timestamp     = $msg['timestamp'] ?? time();

        if (!$phoneNumberId || !$from || !$msgId) {
            Logger::warning('WhatsApp message missing required fields', compact('phoneNumberId', 'from', 'msgId'));
            return;
        }

        // Extract text content
        $content = match ($type) {
            'text'     => $msg['text']['body'] ?? '',
            'image'    => '[Imagem recebida]' . ($msg['image']['caption'] ?? ''),
            'audio'    => '[Áudio recebido]',
            'video'    => '[Vídeo recebido]',
            'document' => '[Documento: ' . ($msg['document']['filename'] ?? 'arquivo') . ']',
            'location' => '[Localização recebida]',
            default    => '[Tipo de mensagem: ' . $type . ']',
        };

        // Dedupe key
        $dedupeKey = 'wa_in_' . $msgId;

        // Check duplicate
        $exists = DB::fetchColumn('SELECT id FROM messages WHERE dedupe_key = ?', [$dedupeKey]);
        if ($exists) {
            Logger::debug('WhatsApp message already processed', ['msg_id' => $msgId]);
            return;
        }

        // Find agent by phone_number_id
        $agent = DB::fetchOne(
            'SELECT a.*, t.status AS tenant_status
             FROM agents a
             JOIN tenants t ON t.id = a.tenant_id
             WHERE a.whatsapp_phone_number_id = ? AND a.status = ? LIMIT 1',
            [$phoneNumberId, 'active']
        );

        if (!$agent) {
            Logger::warning('No active agent found for phone_number_id', ['phone_number_id' => $phoneNumberId]);
            return;
        }

        if ($agent['tenant_status'] !== 'active' && $agent['tenant_status'] !== 'trial') {
            Logger::warning('Tenant not active, ignoring message', ['tenant_id' => $agent['tenant_id']]);
            return;
        }

        $tenantId = (int)$agent['tenant_id'];
        $agentId  = (int)$agent['id'];

        DB::beginTransaction();
        try {
            // Upsert contact
            $contact = DB::fetchOne(
                'SELECT * FROM contacts WHERE agent_id = ? AND phone = ? FOR UPDATE',
                [$agentId, $from]
            );

            if (!$contact) {
                $contactId = DB::insert('contacts', [
                    'tenant_id'       => $tenantId,
                    'agent_id'        => $agentId,
                    'phone'           => $from,
                    'name'            => $value['contacts'][0]['profile']['name'] ?? null,
                    'last_inbound_at' => date('Y-m-d H:i:s', (int)$timestamp),
                ]);
            } else {
                $contactId = (int)$contact['id'];
                DB::update('contacts', [
                    'last_inbound_at' => date('Y-m-d H:i:s', (int)$timestamp),
                ], ['id' => $contactId]);
            }

            // Get or create thread
            $thread = DB::fetchOne(
                "SELECT * FROM threads WHERE agent_id = ? AND contact_id = ? AND status = 'open' ORDER BY id DESC LIMIT 1 FOR UPDATE",
                [$agentId, $contactId]
            );

            if (!$thread) {
                $threadId = DB::insert('threads', [
                    'tenant_id'  => $tenantId,
                    'agent_id'   => $agentId,
                    'contact_id' => $contactId,
                    'status'     => 'open',
                    'started_at' => date('Y-m-d H:i:s'),
                ]);
            } else {
                $threadId = (int)$thread['id'];
            }

            // Save message
            $messageId = DB::insert('messages', [
                'tenant_id'           => $tenantId,
                'agent_id'            => $agentId,
                'thread_id'           => $threadId,
                'contact_id'          => $contactId,
                'direction'           => 'inbound',
                'content'             => $content,
                'message_type'        => $type,
                'whatsapp_message_id' => $msgId,
                'dedupe_key'          => $dedupeKey,
                'status'              => 'received',
            ]);

            // Update thread last_message_at
            DB::update('threads', ['last_message_at' => date('Y-m-d H:i:s')], ['id' => $threadId]);

            // Enqueue processing job
            DB::insert('jobs', [
                'tenant_id' => $tenantId,
                'queue'     => 'inbound',
                'job_class' => 'ProcessInbound',
                'payload'   => json_encode([
                    'message_id' => $messageId,
                    'thread_id'  => $threadId,
                    'contact_id' => $contactId,
                    'agent_id'   => $agentId,
                    'tenant_id'  => $tenantId,
                    'content'    => $content,
                    'type'       => $type,
                ]),
                'status'       => 'pending',
                'max_attempts' => 3,
                'run_at'       => date('Y-m-d H:i:s'),
            ]);

            DB::commit();

            Logger::info('WhatsApp inbound processed', [
                'msg_id'    => $msgId,
                'agent_id'  => $agentId,
                'thread_id' => $threadId,
            ]);
        } catch (\Throwable $e) {
            DB::rollBack();
            Logger::error('WhatsApp inbound transaction failed', ['error' => $e->getMessage(), 'msg_id' => $msgId]);
        }
    }

    private function handleStatusUpdate(array $status): void
    {
        $waId      = $status['id']     ?? '';
        $newStatus = $status['status'] ?? '';

        if (!$waId || !$newStatus) return;

        $statusMap = [
            'sent'      => 'sent',
            'delivered' => 'delivered',
            'read'      => 'read',
            'failed'    => 'failed',
        ];

        $dbStatus = $statusMap[$newStatus] ?? null;
        if (!$dbStatus) return;

        DB::query(
            'UPDATE messages SET status = ? WHERE whatsapp_message_id = ?',
            [$dbStatus, $waId]
        );

        if ($dbStatus === 'sent') {
            DB::query(
                'UPDATE outbox SET status = ?, sent_at = NOW() WHERE message_id = (SELECT id FROM messages WHERE whatsapp_message_id = ? LIMIT 1)',
                ['sent', $waId]
            );
        }
    }
}
