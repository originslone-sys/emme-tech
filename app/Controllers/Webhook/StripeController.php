<?php

declare(strict_types=1);

namespace App\Controllers\Webhook;

use App\Core\DB;
use App\Lib\Logger;
use App\Lib\Stripe;

class StripeController
{
    public function receive(): void
    {
        $rawBody   = file_get_contents('php://input') ?: '';
        $sigHeader = $_SERVER['HTTP_STRIPE_SIGNATURE'] ?? '';
        $secret    = (string)env('STRIPE_WEBHOOK_SECRET', '');

        try {
            $event = Stripe::verifyWebhookSignature($rawBody, $sigHeader, $secret);
        } catch (\Throwable $e) {
            Logger::warning('Stripe webhook signature invalid', ['error' => $e->getMessage()]);
            http_response_code(400);
            echo $e->getMessage();
            exit;
        }

        $eventId   = $event['id']   ?? '';
        $eventType = $event['type'] ?? '';

        // Idempotency — check if already processed
        $alreadyDone = DB::fetchOne(
            'SELECT id FROM stripe_events WHERE stripe_event_id = ? AND processed_at IS NOT NULL',
            [$eventId]
        );
        if ($alreadyDone) {
            http_response_code(200);
            echo 'Already processed';
            exit;
        }

        // Save event
        $existing = DB::fetchOne('SELECT id FROM stripe_events WHERE stripe_event_id = ?', [$eventId]);
        if (!$existing) {
            DB::insert('stripe_events', [
                'stripe_event_id' => $eventId,
                'event_type'      => $eventType,
                'payload'         => $rawBody,
            ]);
        }

        try {
            $this->handleEvent($eventType, $event['data']['object'] ?? []);

            DB::query(
                'UPDATE stripe_events SET processed_at = NOW() WHERE stripe_event_id = ?',
                [$eventId]
            );

            Logger::info('Stripe event processed', ['event' => $eventType, 'id' => $eventId]);
        } catch (\Throwable $e) {
            Logger::error('Stripe event processing failed', ['event' => $eventType, 'error' => $e->getMessage()]);
            http_response_code(500);
            echo 'Processing error';
            exit;
        }

        http_response_code(200);
        echo 'OK';
        exit;
    }

    private function handleEvent(string $type, array $object): void
    {
        switch ($type) {
            case 'checkout.session.completed':
                $this->onCheckoutCompleted($object);
                break;

            case 'customer.subscription.created':
            case 'customer.subscription.updated':
                $this->onSubscriptionUpsert($object);
                break;

            case 'customer.subscription.deleted':
                $this->onSubscriptionDeleted($object);
                break;

            case 'invoice.payment_succeeded':
                $this->onPaymentSucceeded($object);
                break;

            case 'invoice.payment_failed':
                $this->onPaymentFailed($object);
                break;
        }
    }

    private function onCheckoutCompleted(array $session): void
    {
        $customerId   = $session['customer']     ?? '';
        $subId        = $session['subscription'] ?? '';
        $metadata     = $session['metadata']     ?? [];
        $tenantId     = (int)($metadata['tenant_id'] ?? 0);
        $planId       = (int)($metadata['plan_id']   ?? 0);

        if (!$tenantId || !$customerId) return;

        // Ensure stripe_customer record
        $sc = DB::fetchOne('SELECT id FROM stripe_customers WHERE tenant_id = ?', [$tenantId]);
        if (!$sc) {
            DB::insert('stripe_customers', [
                'tenant_id'          => $tenantId,
                'stripe_customer_id' => $customerId,
            ]);
        }

        if ($subId) {
            $this->upsertSubscription($tenantId, $subId, $customerId, $planId);
        }
    }

    private function onSubscriptionUpsert(array $sub): void
    {
        $subId      = $sub['id']       ?? '';
        $customerId = $sub['customer'] ?? '';
        $status     = $sub['status']   ?? 'active';

        if (!$subId || !$customerId) return;

        // Find tenant by customer
        $sc = DB::fetchOne('SELECT tenant_id FROM stripe_customers WHERE stripe_customer_id = ?', [$customerId]);
        if (!$sc) return;

        $tenantId = (int)$sc['tenant_id'];

        // Find plan by price
        $priceId = $sub['items']['data'][0]['price']['id'] ?? '';
        $plan    = null;
        if ($priceId) {
            $plan = DB::fetchOne(
                'SELECT * FROM plans WHERE stripe_price_monthly_id = ? OR stripe_price_yearly_id = ?',
                [$priceId, $priceId]
            );
        }

        $periodStart = isset($sub['current_period_start']) ? date('Y-m-d H:i:s', $sub['current_period_start']) : null;
        $periodEnd   = isset($sub['current_period_end'])   ? date('Y-m-d H:i:s', $sub['current_period_end'])   : null;

        $existing = DB::fetchOne('SELECT id FROM stripe_subscriptions WHERE stripe_subscription_id = ?', [$subId]);
        $subData  = [
            'tenant_id'               => $tenantId,
            'stripe_subscription_id'  => $subId,
            'stripe_customer_id'      => $customerId,
            'plan_id'                 => $plan ? $plan['id'] : null,
            'status'                  => $status,
            'current_period_start'    => $periodStart,
            'current_period_end'      => $periodEnd,
            'cancel_at_period_end'    => $sub['cancel_at_period_end'] ? 1 : 0,
        ];

        if ($existing) {
            DB::update('stripe_subscriptions', $subData, ['id' => $existing['id']]);
        } else {
            DB::insert('stripe_subscriptions', $subData);
        }

        // Update tenant status and plan
        $tenantUpdate = ['status' => $this->mapStripeStatus($status)];
        if ($plan) {
            $tenantUpdate['plan_id'] = $plan['id'];
        }
        DB::update('tenants', $tenantUpdate, ['id' => $tenantId]);
    }

    private function onSubscriptionDeleted(array $sub): void
    {
        $subId      = $sub['id']       ?? '';
        $customerId = $sub['customer'] ?? '';
        if (!$subId) return;

        DB::query(
            "UPDATE stripe_subscriptions SET status = 'canceled' WHERE stripe_subscription_id = ?",
            [$subId]
        );

        $sc = DB::fetchOne('SELECT tenant_id FROM stripe_customers WHERE stripe_customer_id = ?', [$customerId]);
        if ($sc) {
            DB::update('tenants', ['status' => 'canceled'], ['id' => $sc['tenant_id']]);
        }
    }

    private function onPaymentSucceeded(array $invoice): void
    {
        $subId      = $invoice['subscription'] ?? '';
        $customerId = $invoice['customer']     ?? '';
        if (!$customerId) return;

        $sc = DB::fetchOne('SELECT tenant_id FROM stripe_customers WHERE stripe_customer_id = ?', [$customerId]);
        if (!$sc) return;

        DB::update('tenants', ['status' => 'active'], ['id' => $sc['tenant_id']]);
    }

    private function onPaymentFailed(array $invoice): void
    {
        $customerId = $invoice['customer'] ?? '';
        if (!$customerId) return;

        $sc = DB::fetchOne('SELECT tenant_id FROM stripe_customers WHERE stripe_customer_id = ?', [$customerId]);
        if (!$sc) return;

        DB::update('tenants', ['status' => 'past_due'], ['id' => $sc['tenant_id']]);
    }

    private function upsertSubscription(int $tenantId, string $subId, string $customerId, int $planId): void
    {
        $existing = DB::fetchOne('SELECT id FROM stripe_subscriptions WHERE stripe_subscription_id = ?', [$subId]);
        $data     = [
            'tenant_id'              => $tenantId,
            'stripe_subscription_id' => $subId,
            'stripe_customer_id'     => $customerId,
            'plan_id'                => $planId ?: null,
            'status'                 => 'active',
        ];

        if ($existing) {
            DB::update('stripe_subscriptions', $data, ['id' => $existing['id']]);
        } else {
            DB::insert('stripe_subscriptions', $data);
        }

        $tenantUpdate = ['status' => 'active'];
        if ($planId) $tenantUpdate['plan_id'] = $planId;
        DB::update('tenants', $tenantUpdate, ['id' => $tenantId]);
    }

    private function mapStripeStatus(string $status): string
    {
        return match ($status) {
            'active', 'trialing' => 'active',
            'past_due'           => 'past_due',
            'canceled', 'unpaid' => 'canceled',
            default              => 'inactive',
        };
    }
}
