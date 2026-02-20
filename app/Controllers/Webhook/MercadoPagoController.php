<?php

declare(strict_types=1);

namespace App\Controllers\Webhook;

use App\Core\DB;
use App\Lib\Logger;
use App\Lib\MercadoPago;
use App\Lib\GlobalSettings;

/**
 * MercadoPagoController — processa webhooks / IPN do Mercado Pago.
 */
class MercadoPagoController
{
    public function receive(): void
    {
        http_response_code(200);
        echo 'ok';

        $raw = file_get_contents('php://input');
        if (!$raw) exit;

        $payload = json_decode($raw, true);
        if (!is_array($payload)) exit;

        $type = $payload['type'] ?? $payload['action'] ?? '';

        Logger::info('MercadoPago webhook received', ['type' => $type]);

        // Valida assinatura (se configurada)
        $secret = GlobalSettings::get('mp_webhook_secret');
        if ($secret) {
            $xSignature = $_SERVER['HTTP_X_SIGNATURE'] ?? '';
            $xRequestId = $_SERVER['HTTP_X_REQUEST_ID'] ?? '';
            if (!MercadoPago::verifySignature($raw, $xSignature, $xRequestId, $secret)) {
                Logger::warning('MercadoPago webhook: invalid signature');
                exit;
            }
        }

        // Notificação de pagamento
        if (in_array($type, ['payment', 'payment.updated'], true)) {
            $paymentId = (string)($payload['data']['id'] ?? $payload['resource'] ?? '');
            if ($paymentId) {
                $this->handlePayment($paymentId);
            }
        }

        exit;
    }

    private function handlePayment(string $mpPaymentId): void
    {
        try {
            $mp      = MercadoPago::fromSettings();
            $payment = $mp->getPayment($mpPaymentId);

            $status   = $payment['status'] ?? '';
            $metadata = $payment['metadata'] ?? [];
            $tenantId = (int)($metadata['tenant_id'] ?? 0);
            $credits  = (int)($metadata['credits'] ?? 0);
            $prefId   = (string)($payment['preference_id'] ?? '');

            if (!$tenantId || !$credits) {
                Logger::warning('MercadoPago webhook: missing metadata', compact('mpPaymentId'));
                return;
            }

            // Busca o registro de pagamento pelo pref_id ou mp_payment_id
            $record = DB::fetchOne(
                "SELECT * FROM mp_payments WHERE (mp_pref_id = ? OR mp_payment_id = ?) AND tenant_id = ?",
                [$prefId, $mpPaymentId, $tenantId]
            );

            if (!$record) {
                Logger::warning('MercadoPago webhook: payment record not found', ['mp_payment_id' => $mpPaymentId]);
                return;
            }

            // Evita processar duplicado
            if ($record['status'] === 'approved') {
                Logger::info('MercadoPago webhook: already approved', ['record_id' => $record['id']]);
                return;
            }

            if ($status === 'approved') {
                DB::beginTransaction();
                try {
                    // Atualiza registro de pagamento
                    DB::update('mp_payments', [
                        'mp_payment_id' => $mpPaymentId,
                        'status'        => 'approved',
                        'paid_at'       => date('Y-m-d H:i:s'),
                    ], ['id' => $record['id']]);

                    // Adiciona créditos ao tenant
                    DB::query('UPDATE tenants SET credits = credits + ? WHERE id = ?', [$credits, $tenantId]);

                    // Registra transação
                    DB::insert('credit_transactions', [
                        'tenant_id'    => $tenantId,
                        'amount'       => $credits,
                        'type'         => 'purchase',
                        'description'  => 'Compra de créditos — Mercado Pago',
                        'reference_id' => $mpPaymentId,
                    ]);

                    DB::commit();

                    Logger::info('MercadoPago webhook: credits added', [
                        'tenant_id' => $tenantId,
                        'credits'   => $credits,
                        'payment'   => $mpPaymentId,
                    ]);
                } catch (\Throwable $e) {
                    DB::rollBack();
                    Logger::error('MercadoPago webhook: failed to add credits', ['error' => $e->getMessage()]);
                }
            } else {
                // Atualiza status (rejected, cancelled, etc.)
                $mappedStatus = match($status) {
                    'rejected'  => 'rejected',
                    'cancelled' => 'cancelled',
                    default     => 'pending',
                };
                DB::update('mp_payments', [
                    'mp_payment_id' => $mpPaymentId,
                    'status'        => $mappedStatus,
                ], ['id' => $record['id']]);
            }
        } catch (\Throwable $e) {
            Logger::error('MercadoPago webhook: exception', ['error' => $e->getMessage()]);
        }
    }
}
