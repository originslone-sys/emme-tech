<?php

declare(strict_types=1);

namespace App\Lib;

use RuntimeException;

/**
 * WhatsApp — Cloud API client via cURL.
 */
class WhatsApp
{
    private const API_BASE = 'https://graph.facebook.com/v19.0';

    private string $phoneNumberId;
    private string $accessToken;

    public function __construct(string $phoneNumberId, string $accessToken)
    {
        $this->phoneNumberId = $phoneNumberId;
        $this->accessToken   = $accessToken;
    }

    /**
     * Send a free-form text message (only within 24h window).
     */
    public function sendText(string $to, string $text): array
    {
        return $this->send([
            'messaging_product' => 'whatsapp',
            'recipient_type'    => 'individual',
            'to'                => $to,
            'type'              => 'text',
            'text'              => ['body' => $text, 'preview_url' => false],
        ]);
    }

    /**
     * Send a template message (required outside 24h window).
     */
    public function sendTemplate(string $to, string $templateName, array $vars = [], string $lang = 'pt_BR'): array
    {
        $components = [];
        if (!empty($vars)) {
            $params = array_map(fn($v) => ['type' => 'text', 'text' => (string)$v], $vars);
            $components[] = ['type' => 'body', 'parameters' => $params];
        }

        return $this->send([
            'messaging_product' => 'whatsapp',
            'to'                => $to,
            'type'              => 'template',
            'template'          => [
                'name'       => $templateName,
                'language'   => ['code' => $lang],
                'components' => $components,
            ],
        ]);
    }

    /**
     * Mark message as read.
     */
    public function markRead(string $messageId): array
    {
        return $this->send([
            'messaging_product' => 'whatsapp',
            'status'            => 'read',
            'message_id'        => $messageId,
        ]);
    }

    /**
     * Raw POST to WhatsApp API.
     */
    public function send(array $payload): array
    {
        $url = self::API_BASE . "/{$this->phoneNumberId}/messages";

        $ch = curl_init($url);
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_POST           => true,
            CURLOPT_POSTFIELDS     => json_encode($payload),
            CURLOPT_HTTPHEADER     => [
                'Authorization: Bearer ' . $this->accessToken,
                'Content-Type: application/json',
            ],
            CURLOPT_TIMEOUT        => 30,
            CURLOPT_CONNECTTIMEOUT => 10,
        ]);

        $raw    = curl_exec($ch);
        $status = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $error  = curl_error($ch);
        curl_close($ch);

        if ($error) {
            throw new RuntimeException("WhatsApp cURL error: $error");
        }

        $data = json_decode($raw ?: '{}', true) ?? [];

        if ($status >= 400) {
            $msg = $data['error']['message'] ?? $raw;
            throw new RuntimeException("WhatsApp API error ($status): $msg");
        }

        return $data;
    }

    /**
     * Verify webhook signature from Meta.
     */
    public static function verifySignature(string $payload, string $signature, string $appSecret): bool
    {
        if (!str_starts_with($signature, 'sha256=')) {
            return false;
        }
        $expected = 'sha256=' . hash_hmac('sha256', $payload, $appSecret);
        return hash_equals($expected, $signature);
    }

    /**
     * Build WhatsApp client from an agent row.
     */
    public static function forAgent(array $agent): self
    {
        $phoneId = $agent['whatsapp_phone_number_id'] ?? '';
        $tokenEnc = $agent['whatsapp_access_token_encrypted'] ?? '';

        if (!$phoneId || !$tokenEnc) {
            throw new RuntimeException("Agent {$agent['id']} has no WhatsApp credentials.");
        }

        $token = Crypto::tryDecrypt($tokenEnc);
        if (!$token) {
            throw new RuntimeException("Cannot decrypt WhatsApp token for agent {$agent['id']}.");
        }

        return new self($phoneId, $token);
    }

    /**
     * Check if we are within the 24-hour messaging window.
     */
    public static function inFreeWindow(?string $lastInboundAt): bool
    {
        if (!$lastInboundAt) return false;
        $ts = strtotime($lastInboundAt);
        return $ts !== false && (time() - $ts) < 86400;
    }
}
