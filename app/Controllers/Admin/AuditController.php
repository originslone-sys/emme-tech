<?php

declare(strict_types=1);

namespace App\Controllers\Admin;

use App\Core\Auth;
use App\Core\DB;
use App\Core\Request;
use App\Core\Response;

class AuditController
{
    public function index(): void
    {
        Auth::requireAdmin();

        $page    = max(1, (int)Request::get('page', 1));
        $perPage = 50;
        $offset  = ($page - 1) * $perPage;

        $actorType = Request::get('actor_type', '');
        $action    = Request::get('action', '');
        $where     = ['1=1'];
        $params    = [];

        if ($actorType) {
            $where[] = 'actor_type = ?';
            $params[] = $actorType;
        }
        if ($action) {
            $where[] = 'action LIKE ?';
            $params[] = "%$action%";
        }

        $total = (int)DB::fetchColumn(
            'SELECT COUNT(*) FROM audit_log WHERE ' . implode(' AND ', $where),
            $params
        );

        $logs = DB::fetchAll(
            'SELECT a.*, t.name AS tenant_name
             FROM audit_log a
             LEFT JOIN tenants t ON t.id = a.tenant_id
             WHERE ' . implode(' AND ', $where) . '
             ORDER BY a.created_at DESC
             LIMIT ? OFFSET ?',
            [...$params, $perPage, $offset]
        );

        Response::view('admin/audit', [
            'admin'     => Auth::admin(),
            'logs'      => $logs,
            'total'     => $total,
            'page'      => $page,
            'perPage'   => $perPage,
            'actorType' => $actorType,
            'action'    => $action,
        ]);
    }
}
