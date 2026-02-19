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

class PersonasController
{
    public function index(): void
    {
        Auth::requireTenant();
        $tid = Auth::tenantId();
        $personas = DB::fetchAll(
            'SELECT p.*, a.name AS agent_name
             FROM personas p
             LEFT JOIN agents a ON a.id = p.agent_id
             WHERE p.tenant_id = ?
             ORDER BY p.name',
            [$tid]
        );
        Response::view('app/personas/index', [
            'user'     => Auth::tenantUser(),
            'personas' => $personas,
            'csrf'     => CSRF::field(),
        ]);
    }

    public function create(): void
    {
        Auth::requireTenant();
        $tid    = Auth::tenantId();
        $agents = DB::fetchAll('SELECT id, name FROM agents WHERE tenant_id = ?', [$tid]);
        Response::view('app/personas/form', [
            'user'    => Auth::tenantUser(),
            'persona' => null,
            'agents'  => $agents,
            'csrf'    => CSRF::field(),
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
            Session::flash('error', 'Nome da persona é obrigatório.');
            Response::redirect('/app/personas/create');
        }

        $id = DB::insert('personas', $data);
        AuditLog::tenant($user['id'], $tid, 'persona.created', 'persona', (int)$id);

        Session::flash('success', 'Persona criada.');
        Response::redirect('/app/personas');
    }

    public function edit(string $id): void
    {
        Auth::requireTenant();
        $tid     = Auth::tenantId();
        $persona = DB::fetchOne('SELECT * FROM personas WHERE id = ? AND tenant_id = ?', [(int)$id, $tid]);
        if (!$persona) Response::abort(404);

        $agents = DB::fetchAll('SELECT id, name FROM agents WHERE tenant_id = ?', [$tid]);
        Response::view('app/personas/form', [
            'user'    => Auth::tenantUser(),
            'persona' => $persona,
            'agents'  => $agents,
            'csrf'    => CSRF::field(),
        ]);
    }

    public function update(string $id): void
    {
        Auth::requireTenant();
        CSRF::verifyRequest();

        $tid  = Auth::tenantId();
        $user = Auth::tenantUser();
        $pId  = (int)$id;
        $old  = DB::fetchOne('SELECT * FROM personas WHERE id = ? AND tenant_id = ?', [$pId, $tid]);
        if (!$old) Response::abort(404);

        $data = $this->collectData($tid);
        DB::update('personas', $data, ['id' => $pId, 'tenant_id' => $tid]);

        AuditLog::tenant($user['id'], $tid, 'persona.updated', 'persona', $pId);
        Session::flash('success', 'Persona atualizada.');
        Response::redirect('/app/personas');
    }

    public function destroy(string $id): void
    {
        Auth::requireTenant();
        CSRF::verifyRequest();

        $tid  = Auth::tenantId();
        $user = Auth::tenantUser();
        $pId  = (int)$id;
        $old  = DB::fetchOne('SELECT id FROM personas WHERE id = ? AND tenant_id = ?', [$pId, $tid]);
        if (!$old) Response::abort(404);

        DB::delete('personas', ['id' => $pId, 'tenant_id' => $tid]);
        AuditLog::tenant($user['id'], $tid, 'persona.deleted', 'persona', $pId);

        Session::flash('success', 'Persona removida.');
        Response::redirect('/app/personas');
    }

    private function collectData(int $tid): array
    {
        return [
            'tenant_id'    => $tid,
            'agent_id'     => Request::post('agent_id') ?: null,
            'name'         => trim(Request::post('name', '')),
            'description'  => trim(Request::post('description', '')),
            'instructions' => trim(Request::post('instructions', '')),
            'tone'         => Request::post('tone', 'professional'),
            'language'     => Request::post('language', 'pt-BR'),
        ];
    }
}
