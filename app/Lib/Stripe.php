<?php

declare(strict_types=1);

namespace App\Lib;

use RuntimeException;

/**
 * Stripe — lightweight API client via cURL (no SDK dependency).
 */
class Stripe
{
    private const API_BASE = 'https://api.stripe.com/v1';

    private string $secretKey;

    public function __construct(string $secretKey = '')
    {
        $this->secretKey = $secretKey ?: (string)env('STRIPE_SECRET_KEY', '');
    }

    // ----------------------------------------------------------------
    // Customers
    // ----------------------------------------------------------------

    public function createCustomer(string $email, string $name): array
    {
        return $this->post('/customers', ['email' => $email, 'name' => $name]);
    }

    public function getCustomer(string $customerId): array
    {
        return $this->get("/customers/$customerId");
    }

    // ----------------------------------------------------------------
    // Checkout Session
    // ----------------------------------------------------------------

    public function createCheckoutSession(
        string $customerId,
        string $priceId,
        string $successUrl,
        string $cancelUrl,
        array  $metadata = []
    ): array {
        return $this->post('/checkout/sessions', [
            'customer'             => $customerId,
            'mode'                 => 'subscription',
            'payment_method_types' => ['card'],
            'line_items'           => [['price' => $priceId, 'quantity' => 1]],
            'success_url'          => $successUrl,
            'cancel_url'           => $cancelUrl,
            'metadata'             => $metadata,
        ]);
    }

    // ----------------------------------------------------------------
    // Customer Portal
    // ----------------------------------------------------------------

    public function createPortalSession(string $customerId, string $returnUrl): array
    {
        return $this->post('/billing_portal/sessions', [
            'customer'   => $customerId,
            'return_url' => $returnUrl,
        ]);
    }

    // ----------------------------------------------------------------
    // Subscriptions
    // ----------------------------------------------------------------

    public function getSubscription(string $subscriptionId): array
    {
        return $this->get("/subscriptions/$subscriptionId");
    }

    public function cancelSubscription(string $subscriptionId): array
    {
        return $this->delete("/subscriptions/$subscriptionId");
    }

    // ----------------------------------------------------------------
    // Webhook signature verification
    // ----------------------------------------------------------------

    public static function verifyWebhookSignature(string $payload, string $sigHeader, string $secret): array
    {
        $parts = [];
        foreach (explode(',', $sigHeader) as $part) {
            [$k, $v] = explode('=', trim($part), 2);
            $parts[$k][] = $v;
        }

        $timestamp = (int)($parts['t'][0] ?? 0);
        $signatures = $parts['v1'] ?? [];

        if (abs(time() - $timestamp) > 300) {
            throw new RuntimeException('Stripe webhook timestamp is too old.');
        }

        $signed  = $timestamp . '.' . $payload;
        $expected = hash_hmac('sha256', $signed, $secret);

        foreach ($signatures as $sig) {
            if (hash_equals($expected, $sig)) {
                $data = json_decode($payload, true);
                if (!$data) throw new RuntimeException('Invalid Stripe webhook JSON.');
                return $data;
            }
        }

        throw new RuntimeException('Stripe webhook signature mismatch.');
    }

    // ----------------------------------------------------------------
    // HTTP helpers
    // ----------------------------------------------------------------

    private function post(string $endpoint, array $data): array
    {
        return $this->request('POST', $endpoint, $data);
    }

    private function get(string $endpoint): array
    {
        return $this->request('GET', $endpoint);
    }

    private function delete(string $endpoint): array
    {
        return $this->request('DELETE', $endpoint);
    }

    private function request(string $method, string $endpoint, array $data = []): array
    {
        $url  = self::API_BASE . $endpoint;
        $body = '';

        if ($data && $method !== 'GET') {
            $body = $this->buildQuery($data);
        } elseif ($data) {
            $url .= '?' . $this->buildQuery($data);
        }

        $ch = curl_init($url);
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_CUSTOMREQUEST  => $method,
            CURLOPT_HTTPHEADER     => [
                'Authorization: Bearer ' . $this->secretKey,
                'Content-Type: application/x-www-form-urlencoded',
                'Stripe-Version: 2024-04-10',
            ],
            CURLOPT_TIMEOUT        => 30,
            CURLOPT_CONNECTTIMEOUT => 10,
        ]);

        if ($body) {
            curl_setopt($ch, CURLOPT_POSTFIELDS, $body);
        }

        $raw    = curl_exec($ch);
        $status = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $error  = curl_error($ch);
        curl_close($ch);

        if ($error) throw new RuntimeException("Stripe cURL error: $error");

        $resp = json_decode($raw ?: '{}', true) ?? [];

        if ($status >= 400) {
            $msg = $resp['error']['message'] ?? $raw;
            throw new RuntimeException("Stripe API error ($status): $msg");
        }

        return $resp;
    }

    /**
     * Recursively build URL-encoded query string (handles nested arrays).
     */
    private function buildQuery(array $data, string $prefix = ''): string
    {
        $parts = [];
        foreach ($data as $key => $value) {
            $fullKey = $prefix ? "{$prefix}[{$key}]" : $key;
            if (is_array($value)) {
                $parts[] = $this->buildQuery($value, $fullKey);
            } else {
                $parts[] = urlencode($fullKey) . '=' . urlencode((string)$value);
            }
        }
        return implode('&', $parts);
    }
}
