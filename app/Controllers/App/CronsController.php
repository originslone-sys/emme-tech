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

class CronsController
{
    public function index(): void
    {
        Auth::requireTenant();
        $tid = Auth::tenantId();

        $crons = DB::fetchAll(
            'SELECT c.*, a.name AS agent_name
             FROM cron_jobs c
             LEFT JOIN agents a ON a.id = c.agent_id
             WHERE c.tenant_id = ?
             ORDER BY c.created_at DESC',
            [$tid]
        );

        $recentRuns = DB::fetchAll(
            'SELECT cr.*, c.name AS cron_name
             FROM cron_runs cr
             JOIN cron_jobs c ON c.id = cr.cron_job_id
             WHERE cr.tenant_id = ?
             ORDER BY cr.started_at DESC
             LIMIT 20',
            [$tid]
        );

        Response::view('app/crons/index', [
            'user'       => Auth::tenantUser(),
            'crons'      => $crons,
            'recentRuns' => $recentRuns,
            'csrf'       => CSRF::field(),
        ]);
    }

    public function create(): void
    {
        Auth::requireTenant();
        $tid    = Auth::tenantId();
        $agents = DB::fetchAll('SELECT id, name FROM agents WHERE tenant_id = ?', [$tid]);
        Response::view('app/crons/form', [
            'user'   => Auth::tenantUser(),
            'cron'   => null,
            'agents' => $agents,
            'csrf'   => CSRF::field(),
        ]);
    }

    public function store(): void
    {
        Auth::requireTenant();
        CSRF::verifyRequest();

        $tid  = Auth::tenantId();
        $user = Auth::tenantUser();

        $data = $this->collectData($tid);
        if (!$data['name'] || !$data['agent_id']) {
            Session::flash('error', 'Nome e agente são obrigatórios.');
            Response::redirect('/app/crons/create');
        }

        $id = DB::insert('cron_jobs', $data);
        AuditLog::tenant($user['id'], $tid, 'cron.created', 'cron_jobs', (int)$id);

        Session::flash('success', 'Automação criada!');
        Response::redirect('/app/crons');
    }

    public function edit(string $id): void
    {
        Auth::requireTenant();
        $tid   = Auth::tenantId();
        $cronId = (int)$id;
        $cron  = DB::fetchOne('SELECT * FROM cron_jobs WHERE id = ? AND tenant_id = ?', [$cronId, $tid]);
        if (!$cron) Response::abort(404);

        $agents = DB::fetchAll('SELECT id, name FROM agents WHERE tenant_id = ?', [$tid]);
        Response::view('app/crons/form', [
            'user'   => Auth::tenantUser(),
            'cron'   => $cron,
            'agents' => $agents,
            'csrf'   => CSRF::field(),
        ]);
    }

    public function update(string $id): void
    {
        Auth::requireTenant();
        CSRF::verifyRequest();

        $tid    = Auth::tenantId();
        $user   = Auth::tenantUser();
        $cronId = (int)$id;
        $old    = DB::fetchOne('SELECT * FROM cron_jobs WHERE id = ? AND tenant_id = ?', [$cronId, $tid]);
        if (!$old) Response::abort(404);

        $data = $this->collectData($tid);
        DB::update('cron_jobs', $data, ['id' => $cronId, 'tenant_id' => $tid]);

        AuditLog::tenant($user['id'], $tid, 'cron.updated', 'cron_jobs', $cronId);
        Session::flash('success', 'Automação atualizada.');
        Response::redirect('/app/crons');
    }

    public function destroy(string $id): void
    {
        Auth::requireTenant();
        CSRF::verifyRequest();

        $tid    = Auth::tenantId();
        $user   = Auth::tenantUser();
        $cronId = (int)$id;
        $old    = DB::fetchOne('SELECT id FROM cron_jobs WHERE id = ? AND tenant_id = ?', [$cronId, $tid]);
        if (!$old) Response::abort(404);

        DB::delete('cron_jobs', ['id' => $cronId, 'tenant_id' => $tid]);
        AuditLog::tenant($user['id'], $tid, 'cron.deleted', 'cron_jobs', $cronId);

        Session::flash('success', 'Automação removida.');
        Response::redirect('/app/crons');
    }

    private function collectData(int $tid): array
    {
        $templateVarsRaw = Request::post('template_vars', '');
        $templateVars    = null;
        if ($templateVarsRaw) {
            $decoded = json_decode($templateVarsRaw, true);
            $templateVars = json_encode(is_array($decoded) ? $decoded : array_map('trim', explode(',', $templateVarsRaw)));
        }

        return [
            'tenant_id'     => $tid,
            'agent_id'      => (int)Request::post('agent_id', 0),
            'name'          => trim(Request::post('name', '')),
            'schedule'      => trim(Request::post('schedule', '0 9 * * *')),
            'is_active'     => Request::post('is_active') ? 1 : 0,
            'action_type'   => Request::post('action_type', 'send_template'),
            'template_name' => trim(Request::post('template_name', '')),
            'template_vars' => $templateVars,
            'target_type'   => Request::post('target_type', 'specific_phone'),
            'target_value'  => trim(Request::post('target_value', '')),
            'next_run_at'   => null, // Will be computed by scheduler
        ];
    }
}
