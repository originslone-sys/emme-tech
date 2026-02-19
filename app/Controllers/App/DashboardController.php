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

        $user  = Auth::tenantUser();
        $tid   = $user['tenant_id'];
        $plan  = Auth::tenantPlan();

        $tenant = DB::fetchOne('SELECT * FROM tenants WHERE id = ?', [$tid]);

        $stats = [
            'agents'   => (int)DB::fetchColumn('SELECT COUNT(*) FROM agents WHERE tenant_id = ?', [$tid]),
            'contacts' => (int)DB::fetchColumn('SELECT COUNT(*) FROM contacts WHERE tenant_id = ?', [$tid]),
            'messages_today' => (int)DB::fetchColumn(
                "SELECT COUNT(*) FROM messages WHERE tenant_id = ? AND DATE(created_at) = CURDATE()",
                [$tid]
            ),
            'threads_open' => (int)DB::fetchColumn(
                "SELECT COUNT(*) FROM threads WHERE tenant_id = ? AND status = 'open'",
                [$tid]
            ),
        ];

        // Onboarding checklist
        $agents = DB::fetchAll(
            'SELECT id, name, status, whatsapp_phone_number_id, persona_id FROM agents WHERE tenant_id = ?',
            [$tid]
        );

        $hasWA      = false;
        $hasPersona = false;
        foreach ($agents as $a) {
            if ($a['whatsapp_phone_number_id']) $hasWA = true;
            if ($a['persona_id']) $hasPersona = true;
        }
        $hasDocs = DB::fetchColumn(
            "SELECT COUNT(*) FROM kb_docs WHERE tenant_id = ? AND status = 'ready'",
            [$tid]
        ) > 0;

        $checklist = [
            'whatsapp' => $hasWA,
            'persona'  => $hasPersona,
            'docs'     => $hasDocs,
            'message'  => $stats['messages_today'] > 0,
        ];

        // Stripe subscription info
        $subscription = DB::fetchOne(
            'SELECT ss.*, p.name AS plan_name
             FROM stripe_subscriptions ss
             LEFT JOIN plans p ON p.stripe_price_monthly_id = ss.stripe_subscription_id
             WHERE ss.tenant_id = ?
             ORDER BY ss.id DESC LIMIT 1',
            [$tid]
        );

        Response::view('app/dashboard', [
            'user'         => $user,
            'tenant'       => $tenant,
            'plan'         => $plan,
            'stats'        => $stats,
            'agents'       => $agents,
            'checklist'    => $checklist,
            'subscription' => $subscription,
        ]);
    }
}
