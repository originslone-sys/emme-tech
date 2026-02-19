<?php

declare(strict_types=1);

namespace App\Jobs;

use App\Core\DB;
use App\Lib\Logger;
use App\Lib\OpenRouter;
use App\Lib\Retriever;
use App\Lib\WhatsApp;

/**
 * ProcessInbound — handles an inbound WhatsApp message:
 * 1. Resolve agent, contact, thread
 * 2. Check opt-out / handoff / smalltalk rules
 * 3. RAG retrieval (if KB enabled)
 * 4. Build prompt and call OpenRouter
 * 5. Save reply and enqueue outbox
 */
class ProcessInbound
{
    public function handle(array $payload): void
    {
        $messageId = (int)($payload['message_id'] ?? 0);
        $threadId  = (int)($payload['thread_id']  ?? 0);
        $contactId = (int)($payload['contact_id'] ?? 0);
        $agentId   = (int)($payload['agent_id']   ?? 0);
        $tenantId  = (int)($payload['tenant_id']  ?? 0);
        $content   = (string)($payload['content'] ?? '');

        Logger::info('ProcessInbound started', compact('messageId', 'agentId', 'tenantId'));

        // Load records
        $agent = DB::fetchOne('SELECT * FROM agents WHERE id = ? AND tenant_id = ?', [$agentId, $tenantId]);
        if (!$agent) {
            throw new \RuntimeException("Agent $agentId not found for tenant $tenantId");
        }

        $contact = DB::fetchOne('SELECT * FROM contacts WHERE id = ? AND tenant_id = ?', [$contactId, $tenantId]);
        if (!$contact) {
            throw new \RuntimeException("Contact $contactId not found");
        }

        // Check opt-out
        $optoutKw = strtolower(trim($agent['optout_keyword'] ?? 'sair'));
        if ($optoutKw && strtolower(trim($content)) === $optoutKw) {
            DB::update('contacts', ['opt_out' => 1], ['id' => $contactId]);
            $this->sendReply($agent, $contact, $threadId, $tenantId, 'Você foi removido da lista. Para voltar, envie OI.', 'text');
            Logger::info('Contact opted out', ['contact_id' => $contactId]);
            return;
        }

        if ($contact['opt_out']) {
            Logger::info('Contact is opted out, ignoring', ['contact_id' => $contactId]);
            return;
        }

        // Check handoff
        $handoffKw = strtolower(trim($agent['handoff_keyword'] ?? 'humano'));
        if ($handoffKw && strtolower(trim($content)) === $handoffKw) {
            DB::update('contacts', ['handoff' => 1], ['id' => $contactId]);
            DB::update('threads', ['status' => 'handoff'], ['id' => $threadId]);
            $this->sendReply($agent, $contact, $threadId, $tenantId, 'Solicitação de atendimento humano registrada. Aguarde.', 'text');
            Logger::info('Handoff requested', ['contact_id' => $contactId]);
            return;
        }

        if ($contact['handoff']) {
            Logger::info('Contact in handoff, skipping AI', ['contact_id' => $contactId]);
            return;
        }

        // Build conversation history (last 10 messages)
        $history = DB::fetchAll(
            "SELECT direction, content FROM messages
             WHERE thread_id = ? AND id < ?
             ORDER BY id DESC LIMIT 10",
            [$threadId, $messageId]
        );
        $history = array_reverse($history);

        // Build messages array for OpenRouter
        $messages = [];

        // System prompt
        $systemPrompt = $agent['system_prompt'] ?? '';

        // Persona
        $persona = null;
        if ($agent['persona_id']) {
            $persona = DB::fetchOne('SELECT * FROM personas WHERE id = ?', [(int)$agent['persona_id']]);
        }

        if ($persona && $persona['instructions']) {
            $systemPrompt = $persona['instructions'] . "\n\n" . $systemPrompt;
        }

        // RAG context
        if ($agent['enable_kb']) {
            $ctx = Retriever::buildContext($agentId, $content, (int)$agent['kb_top_k']);
            if ($ctx) {
                $systemPrompt .= "\n\n" . $ctx;
            }
        }

        if ($systemPrompt) {
            $messages[] = ['role' => 'system', 'content' => $systemPrompt];
        }

        // Historical messages
        foreach ($history as $h) {
            $role = $h['direction'] === 'inbound' ? 'user' : 'assistant';
            $messages[] = ['role' => $role, 'content' => $h['content']];
        }

        // Current message
        $messages[] = ['role' => 'user', 'content' => $content];

        // Get model
        $model = null;
        if ($agent['model_catalog_id']) {
            $model = DB::fetchOne('SELECT * FROM model_catalog WHERE id = ? AND is_active = 1', [(int)$agent['model_catalog_id']]);
        }

        if (!$model) {
            // Fallback to first active model
            $model = DB::fetchOne('SELECT * FROM model_catalog WHERE is_active = 1 ORDER BY sort_order LIMIT 1');
        }

        if (!$model) {
            throw new \RuntimeException("No active model available for agent $agentId");
        }

        // Call OpenRouter
        $or    = OpenRouter::forAgent($agent, $tenantId);
        $reply = $or->chat(
            $model['model_id'],
            $messages,
            (float)$agent['temperature'],
            (int)$agent['max_tokens']
        );

        // Determine message type based on 24h window
        $msgType = WhatsApp::inFreeWindow($contact['last_inbound_at']) ? 'text' : 'template';

        if ($msgType === 'template') {
            // We cannot send arbitrary text outside window
            Logger::warning('Outside 24h window, cannot send free text', ['contact_id' => $contactId]);
            // Save the reply but mark as failed due to window constraint
            DB::insert('messages', [
                'tenant_id'    => $tenantId,
                'agent_id'     => $agentId,
                'thread_id'    => $threadId,
                'contact_id'   => $contactId,
                'direction'    => 'outbound',
                'content'      => $reply,
                'message_type' => 'text',
                'status'       => 'failed',
                'metadata'     => json_encode(['error' => 'Outside 24h messaging window. Use template.']),
            ]);
            return;
        }

        $this->sendReply($agent, $contact, $threadId, $tenantId, $reply, 'text');

        Logger::info('ProcessInbound completed', [
            'agent_id'  => $agentId,
            'thread_id' => $threadId,
            'model'     => $model['model_id'],
        ]);
    }

    private function sendReply(
        array  $agent,
        array  $contact,
        int    $threadId,
        int    $tenantId,
        string $content,
        string $type
    ): void {
        // Save outbound message
        $msgId = DB::insert('messages', [
            'tenant_id'    => $tenantId,
            'agent_id'     => $agent['id'],
            'thread_id'    => $threadId,
            'contact_id'   => $contact['id'],
            'direction'    => 'outbound',
            'content'      => $content,
            'message_type' => $type,
            'status'       => 'queued',
        ]);

        // Enqueue in outbox
        DB::insert('outbox', [
            'tenant_id'    => $tenantId,
            'agent_id'     => $agent['id'],
            'contact_id'   => $contact['id'],
            'thread_id'    => $threadId,
            'message_id'   => $msgId,
            'phone'        => $contact['phone'],
            'content'      => $content,
            'message_type' => $type,
            'status'       => 'pending',
        ]);

        // Update thread last_message_at
        DB::update('threads', ['last_message_at' => date('Y-m-d H:i:s')], ['id' => $threadId]);
    }
}
