<?php

declare(strict_types=1);

namespace App\Controllers\Webhook;

use App\Core\DB;
use App\Lib\Logger;

/**
 * EvolutionController — processa webhooks da Evolution API (WhatsApp Web).
 */
class EvolutionController
{
    public function receive(): void
    {
        // Retorna 200 imediatamente
        http_response_code(200);
        echo 'ok';

        // Lê o payload
        $raw = file_get_contents('php://input');
        if (!$raw) {
            exit;
        }

        $payload = json_decode($raw, true);
        if (!is_array($payload)) {
            exit;
        }

        $event        = $payload['event'] ?? '';
        $instanceName = $payload['instance'] ?? '';

        Logger::info('EvolutionWebhook received', ['event' => $event, 'instance' => $instanceName]);

        if ($event === 'messages.upsert') {
            $this->handleMessage($payload, $instanceName);
        }

        exit;
    }

    private function handleMessage(array $payload, string $instanceName): void
    {
        // Encontra o agente pela instância
        $agent = DB::fetchOne(
            "SELECT * FROM agents WHERE evo_instance_name = ? AND status = 'active'",
            [$instanceName]
        );
        if (!$agent) {
            Logger::warning('EvolutionWebhook: agent not found', ['instance' => $instanceName]);
            return;
        }

        $data = $payload['data'] ?? [];
        if (empty($data)) return;

        // Suporte a array de mensagens ou objeto único
        $messages = isset($data[0]) ? $data : [$data];

        foreach ($messages as $msg) {
            $this->processMessage($agent, $msg);
        }
    }

    private function processMessage(array $agent, array $msg): void
    {
        $key       = $msg['key'] ?? [];
        $fromMe    = $key['fromMe'] ?? false;

        // Ignora mensagens enviadas pelo próprio bot
        if ($fromMe) return;

        $remoteJid = $key['remoteJid'] ?? '';
        $msgId     = $key['id'] ?? '';

        // Ignora grupos (jid contém @g.us)
        if (str_contains($remoteJid, '@g.us')) return;

        // Extrai número limpo
        $phone = preg_replace('/[^0-9]/', '', str_replace('@s.whatsapp.net', '', $remoteJid));
        if (!$phone) return;

        // Extrai conteúdo de texto
        $message  = $msg['message'] ?? [];
        $content  = $message['conversation']
            ?? $message['extendedTextMessage']['text']
            ?? $message['imageMessage']['caption']
            ?? '';

        if (!$content) return;

        $tenantId = (int)$agent['tenant_id'];
        $agentId  = (int)$agent['id'];

        // Deduplicação
        $dedupeKey = 'evo_in_' . $msgId;
        $exists    = DB::fetchColumn(
            'SELECT id FROM messages WHERE dedupe_key = ?',
            [$dedupeKey]
        );
        if ($exists) return;

        // Contato
        $contact = DB::fetchOne(
            'SELECT * FROM contacts WHERE agent_id = ? AND phone = ?',
            [$agentId, $phone]
        );

        if (!$contact) {
            $pushName = $msg['pushName'] ?? null;
            $contactId = DB::insert('contacts', [
                'tenant_id'       => $tenantId,
                'agent_id'        => $agentId,
                'phone'           => $phone,
                'name'            => $pushName,
                'last_inbound_at' => date('Y-m-d H:i:s'),
            ]);
            $contact = DB::fetchOne('SELECT * FROM contacts WHERE id = ?', [$contactId]);
        } else {
            DB::update('contacts', ['last_inbound_at' => date('Y-m-d H:i:s')], ['id' => $contact['id']]);
        }

        // Thread
        $thread = DB::fetchOne(
            "SELECT * FROM threads WHERE agent_id = ? AND contact_id = ? AND status = 'open' ORDER BY id DESC LIMIT 1",
            [$agentId, $contact['id']]
        );
        if (!$thread) {
            $threadId = DB::insert('threads', [
                'tenant_id'      => $tenantId,
                'agent_id'       => $agentId,
                'contact_id'     => $contact['id'],
                'started_at'     => date('Y-m-d H:i:s'),
                'last_message_at' => date('Y-m-d H:i:s'),
            ]);
        } else {
            $threadId = $thread['id'];
        }

        // Salva mensagem
        $messageId = DB::insert('messages', [
            'tenant_id'           => $tenantId,
            'agent_id'            => $agentId,
            'thread_id'           => $threadId,
            'contact_id'          => $contact['id'],
            'direction'           => 'inbound',
            'content'             => $content,
            'message_type'        => 'text',
            'whatsapp_message_id' => $msgId,
            'dedupe_key'          => $dedupeKey,
            'status'              => 'received',
        ]);

        // Enfileira job de processamento
        DB::insert('jobs', [
            'tenant_id' => $tenantId,
            'queue'     => 'inbound',
            'job_class' => 'ProcessInbound',
            'payload'   => json_encode([
                'message_id' => $messageId,
                'thread_id'  => $threadId,
                'contact_id' => $contact['id'],
                'agent_id'   => $agentId,
                'tenant_id'  => $tenantId,
                'content'    => $content,
            ]),
        ]);

        Logger::info('EvolutionWebhook: message queued', [
            'agent_id'   => $agentId,
            'phone'      => $phone,
            'message_id' => $messageId,
        ]);
    }
}
