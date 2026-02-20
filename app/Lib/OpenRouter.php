<?php

declare(strict_types=1);

namespace App\Lib;

use RuntimeException;

/**
 * OpenRouter — cliente via cURL.
 * O token é sempre o global configurado pelo admin em global_settings.
 */
class OpenRouter
{
    private string $apiKey;
    private string $apiUrl;

    public function __construct(string $apiKey, string $apiUrl = 'https://openrouter.ai/api/v1')
    {
        $this->apiKey = $apiKey;
        $this->apiUrl = rtrim($apiUrl, '/');
    }

    /**
     * Envia uma requisição de chat completion.
     */
    public function chat(string $model, array $messages, float $temperature = 0.7, int $maxTokens = 1024): string
    {
        $payload = [
            'model'       => $model,
            'messages'    => $messages,
            'temperature' => $temperature,
            'max_tokens'  => $maxTokens,
        ];

        $data = $this->request($payload);

        $content = $data['choices'][0]['message']['content'] ?? '';
        if (!$content) {
            throw new RuntimeException('OpenRouter returned empty response. Raw: ' . json_encode($data));
        }

        return $content;
    }

    /**
     * POST direto para a API do OpenRouter.
     */
    public function request(array $payload): array
    {
        $url = $this->apiUrl . '/chat/completions';

        $ch = curl_init($url);
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_POST           => true,
            CURLOPT_POSTFIELDS     => json_encode($payload),
            CURLOPT_HTTPHEADER     => [
                'Authorization: Bearer ' . $this->apiKey,
                'Content-Type: application/json',
                'HTTP-Referer: ' . env('APP_URL', 'https://emmetech.digital'),
                'X-Title: EMME Tech Agent',
            ],
            CURLOPT_TIMEOUT        => 60,
            CURLOPT_CONNECTTIMEOUT => 10,
        ]);

        $raw    = curl_exec($ch);
        $status = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $error  = curl_error($ch);
        curl_close($ch);

        if ($error) {
            throw new RuntimeException("OpenRouter cURL error: $error");
        }

        $data = json_decode($raw ?: '{}', true) ?? [];

        if ($status >= 400) {
            $msg = $data['error']['message'] ?? $raw;
            throw new RuntimeException("OpenRouter API error ($status): $msg");
        }

        return $data;
    }
}
