<?php

declare(strict_types=1);

namespace App\Lib;

use RuntimeException;

/**
 * EvolutionAPI — cliente REST para a Evolution API (WhatsApp Web).
 * Compatível com Evolution API v2.x
 *
 * Documentação: https://doc.evolution-api.com
 */
class EvolutionAPI
{
    private string $baseUrl;
    private string $apiKey;

    public function __construct(string $baseUrl, string $apiKey)
    {
        $this->baseUrl = rtrim($baseUrl, '/');
        $this->apiKey  = $apiKey;
    }

    // ----------------------------------------------------------------
    // Gerenciamento de instâncias
    // ----------------------------------------------------------------

    /**
     * Cria uma nova instância do WhatsApp Web.
     */
    public function createInstance(string $instanceName, string $webhookUrl = ''): array
    {
        $payload = [
            'instanceName' => $instanceName,
            'qrcode'       => true,
        ];

        if ($webhookUrl) {
            $payload['webhook'] = [
                'url'     => $webhookUrl,
                'enabled' => true,
                'events'  => ['MESSAGES_UPSERT', 'CONNECTION_UPDATE'],
            ];
        }

        return $this->post('/instance/create', $payload);
    }

    /**
     * Obtém o QR code de conexão de uma instância.
     * Retorna array com 'base64' (imagem) e 'code' (texto do QR).
     */
    public function getQRCode(string $instanceName): array
    {
        return $this->get("/instance/connect/{$instanceName}");
    }

    /**
     * Retorna o estado de conexão da instância.
     * Possíveis: open, close, connecting
     */
    public function getConnectionState(string $instanceName): array
    {
        return $this->get("/instance/connectionState/{$instanceName}");
    }

    /**
     * Desconecta (logout) uma instância.
     */
    public function logoutInstance(string $instanceName): array
    {
        return $this->delete("/instance/logout/{$instanceName}");
    }

    /**
     * Remove permanentemente uma instância.
     */
    public function deleteInstance(string $instanceName): array
    {
        return $this->delete("/instance/delete/{$instanceName}");
    }

    // ----------------------------------------------------------------
    // Envio de mensagens
    // ----------------------------------------------------------------

    /**
     * Envia uma mensagem de texto.
     *
     * @param string $instanceName Nome da instância
     * @param string $to           Número no formato 5511999999999 (sem @s.whatsapp.net)
     * @param string $text         Texto da mensagem
     */
    public function sendText(string $instanceName, string $to, string $text): array
    {
        // Normaliza o número
        $number = $this->normalizePhone($to);

        return $this->post("/message/sendText/{$instanceName}", [
            'number'  => $number,
            'options' => ['delay' => 200],
            'textMessage' => ['text' => $text],
        ]);
    }

    /**
     * Marca mensagem como lida.
     */
    public function markRead(string $instanceName, array $messageKeys): array
    {
        return $this->post("/message/markMessageAsRead/{$instanceName}", [
            'readMessages' => $messageKeys,
        ]);
    }

    // ----------------------------------------------------------------
    // Helpers
    // ----------------------------------------------------------------

    /**
     * Normaliza número de telefone para formato Evolution API.
     * Remove @s.whatsapp.net e garante apenas dígitos.
     */
    private function normalizePhone(string $phone): string
    {
        $phone = str_replace('@s.whatsapp.net', '', $phone);
        $phone = preg_replace('/[^0-9]/', '', $phone);
        return $phone;
    }

    /**
     * Instancia a partir das configurações globais do banco.
     */
    public static function fromSettings(): self
    {
        $url = GlobalSettings::get('evo_api_url');
        $key = GlobalSettings::get('evo_api_key');

        if (!$url || !$key) {
            throw new RuntimeException('Evolution API: URL ou chave não configuradas nas configurações globais.');
        }

        return new self($url, $key);
    }

    /**
     * Gera o nome de instância para um agente.
     * Formato: t{tenant_id}a{agent_id}
     */
    public static function instanceName(int $tenantId, int $agentId): string
    {
        return "t{$tenantId}a{$agentId}";
    }

    // ----------------------------------------------------------------
    // HTTP helpers
    // ----------------------------------------------------------------

    private function get(string $path): array
    {
        return $this->request('GET', $path);
    }

    private function post(string $path, array $data = []): array
    {
        return $this->request('POST', $path, $data);
    }

    private function delete(string $path): array
    {
        return $this->request('DELETE', $path);
    }

    private function request(string $method, string $path, array $data = []): array
    {
        $url = $this->baseUrl . $path;

        $ch   = curl_init($url);
        $opts = [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_CUSTOMREQUEST  => $method,
            CURLOPT_HTTPHEADER     => [
                'apikey: ' . $this->apiKey,
                'Content-Type: application/json',
            ],
            CURLOPT_TIMEOUT        => 30,
            CURLOPT_CONNECTTIMEOUT => 10,
        ];

        if (!empty($data)) {
            $opts[CURLOPT_POSTFIELDS] = json_encode($data);
        }

        curl_setopt_array($ch, $opts);
        $raw    = curl_exec($ch);
        $status = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $error  = curl_error($ch);
        curl_close($ch);

        if ($error) {
            throw new RuntimeException("Evolution API cURL error: $error");
        }

        $result = json_decode($raw ?: '{}', true) ?? [];

        if ($status >= 400) {
            $msg = $result['message'] ?? $result['error'] ?? $raw;
            throw new RuntimeException("Evolution API error ($status): $msg");
        }

        return $result;
    }
}
