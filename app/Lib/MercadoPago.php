<?php

declare(strict_types=1);

namespace App\Lib;

use RuntimeException;

/**
 * MercadoPago — integração com a API do Mercado Pago via cURL.
 * Usa Checkout Pro (preferências de pagamento).
 */
class MercadoPago
{
    private const API_BASE = 'https://api.mercadopago.com';

    private string $accessToken;

    public function __construct(string $accessToken)
    {
        $this->accessToken = $accessToken;
    }

    /**
     * Cria uma preferência de pagamento (Checkout Pro).
     *
     * @param string $title       Título do item
     * @param int    $quantity    Quantidade
     * @param float  $unitPrice   Preço unitário em BRL
     * @param array  $metadata    Dados extras (tenant_id, package_id, etc.)
     * @param string $successUrl  URL de retorno após pagamento aprovado
     * @param string $failureUrl  URL de retorno após falha
     * @param string $pendingUrl  URL de retorno para pagamentos pendentes
     * @param string $notifUrl    URL de notificação IPN/webhook
     */
    public function createPreference(
        string $title,
        int    $quantity,
        float  $unitPrice,
        array  $metadata,
        string $successUrl,
        string $failureUrl,
        string $pendingUrl,
        string $notifUrl
    ): array {
        $payload = [
            'items' => [[
                'title'       => $title,
                'quantity'    => $quantity,
                'unit_price'  => $unitPrice,
                'currency_id' => 'BRL',
            ]],
            'metadata'  => $metadata,
            'back_urls' => [
                'success' => $successUrl,
                'failure' => $failureUrl,
                'pending' => $pendingUrl,
            ],
            'auto_return'      => 'approved',
            'notification_url' => $notifUrl,
        ];

        return $this->post('/checkout/preferences', $payload);
    }

    /**
     * Busca informações de um pagamento pelo ID.
     */
    public function getPayment(string $paymentId): array
    {
        return $this->get("/v1/payments/{$paymentId}");
    }

    /**
     * Valida a assinatura do webhook do Mercado Pago.
     * Header x-signature: ts=...,v1=...
     */
    public static function verifySignature(
        string $rawBody,
        string $xSignature,
        string $xRequestId,
        string $secret
    ): bool {
        // Extrai ts e v1
        $parts = [];
        foreach (explode(',', $xSignature) as $part) {
            [$k, $v] = array_map('trim', explode('=', $part, 2));
            $parts[$k] = $v;
        }

        if (empty($parts['ts']) || empty($parts['v1'])) {
            return false;
        }

        $manifest = "id:{$xRequestId};request-id:{$xRequestId};ts:{$parts['ts']};";
        $expected = hash_hmac('sha256', $manifest, $secret);

        return hash_equals($expected, $parts['v1']);
    }

    /**
     * Instancia a partir das configurações globais do banco.
     */
    public static function fromSettings(): self
    {
        $token = GlobalSettings::get('mp_access_token');
        if (!$token) {
            throw new RuntimeException('Mercado Pago: access token não configurado.');
        }
        return new self($token);
    }

    // ----------------------------------------------------------------
    // HTTP helpers
    // ----------------------------------------------------------------

    private function post(string $path, array $data): array
    {
        return $this->request('POST', $path, $data);
    }

    private function get(string $path): array
    {
        return $this->request('GET', $path);
    }

    private function request(string $method, string $path, array $data = []): array
    {
        $url = self::API_BASE . $path;

        $ch = curl_init($url);
        $opts = [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_HTTPHEADER     => [
                'Authorization: Bearer ' . $this->accessToken,
                'Content-Type: application/json',
                'X-Idempotency-Key: ' . bin2hex(random_bytes(16)),
            ],
            CURLOPT_TIMEOUT        => 30,
            CURLOPT_CONNECTTIMEOUT => 10,
        ];

        if ($method === 'POST') {
            $opts[CURLOPT_POST]       = true;
            $opts[CURLOPT_POSTFIELDS] = json_encode($data);
        }

        curl_setopt_array($ch, $opts);
        $raw    = curl_exec($ch);
        $status = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $error  = curl_error($ch);
        curl_close($ch);

        if ($error) {
            throw new RuntimeException("MercadoPago cURL error: $error");
        }

        $result = json_decode($raw ?: '{}', true) ?? [];

        if ($status >= 400) {
            $msg = $result['message'] ?? $result['error'] ?? $raw;
            throw new RuntimeException("MercadoPago API error ($status): $msg");
        }

        return $result;
    }
}
