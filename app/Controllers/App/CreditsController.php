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
use App\Lib\GlobalSettings;
use App\Lib\MercadoPago;

class CreditsController
{
    public function index(): void
    {
        Auth::requireTenant();
        $tid    = Auth::tenantId();
        $user   = Auth::tenantUser();
        $tenant = DB::fetchOne('SELECT * FROM tenants WHERE id = ?', [$tid]);

        $packages = DB::fetchAll(
            'SELECT * FROM credit_packages WHERE is_active = 1 ORDER BY sort_order, credits'
        );

        $transactions = DB::fetchAll(
            'SELECT * FROM credit_transactions WHERE tenant_id = ? ORDER BY created_at DESC LIMIT 30',
            [$tid]
        );

        $mpPublicKey = GlobalSettings::get('mp_public_key');

        Response::view('app/credits', [
            'user'         => $user,
            'tenant'       => $tenant,
            'packages'     => $packages,
            'transactions' => $transactions,
            'mpPublicKey'  => $mpPublicKey,
            'csrf'         => CSRF::field(),
        ]);
    }

    /**
     * Inicia compra de créditos via Mercado Pago.
     * POST /app/credits/buy
     */
    public function buy(): void
    {
        Auth::requireTenant();
        CSRF::verifyRequest();

        $tid       = Auth::tenantId();
        $user      = Auth::tenantUser();
        $packageId = (int)Request::post('package_id', 0);

        $package = DB::fetchOne(
            'SELECT * FROM credit_packages WHERE id = ? AND is_active = 1',
            [$packageId]
        );

        if (!$package) {
            Session::flash('error', 'Pacote de créditos não encontrado.');
            Response::redirect('/app/credits');
        }

        try {
            $mp     = MercadoPago::fromSettings();
            $appUrl = env('APP_URL', '');

            $preference = $mp->createPreference(
                title:      $package['name'] . ' — ' . number_format($package['credits']) . ' créditos',
                quantity:   1,
                unitPrice:  (float)$package['price_brl'],
                metadata:   [
                    'tenant_id'  => $tid,
                    'package_id' => $package['id'],
                    'credits'    => $package['credits'],
                ],
                successUrl: $appUrl . '/app/credits?success=1',
                failureUrl: $appUrl . '/app/credits?error=1',
                pendingUrl: $appUrl . '/app/credits?pending=1',
                notifUrl:   $appUrl . '/webhook/mercadopago'
            );

            // Registra pagamento pendente
            $paymentRecId = DB::insert('mp_payments', [
                'tenant_id'  => $tid,
                'package_id' => $package['id'],
                'mp_pref_id' => $preference['id'],
                'amount_brl' => $package['price_brl'],
                'credits'    => $package['credits'],
                'status'     => 'pending',
            ]);

            AuditLog::tenant($user['id'], $tid, 'billing.checkout_started', 'mp_payment', (int)$paymentRecId);

            $checkoutUrl = $preference['init_point'] ?? '';
            if (!$checkoutUrl) {
                throw new \RuntimeException('URL de checkout não retornada pelo Mercado Pago.');
            }

            Response::redirect($checkoutUrl);

        } catch (\Throwable $e) {
            Session::flash('error', 'Erro ao iniciar pagamento: ' . $e->getMessage());
            Response::redirect('/app/credits');
        }
    }

    /**
     * Histórico completo de transações.
     * GET /app/credits/history
     */
    public function history(): void
    {
        Auth::requireTenant();
        $tid    = Auth::tenantId();
        $user   = Auth::tenantUser();
        $tenant = DB::fetchOne('SELECT * FROM tenants WHERE id = ?', [$tid]);

        $transactions = DB::fetchAll(
            'SELECT * FROM credit_transactions WHERE tenant_id = ? ORDER BY created_at DESC LIMIT 200',
            [$tid]
        );

        Response::view('app/credits_history', [
            'user'         => $user,
            'tenant'       => $tenant,
            'transactions' => $transactions,
        ]);
    }
}
