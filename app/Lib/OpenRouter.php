<?php

declare(strict_types=1);

namespace App\Lib;

use RuntimeException;

/**
 * OpenRouter — Chat Completions client via cURL.
 */
class OpenRouter
{
    private string $apiKey;
    private string $apiUrl;

    public function __construct(string $apiKey)
    {
        $this->apiKey = $apiKey;
        $this->apiUrl = (string)env('OPENROUTER_API_URL', 'https://openrouter.ai/api/v1/chat/completions');
    }

    /**
     * Send a chat completion request.
     *
     * @param string $model     OpenRouter model ID (e.g. openai/gpt-4o-mini)
     * @param array  $messages  Array of {role, content} messages
     * @param float  $temperature
     * @param int    $maxTokens
     * @return string           The assistant reply text
     */
    public function chat(
        string $model,
        array  $messages,
        float  $temperature = 0.7,
        int    $maxTokens   = 1024
    ): string {
        $payload = [
            'model'       => $model,
            'messages'    => $messages,
            'temperature' => $temperature,
            'max_tokens'  => $maxTokens,
        ];

        $response = $this->request($payload);

        $text = $response['choices'][0]['message']['content'] ?? null;
        if ($text === null) {
            throw new RuntimeException('OpenRouter returned no content. Response: ' . json_encode($response));
        }

        return trim($text);
    }

    /**
     * Raw HTTP POST to OpenRouter API.
     */
    public function request(array $payload): array
    {
        $ch = curl_init($this->apiUrl);
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_POST           => true,
            CURLOPT_POSTFIELDS     => json_encode($payload),
            CURLOPT_HTTPHEADER     => [
                'Authorization: Bearer ' . $this->apiKey,
                'Content-Type: application/json',
                'HTTP-Referer: ' . APP_URL,
                'X-Title: WhatsApp AI Manager',
            ],
            CURLOPT_TIMEOUT        => 60,
            CURLOPT_CONNECTTIMEOUT => 10,
        ]);

        $raw    = curl_exec($ch);
        $status = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $error  = curl_error($ch);
        curl_close($ch);

        if ($error) {
            throw new RuntimeException("cURL error: $error");
        }

        $data = json_decode($raw ?: '{}', true);

        if ($status >= 400) {
            $msg = $data['error']['message'] ?? $raw;
            throw new RuntimeException("OpenRouter API error ($status): $msg");
        }

        return $data ?? [];
    }

    /**
     * Build the OpenRouter client for an agent, resolving the token priority:
     * 1. Agent override token (encrypted)
     * 2. Tenant default token (encrypted)
     * 3. Global default token from .env
     */
    public static function forAgent(array $agent, int $tenantId): self
    {
        // Agent-level override
        if (!empty($agent['openrouter_token_override_enc'])) {
            $token = Crypto::tryDecrypt($agent['openrouter_token_override_enc']);
            if ($token) return new self($token);
        }

        // Tenant default token
        $row = \App\Core\DB::fetchOne(
            'SELECT token_encrypted FROM openrouter_tokens WHERE tenant_id = ? AND is_default = 1 LIMIT 1',
            [$tenantId]
        );
        if ($row) {
            $token = Crypto::tryDecrypt($row['token_encrypted']);
            if ($token) return new self($token);
        }

        // Global fallback
        $global = env('OPENROUTER_DEFAULT_TOKEN', '');
        if ($global) return new self($global);

        throw new RuntimeException("No OpenRouter token configured for tenant $tenantId.");
    }
}
