<?php

declare(strict_types=1);

namespace App\Controllers\Admin;

use App\Core\Auth;
use App\Core\DB;
use App\Core\Response;

class DashboardController
{
    public function index(): void
    {
        Auth::requireAdmin();

        $stats = [
            'tenants'  => (int)DB::fetchColumn('SELECT COUNT(*) FROM tenants'),
            'active'   => (int)DB::fetchColumn("SELECT COUNT(*) FROM tenants WHERE status = 'active'"),
            'agents'   => (int)DB::fetchColumn('SELECT COUNT(*) FROM agents'),
            'messages' => (int)DB::fetchColumn('SELECT COUNT(*) FROM messages'),
            'jobs_pending' => (int)DB::fetchColumn("SELECT COUNT(*) FROM jobs WHERE status = 'pending'"),
            'jobs_failed'  => (int)DB::fetchColumn("SELECT COUNT(*) FROM jobs WHERE status = 'failed'"),
        ];

        $recentTenants = DB::fetchAll(
            'SELECT t.*, p.name AS plan_name FROM tenants t
             LEFT JOIN plans p ON p.id = t.plan_id
             ORDER BY t.created_at DESC LIMIT 10'
        );

        Response::view('admin/dashboard', [
            'admin'         => Auth::admin(),
            'stats'         => $stats,
            'recentTenants' => $recentTenants,
        ]);
    }
}
