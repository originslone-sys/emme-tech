<?php

declare(strict_types=1);

namespace App\Controllers\App;

use App\Core\Auth;
use App\Core\DB;
use App\Core\Response;

class DashboardController
{
    public function index(): void
    {
        Auth::requireTenant();

        $user = Auth::tenantUser();
        $tid  = $user['tenant_id'];

        $tenant = DB::fetchOne('SELECT * FROM tenants WHERE id = ?', [$tid]);

        $stats = [
            'agents'         => (int)DB::fetchColumn('SELECT COUNT(*) FROM agents WHERE tenant_id = ?', [$tid]),
            'contacts'       => (int)DB::fetchColumn('SELECT COUNT(*) FROM contacts WHERE tenant_id = ?', [$tid]),
            'messages_today' => (int)DB::fetchColumn(
                "SELECT COUNT(*) FROM messages WHERE tenant_id = ? AND DATE(created_at) = CURDATE()",
                [$tid]
            ),
            'threads_open'   => (int)DB::fetchColumn(
                "SELECT COUNT(*) FROM threads WHERE tenant_id = ? AND status = 'open'",
                [$tid]
            ),
        ];

        $agents = DB::fetchAll(
            'SELECT id, name, status, whatsapp_mode, whatsapp_phone_number_id, evo_instance_name, persona_id
             FROM agents WHERE tenant_id = ?',
            [$tid]
        );

        $hasWA      = false;
        $hasPersona = false;
        foreach ($agents as $a) {
            if ($a['whatsapp_phone_number_id'] || $a['evo_instance_name']) $hasWA = true;
            if ($a['persona_id']) $hasPersona = true;
        }
        $hasDocs = (int)DB::fetchColumn(
            "SELECT COUNT(*) FROM kb_docs WHERE tenant_id = ? AND status = 'ready'",
            [$tid]
        ) > 0;

        $checklist = [
            'whatsapp' => $hasWA,
            'persona'  => $hasPersona,
            'docs'     => $hasDocs,
            'message'  => $stats['messages_today'] > 0,
        ];

        Response::view('app/dashboard', [
            'user'      => $user,
            'tenant'    => $tenant,
            'credits'   => (int)($tenant['credits'] ?? 0),
            'stats'     => $stats,
            'agents'    => $agents,
            'checklist' => $checklist,
        ]);
    }
}
