<?php

declare(strict_types=1);

namespace App\Jobs;

use App\Core\DB;
use App\Lib\GlobalSettings;
use App\Lib\Logger;
use App\Lib\OpenRouter;
use App\Lib\Retriever;
use App\Lib\WhatsApp;

/**
 * ProcessInbound — processa mensagem inbound do WhatsApp:
 * 1. Verifica créditos do tenant
 * 2. Resolve agente, contato, thread
 * 3. Verifica opt-out / handoff / keywords
 * 4. RAG retrieval (se KB habilitada)
 * 5. Chama OpenRouter com token global (admin configura)
 * 6. Debita 1 crédito por resposta enviada
 * 7. Salva resposta e enfileira outbox
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

        // ----------------------------------------------------------------
        // Verifica saldo de créditos ANTES de processar
        // ----------------------------------------------------------------
        $tenant = DB::fetchOne('SELECT credits FROM tenants WHERE id = ?', [$tenantId]);
        if (!$tenant || (int)$tenant['credits'] <= 0) {
            Logger::warning('ProcessInbound: tenant has no credits', ['tenant_id' => $tenantId]);
            $agent   = DB::fetchOne('SELECT * FROM agents WHERE id = ?', [$agentId]);
            $contact = DB::fetchOne('SELECT * FROM contacts WHERE id = ?', [$contactId]);
            if ($agent && $contact) {
                $this->sendReply($agent, $contact, $threadId, $tenantId,
                    'Desculpe, não posso responder no momento. Entre em contato com o suporte.', 'text');
            }
            return;
        }

        // Carrega registros
        $agent = DB::fetchOne('SELECT * FROM agents WHERE id = ? AND tenant_id = ?', [$agentId, $tenantId]);
        if (!$agent) {
            throw new \RuntimeException("Agent $agentId not found for tenant $tenantId");
        }

        $contact = DB::fetchOne('SELECT * FROM contacts WHERE id = ? AND tenant_id = ?', [$contactId, $tenantId]);
        if (!$contact) {
            throw new \RuntimeException("Contact $contactId not found");
        }

        // Verifica opt-out
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

        // Verifica handoff
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

        // Histórico de conversa (últimas 10 mensagens)
        $history = DB::fetchAll(
            "SELECT direction, content FROM messages
             WHERE thread_id = ? AND id < ?
             ORDER BY id DESC LIMIT 10",
            [$threadId, $messageId]
        );
        $history = array_reverse($history);

        // Constrói mensagens para o LLM
        $messages     = [];
        $systemPrompt = $agent['system_prompt'] ?? '';

        // Persona
        if ($agent['persona_id']) {
            $persona = DB::fetchOne('SELECT * FROM personas WHERE id = ?', [(int)$agent['persona_id']]);
            if ($persona && $persona['instructions']) {
                $systemPrompt = $persona['instructions'] . "\n\n" . $systemPrompt;
            }
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

        foreach ($history as $h) {
            $role       = $h['direction'] === 'inbound' ? 'user' : 'assistant';
            $messages[] = ['role' => $role, 'content' => $h['content']];
        }
        $messages[] = ['role' => 'user', 'content' => $content];

        // Modelo
        $model = null;
        if ($agent['model_catalog_id']) {
            $model = DB::fetchOne('SELECT * FROM model_catalog WHERE id = ? AND is_active = 1', [(int)$agent['model_catalog_id']]);
        }
        if (!$model) {
            $model = DB::fetchOne('SELECT * FROM model_catalog WHERE is_active = 1 ORDER BY sort_order LIMIT 1');
        }
        if (!$model) {
            throw new \RuntimeException("No active model available for agent $agentId");
        }

        // OpenRouter — usa token global configurado pelo admin
        $apiKey = GlobalSettings::get('openrouter_api_key');
        $apiUrl = GlobalSettings::get('openrouter_api_url', 'https://openrouter.ai/api/v1');

        if (!$apiKey) {
            throw new \RuntimeException("OpenRouter API key not configured in global settings.");
        }

        $or    = new OpenRouter($apiKey, $apiUrl);
        $reply = $or->chat(
            $model['model_id'],
            $messages,
            (float)$agent['temperature'],
            (int)$agent['max_tokens']
        );

        // Janela de 24h (apenas Cloud API)
        if (($agent['whatsapp_mode'] ?? 'cloud_api') !== 'whatsapp_web') {
            if (!WhatsApp::inFreeWindow($contact['last_inbound_at'])) {
                Logger::warning('Outside 24h window, cannot send free text', ['contact_id' => $contactId]);
                DB::insert('messages', [
                    'tenant_id'    => $tenantId,
                    'agent_id'     => $agentId,
                    'thread_id'    => $threadId,
                    'contact_id'   => $contactId,
                    'direction'    => 'outbound',
                    'content'      => $reply,
                    'message_type' => 'text',
                    'status'       => 'failed',
                    'metadata'     => json_encode(['error' => 'Outside 24h messaging window.']),
                ]);
                return;
            }
        }

        $this->sendReply($agent, $contact, $threadId, $tenantId, $reply, 'text');

        // ----------------------------------------------------------------
        // Debita 1 crédito por resposta do agente
        // ----------------------------------------------------------------
        DB::query('UPDATE tenants SET credits = credits - 1 WHERE id = ? AND credits > 0', [$tenantId]);
        DB::insert('credit_transactions', [
            'tenant_id'    => $tenantId,
            'amount'       => -1,
            'type'         => 'usage',
            'description'  => 'Resposta do agente',
            'reference_id' => (string)$messageId,
        ]);

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

        DB::update('threads', ['last_message_at' => date('Y-m-d H:i:s')], ['id' => $threadId]);
    }
}
