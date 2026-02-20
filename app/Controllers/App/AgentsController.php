<?php

declare(strict_types=1);

namespace App\Controllers\App;

use App\Core\Auth;
use App\Core\CSRF;
use App\Core\DB;
use App\Core\Request;
use App\Core\Response;
use App\Core\Session;
use App\Lib\AuditLog;
use App\Lib\Crypto;
use App\Lib\EvolutionAPI;
use App\Lib\GlobalSettings;

class AgentsController
{
    public function index(): void
    {
        Auth::requireTenant();
        $user = Auth::tenantUser();
        $tid  = $user['tenant_id'];

        $agents = DB::fetchAll(
            'SELECT a.*, mc.display_name AS model_name, p.name AS persona_name
             FROM agents a
             LEFT JOIN model_catalog mc ON mc.id = a.model_catalog_id
             LEFT JOIN personas p ON p.id = a.persona_id
             WHERE a.tenant_id = ?
             ORDER BY a.created_at DESC',
            [$tid]
        );

        Response::view('app/agents/index', [
            'user'   => $user,
            'agents' => $agents,
            'csrf'   => CSRF::field(),
        ]);
    }

    public function create(): void
    {
        Auth::requireTenant();

        $tid      = Auth::tenantId();
        $models   = DB::fetchAll('SELECT * FROM model_catalog WHERE is_active = 1 ORDER BY sort_order');
        $personas = DB::fetchAll('SELECT * FROM personas WHERE tenant_id = ? ORDER BY name', [$tid]);

        Response::view('app/agents/form', [
            'user'      => Auth::tenantUser(),
            'agent'     => null,
            'models'    => $models,
            'personas'  => $personas,
            'evoStatus' => null,
            'csrf'      => CSRF::field(),
        ]);
    }

    public function store(): void
    {
        Auth::requireTenant();
        CSRF::verifyRequest();

        $tid  = Auth::tenantId();
        $user = Auth::tenantUser();
        $data = $this->collectData($tid);

        if (!$data['name']) {
            Session::flash('error', 'Nome do agente é obrigatório.');
            Response::redirect('/app/agents/create');
        }

        $id = DB::insert('agents', $data);

        // Para WhatsApp Web: cria instância na Evolution API
        if ($data['whatsapp_mode'] === 'whatsapp_web' && $data['evo_instance_name']) {
            $this->provisionEvoInstance($data['evo_instance_name']);
        }

        AuditLog::tenant($user['id'], $tid, 'agent.created', 'agent', (int)$id);

        $msg = 'Agente criado com sucesso!';
        if ($data['whatsapp_mode'] === 'whatsapp_web') {
            $msg .= ' Acesse editar para escanear o QR Code e conectar o WhatsApp.';
        }
        Session::flash('success', $msg);
        Response::redirect('/app/agents');
    }

    public function edit(string $id): void
    {
        Auth::requireTenant();
        $tid   = Auth::tenantId();
        $agent = DB::fetchOne('SELECT * FROM agents WHERE id = ? AND tenant_id = ?', [(int)$id, $tid]);
        if (!$agent) Response::abort(404);

        $models   = DB::fetchAll('SELECT * FROM model_catalog WHERE is_active = 1 ORDER BY sort_order');
        $personas = DB::fetchAll('SELECT * FROM personas WHERE tenant_id = ? ORDER BY name', [$tid]);

        // Estado de conexão para WhatsApp Web
        $evoStatus = null;
        if ($agent['whatsapp_mode'] === 'whatsapp_web' && $agent['evo_instance_name']) {
            try {
                $evo       = EvolutionAPI::fromSettings();
                $state     = $evo->getConnectionState($agent['evo_instance_name']);
                $evoStatus = $state['instance']['state'] ?? 'unknown';
            } catch (\Throwable) {
                $evoStatus = 'error';
            }
        }

        Response::view('app/agents/form', [
            'user'      => Auth::tenantUser(),
            'agent'     => $agent,
            'models'    => $models,
            'personas'  => $personas,
            'evoStatus' => $evoStatus,
            'csrf'      => CSRF::field(),
        ]);
    }

    public function update(string $id): void
    {
        Auth::requireTenant();
        CSRF::verifyRequest();

        $tid  = Auth::tenantId();
        $user = Auth::tenantUser();
        $agId = (int)$id;
        $old  = DB::fetchOne('SELECT * FROM agents WHERE id = ? AND tenant_id = ?', [$agId, $tid]);
        if (!$old) Response::abort(404);

        $data = $this->collectData($tid, $old);
        DB::update('agents', $data, ['id' => $agId, 'tenant_id' => $tid]);

        // Se mudou para WhatsApp Web e ainda não tem instância criada
        if ($data['whatsapp_mode'] === 'whatsapp_web' && $data['evo_instance_name'] && !$old['evo_instance_name']) {
            $this->provisionEvoInstance($data['evo_instance_name']);
        }

        AuditLog::tenant($user['id'], $tid, 'agent.updated', 'agent', $agId);
        Session::flash('success', 'Agente atualizado.');
        Response::redirect('/app/agents');
    }

    public function destroy(string $id): void
    {
        Auth::requireTenant();
        CSRF::verifyRequest();

        $tid  = Auth::tenantId();
        $user = Auth::tenantUser();
        $agId = (int)$id;
        $ag   = DB::fetchOne('SELECT * FROM agents WHERE id = ? AND tenant_id = ?', [$agId, $tid]);
        if (!$ag) Response::abort(404);

        // Remove instância Evolution se for WhatsApp Web
        if ($ag['whatsapp_mode'] === 'whatsapp_web' && $ag['evo_instance_name']) {
            try {
                $evo = EvolutionAPI::fromSettings();
                $evo->deleteInstance($ag['evo_instance_name']);
            } catch (\Throwable) {
                // Não bloqueia remoção se Evolution falhar
            }
        }

        DB::delete('agents', ['id' => $agId, 'tenant_id' => $tid]);
        AuditLog::tenant($user['id'], $tid, 'agent.deleted', 'agent', $agId);

        Session::flash('success', 'Agente removido.');
        Response::redirect('/app/agents');
    }

    /**
     * Retorna QR Code JSON da Evolution API.
     * GET /app/agents/:id/qrcode
     */
    public function qrcode(string $id): void
    {
        Auth::requireTenant();
        $tid   = Auth::tenantId();
        $agId  = (int)$id;
        $agent = DB::fetchOne('SELECT * FROM agents WHERE id = ? AND tenant_id = ?', [$agId, $tid]);

        if (!$agent) {
            header('Content-Type: application/json');
            http_response_code(404);
            echo json_encode(['error' => 'Agente não encontrado.']);
            exit;
        }

        if ($agent['whatsapp_mode'] !== 'whatsapp_web' || !$agent['evo_instance_name']) {
            header('Content-Type: application/json');
            http_response_code(400);
            echo json_encode(['error' => 'Agente não está em modo WhatsApp Web.']);
            exit;
        }

        try {
            $evo  = EvolutionAPI::fromSettings();
            $data = $evo->getQRCode($agent['evo_instance_name']);
            header('Content-Type: application/json');
            echo json_encode(['qrcode' => $data['base64'] ?? $data['qrcode'] ?? null, 'status' => 'ok']);
        } catch (\Throwable $e) {
            header('Content-Type: application/json');
            http_response_code(500);
            echo json_encode(['error' => $e->getMessage()]);
        }
        exit;
    }

    // ----------------------------------------------------------------
    // Helpers
    // ----------------------------------------------------------------

    private function collectData(int $tid, array $old = []): array
    {
        $name = trim(Request::post('name', ''));
        $slug = preg_replace('/[^a-z0-9\-]/', '', strtolower(trim(Request::post('slug', '') ?: $name)));
        $slug = $slug ?: 'agent';

        $mode = Request::post('whatsapp_mode', 'cloud_api');

        // Cloud API: token WhatsApp
        $waToken    = Request::post('whatsapp_access_token', '');
        $waTokenEnc = $old['whatsapp_access_token_encrypted'] ?? null;
        if ($waToken) {
            $waTokenEnc = Crypto::encrypt($waToken);
        }

        // WhatsApp Web: nome da instância
        $evoInstanceName = $old['evo_instance_name'] ?? null;
        if ($mode === 'whatsapp_web' && !$evoInstanceName) {
            $evoInstanceName = 't' . $tid . '-' . preg_replace('/[^a-z0-9]/', '', $slug) . '-' . substr(md5(uniqid()), 0, 6);
        }

        return [
            'tenant_id'                       => $tid,
            'name'                            => $name,
            'slug'                            => $slug,
            'status'                          => Request::post('status', 'inactive'),
            'model_catalog_id'                => Request::post('model_catalog_id') ?: null,
            'temperature'                     => (float)Request::post('temperature', 0.7),
            'max_tokens'                      => (int)Request::post('max_tokens', 1024),
            'system_prompt'                   => Request::post('system_prompt', ''),
            'persona_id'                      => Request::post('persona_id') ?: null,
            // WhatsApp
            'whatsapp_mode'                   => $mode,
            'whatsapp_phone_number_id'        => trim(Request::post('whatsapp_phone_number_id', '')),
            'whatsapp_access_token_encrypted' => $waTokenEnc,
            'whatsapp_verify_token'           => trim(Request::post('whatsapp_verify_token', '')),
            'whatsapp_waba_id'                => trim(Request::post('whatsapp_waba_id', '')),
            'evo_instance_name'               => $evoInstanceName,
            // KB
            'enable_kb'                       => Request::post('enable_kb') ? 1 : 0,
            'kb_top_k'                        => (int)Request::post('kb_top_k', 3),
            // Keywords
            'handoff_keyword'                 => trim(Request::post('handoff_keyword', 'humano')),
            'optout_keyword'                  => trim(Request::post('optout_keyword', 'sair')),
        ];
    }

    private function provisionEvoInstance(string $instanceName): void
    {
        try {
            $evoUrl = GlobalSettings::get('evo_api_url');
            $evoKey = GlobalSettings::get('evo_api_key');
            if (!$evoUrl || !$evoKey) return;

            $evo = EvolutionAPI::fromSettings();
            $evo->createInstance($instanceName, env('APP_URL', '') . '/webhook/evolution');
        } catch (\Throwable) {
            // Silencioso — não bloqueia o fluxo
        }
    }
}
