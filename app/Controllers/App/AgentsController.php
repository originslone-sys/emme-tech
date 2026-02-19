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

        $plan = Auth::tenantPlan();
        Response::view('app/agents/index', [
            'user'   => $user,
            'agents' => $agents,
            'plan'   => $plan,
            'csrf'   => CSRF::field(),
        ]);
    }

    public function create(): void
    {
        Auth::requireTenant();

        if (!Auth::canCreateAgent()) {
            Session::flash('error', 'Limite de agentes do plano atingido. Faça upgrade.');
            Response::redirect('/app/agents');
        }

        $tid      = Auth::tenantId();
        $models   = DB::fetchAll('SELECT * FROM model_catalog WHERE is_active = 1 ORDER BY sort_order');
        $personas = DB::fetchAll('SELECT * FROM personas WHERE tenant_id = ? ORDER BY name', [$tid]);

        Response::view('app/agents/form', [
            'user'     => Auth::tenantUser(),
            'agent'    => null,
            'models'   => $models,
            'personas' => $personas,
            'csrf'     => CSRF::field(),
        ]);
    }

    public function store(): void
    {
        Auth::requireTenant();
        CSRF::verifyRequest();

        if (!Auth::canCreateAgent()) {
            Session::flash('error', 'Limite de agentes do plano atingido.');
            Response::redirect('/app/agents');
        }

        $tid  = Auth::tenantId();
        $user = Auth::tenantUser();
        $data = $this->collectData($tid);

        if (!$data['name']) {
            Session::flash('error', 'Nome do agente é obrigatório.');
            Response::redirect('/app/agents/create');
        }

        $id = DB::insert('agents', $data);

        AuditLog::tenant($user['id'], $tid, 'agent.created', 'agent', (int)$id);
        Session::flash('success', 'Agente criado com sucesso!');
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

        Response::view('app/agents/form', [
            'user'     => Auth::tenantUser(),
            'agent'    => $agent,
            'models'   => $models,
            'personas' => $personas,
            'csrf'     => CSRF::field(),
        ]);
    }

    public function update(string $id): void
    {
        Auth::requireTenant();
        CSRF::verifyRequest();

        $tid    = Auth::tenantId();
        $user   = Auth::tenantUser();
        $agId   = (int)$id;
        $old    = DB::fetchOne('SELECT * FROM agents WHERE id = ? AND tenant_id = ?', [$agId, $tid]);
        if (!$old) Response::abort(404);

        $data = $this->collectData($tid, $old);
        DB::update('agents', $data, ['id' => $agId, 'tenant_id' => $tid]);

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
        $ag   = DB::fetchOne('SELECT id FROM agents WHERE id = ? AND tenant_id = ?', [$agId, $tid]);
        if (!$ag) Response::abort(404);

        DB::delete('agents', ['id' => $agId, 'tenant_id' => $tid]);
        AuditLog::tenant($user['id'], $tid, 'agent.deleted', 'agent', $agId);

        Session::flash('success', 'Agente removido.');
        Response::redirect('/app/agents');
    }

    private function collectData(int $tid, array $old = []): array
    {
        $name    = trim(Request::post('name', ''));
        $slug    = preg_replace('/[^a-z0-9\-]/', '', strtolower(trim(Request::post('slug', '') ?: $name)));
        $slug    = $slug ?: 'agent';

        // Handle WhatsApp token
        $waToken    = Request::post('whatsapp_access_token', '');
        $waTokenEnc = !empty($old['whatsapp_access_token_encrypted']) ? $old['whatsapp_access_token_encrypted'] : null;
        if ($waToken) {
            $waTokenEnc = Crypto::encrypt($waToken);
        }

        // Handle OpenRouter override token
        $orToken    = Request::post('openrouter_token_override', '');
        $orTokenEnc = !empty($old['openrouter_token_override_enc']) ? $old['openrouter_token_override_enc'] : null;
        if ($orToken) {
            $orTokenEnc = Crypto::encrypt($orToken);
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
            'whatsapp_phone_number_id'        => trim(Request::post('whatsapp_phone_number_id', '')),
            'whatsapp_access_token_encrypted' => $waTokenEnc,
            'whatsapp_verify_token'           => trim(Request::post('whatsapp_verify_token', '')),
            'whatsapp_waba_id'                => trim(Request::post('whatsapp_waba_id', '')),
            'openrouter_token_override_enc'   => $orTokenEnc,
            'enable_kb'                       => Request::post('enable_kb') ? 1 : 0,
            'kb_top_k'                        => (int)Request::post('kb_top_k', 3),
            'handoff_keyword'                 => trim(Request::post('handoff_keyword', 'humano')),
            'optout_keyword'                  => trim(Request::post('optout_keyword', 'sair')),
        ];
    }
}
