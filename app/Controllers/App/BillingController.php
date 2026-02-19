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
use App\Lib\Stripe;

class BillingController
{
    public function index(): void
    {
        Auth::requireTenant();
        $tid    = Auth::tenantUser()['tenant_id'];
        $tenant = DB::fetchOne('SELECT * FROM tenants WHERE id = ?', [$tid]);
        $plan   = Auth::tenantPlan();

        $subscription = DB::fetchOne(
            'SELECT * FROM stripe_subscriptions WHERE tenant_id = ? ORDER BY id DESC LIMIT 1',
            [$tid]
        );

        $plans = DB::fetchAll('SELECT * FROM plans WHERE is_active = 1 ORDER BY sort_order');

        $stripeCustomer = DB::fetchOne(
            'SELECT * FROM stripe_customers WHERE tenant_id = ?', [$tid]
        );

        Response::view('app/billing', [
            'user'           => Auth::tenantUser(),
            'tenant'         => $tenant,
            'plan'           => $plan,
            'subscription'   => $subscription,
            'plans'          => $plans,
            'stripeCustomer' => $stripeCustomer,
            'stripePubKey'   => env('STRIPE_PUBLISHABLE_KEY', ''),
            'csrf'           => CSRF::field(),
        ]);
    }

    public function checkout(): void
    {
        Auth::requireTenant();
        CSRF::verifyRequest();

        $tid    = Auth::tenantUser()['tenant_id'];
        $user   = Auth::tenantUser();
        $priceId = Request::post('price_id', '');
        $interval = Request::post('interval', 'monthly');

        if (!$priceId) {
            Session::flash('error', 'Plano inválido.');
            Response::redirect('/app/billing');
        }

        // Validate the price_id belongs to a real plan
        $plan = DB::fetchOne(
            'SELECT * FROM plans WHERE (stripe_price_monthly_id = ? OR stripe_price_yearly_id = ?) AND is_active = 1',
            [$priceId, $priceId]
        );
        if (!$plan) {
            Session::flash('error', 'Plano não encontrado.');
            Response::redirect('/app/billing');
        }

        $tenant = DB::fetchOne('SELECT * FROM tenants WHERE id = ?', [$tid]);

        try {
            $stripe = new Stripe();

            // Get or create Stripe customer
            $sc = DB::fetchOne('SELECT * FROM stripe_customers WHERE tenant_id = ?', [$tid]);
            if (!$sc) {
                $customer = $stripe->createCustomer($tenant['email'], $tenant['name']);
                DB::insert('stripe_customers', [
                    'tenant_id'          => $tid,
                    'stripe_customer_id' => $customer['id'],
                ]);
                $customerId = $customer['id'];
            } else {
                $customerId = $sc['stripe_customer_id'];
            }

            $successUrl = env('STRIPE_SUCCESS_URL', APP_URL . '/app/billing?success=1');
            $cancelUrl  = env('STRIPE_CANCEL_URL', APP_URL . '/app/billing?canceled=1');

            $session = $stripe->createCheckoutSession(
                $customerId,
                $priceId,
                $successUrl,
                $cancelUrl,
                ['tenant_id' => (string)$tid, 'plan_id' => (string)$plan['id']]
            );

            AuditLog::tenant($user['id'], $tid, 'billing.checkout_started', 'stripe', $plan['id']);

            Response::redirect($session['url']);
        } catch (\Throwable $e) {
            Session::flash('error', 'Erro ao criar sessão de pagamento: ' . $e->getMessage());
            Response::redirect('/app/billing');
        }
    }

    public function portal(): void
    {
        Auth::requireTenant();
        CSRF::verifyRequest();

        $tid  = Auth::tenantUser()['tenant_id'];
        $sc   = DB::fetchOne('SELECT * FROM stripe_customers WHERE tenant_id = ?', [$tid]);

        if (!$sc) {
            Session::flash('error', 'Nenhuma assinatura encontrada.');
            Response::redirect('/app/billing');
        }

        try {
            $stripe  = new Stripe();
            $portal  = $stripe->createPortalSession($sc['stripe_customer_id'], APP_URL . '/app/billing');
            Response::redirect($portal['url']);
        } catch (\Throwable $e) {
            Session::flash('error', 'Erro ao abrir portal de assinatura: ' . $e->getMessage());
            Response::redirect('/app/billing');
        }
    }
}
