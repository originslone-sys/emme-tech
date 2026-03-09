<?php
require_once __DIR__ . '/../includes/auth.php';
requireLogin();

$user = getCurrentUser($pdo);
if (!$user || $user['is_admin']) {
    redirect('../login.php');
}

$error = '';
$success = '';

// Get unread notifications count
$stmt = $pdo->prepare("SELECT COUNT(*) as count FROM notifications WHERE user_id = ? AND is_read = 0");
$stmt->execute([$user['id']]);
$unreadNotifications = $stmt->fetch()['count'];

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $barcode = preg_replace('/\D/', '', $_POST['barcode'] ?? '');
    $amount = floatval(str_replace(['.', ','], ['', '.'], preg_replace('/[^\d,.]/', '', $_POST['amount'] ?? '0')));
    $billType = $_POST['bill_type'] ?? 'boleto';
    $description = sanitize($_POST['description'] ?? 'Pagamento de conta');
    $useCashback = isset($_POST['use_cashback']) && $_POST['use_cashback'] === '1';

    if (empty($barcode)) {
        $error = 'Informe o código de barras.';
    } elseif ($amount <= 0) {
        $error = 'Informe um valor válido.';
    } else {
        $totalBalance = $user['balance'];
        $cashbackUsed = 0;

        if ($useCashback && $user['cashback_balance'] > 0) {
            $cashbackUsed = min($user['cashback_balance'], $amount);
            $amountFromBalance = $amount - $cashbackUsed;
        } else {
            $amountFromBalance = $amount;
        }

        if ($amountFromBalance > $user['balance']) {
            $error = 'Saldo insuficiente. Seu saldo é ' . formatMoney($user['balance']) . ($useCashback ? ' + cashback ' . formatMoney($user['cashback_balance']) : '') . '.';
        } else {
            try {
                $pdo->beginTransaction();

                // Deduct from balance
                $newBalance = $user['balance'] - $amountFromBalance;
                $newCashbackBalance = $user['cashback_balance'] - $cashbackUsed;

                $stmt = $pdo->prepare("UPDATE users SET balance = ?, cashback_balance = ? WHERE id = ?");
                $stmt->execute([$newBalance, $newCashbackBalance, $user['id']]);

                // Record payment transaction
                $billTypes = [
                    'boleto' => 'Pagamento de Boleto',
                    'energia' => 'Conta de Energia',
                    'agua' => 'Conta de Água',
                    'gas' => 'Conta de Gás',
                    'telefone' => 'Conta de Telefone',
                    'internet' => 'Conta de Internet',
                    'outro' => 'Pagamento de Conta'
                ];
                $desc = $billTypes[$billType] ?? $description;

                $cashbackAmount = round($amount * (CASHBACK_PERCENT / 100), 2);
                $refId = 'PAY-' . strtoupper(substr(md5(uniqid()), 0, 10));

                $stmt = $pdo->prepare("INSERT INTO transactions (user_id, type, amount, balance_after, description, barcode, bill_type, cashback_amount, status, reference_id) VALUES (?, 'payment', ?, ?, ?, ?, ?, ?, 'completed', ?)");
                $stmt->execute([$user['id'], $amount, $newBalance, $desc, $barcode, $billType, $cashbackAmount, $refId]);

                // If cashback was used, record it
                if ($cashbackUsed > 0) {
                    $stmt = $pdo->prepare("INSERT INTO transactions (user_id, type, amount, balance_after, description, status, reference_id) VALUES (?, 'cashback_used', ?, ?, ?, 'completed', ?)");
                    $stmt->execute([$user['id'], $cashbackUsed, $newCashbackBalance, 'Cashback utilizado no pagamento', $refId]);
                }

                // Credit cashback
                $finalCashbackBalance = $newCashbackBalance + $cashbackAmount;
                $stmt = $pdo->prepare("UPDATE users SET cashback_balance = ? WHERE id = ?");
                $stmt->execute([$finalCashbackBalance, $user['id']]);

                $stmt = $pdo->prepare("INSERT INTO transactions (user_id, type, amount, balance_after, description, status, reference_id) VALUES (?, 'cashback', ?, ?, ?, 'completed', ?)");
                $stmt->execute([$user['id'], $cashbackAmount, $finalCashbackBalance, 'Cashback de ' . CASHBACK_PERCENT . '% - ' . $desc, $refId]);

                // Create notification
                $stmt = $pdo->prepare("INSERT INTO notifications (user_id, title, message, type) VALUES (?, ?, ?, 'success')");
                $stmt->execute([
                    $user['id'],
                    'Pagamento Realizado!',
                    $desc . ' de ' . formatMoney($amount) . ' pago com sucesso! Cashback de ' . formatMoney($cashbackAmount) . ' creditado.'
                ]);

                $pdo->commit();

                $success = 'Pagamento de ' . formatMoney($amount) . ' realizado com sucesso! Cashback de ' . formatMoney($cashbackAmount) . ' creditado na sua conta.';
                $user = getCurrentUser($pdo);
            } catch (Exception $e) {
                $pdo->rollBack();
                $error = 'Erro ao processar pagamento. Tente novamente.';
            }
        }
    }
}
?>
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pagar Conta - PagueContas</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="../assets/css/style.css">
    <link rel="stylesheet" href="assets/css/dashboard.css">
</head>
<body>
    <div class="dashboard-layout">
        <?php include 'includes/sidebar.php'; ?>

        <div class="main-content">
            <div class="content-header">
                <div>
                    <button class="sidebar-toggle" onclick="document.getElementById('sidebar').classList.toggle('active')">&#9776;</button>
                    <h1>Pagar Conta</h1>
                    <p class="header-subtitle">Pague boletos e contas com código de barras</p>
                </div>
            </div>

            <div class="content-body">
                <?php if ($success): ?>
                    <div class="alert alert-success" style="max-width: 600px;">
                        <span>&#10003;</span> <?= $success ?>
                    </div>
                <?php endif; ?>

                <?php if ($error): ?>
                    <div class="alert alert-danger" style="max-width: 600px;">
                        <span>&#10007;</span> <?= sanitize($error) ?>
                    </div>
                <?php endif; ?>

                <div class="card payment-form-card">
                    <div class="card-header">
                        <h3>&#128179; Novo Pagamento</h3>
                    </div>
                    <div class="card-body" style="padding: 24px;">
                        <form method="POST" action="" id="paymentForm">
                            <div class="form-group">
                                <label for="bill_type">Tipo de Conta</label>
                                <select name="bill_type" id="bill_type" class="form-control">
                                    <option value="boleto">&#128196; Boleto Bancário</option>
                                    <option value="energia">&#128161; Conta de Energia</option>
                                    <option value="agua">&#128167; Conta de Água</option>
                                    <option value="gas">&#128293; Conta de Gás</option>
                                    <option value="telefone">&#128222; Conta de Telefone</option>
                                    <option value="internet">&#127760; Conta de Internet</option>
                                    <option value="outro">&#128203; Outra Conta</option>
                                </select>
                            </div>

                            <div class="form-group">
                                <label for="barcode">Código de Barras</label>
                                <input type="text" id="barcode" name="barcode" class="form-control barcode-input" placeholder="Digite o código de barras da conta" required>
                                <div class="form-text">Digite os números do código de barras (somente números)</div>
                            </div>

                            <div class="form-group">
                                <label for="amount">Valor da Conta</label>
                                <input type="text" id="amount" name="amount" class="form-control money-input" placeholder="R$ 0,00" required>
                            </div>

                            <div class="form-group">
                                <label for="description">Descrição (opcional)</label>
                                <input type="text" id="description" name="description" class="form-control" placeholder="Ex: Conta de luz janeiro">
                            </div>

                            <?php if ($user['cashback_balance'] > 0): ?>
                                <div class="form-group" style="background: rgba(6, 214, 160, 0.08); border: 1px solid rgba(6, 214, 160, 0.2); border-radius: var(--radius-sm); padding: 16px;">
                                    <label style="display: flex; align-items: center; gap: 10px; cursor: pointer; margin-bottom: 0;">
                                        <input type="checkbox" name="use_cashback" value="1" style="width: 18px; height: 18px; accent-color: var(--success);">
                                        <span>Usar saldo de cashback (<?= formatMoney($user['cashback_balance']) ?> disponível)</span>
                                    </label>
                                </div>
                            <?php endif; ?>

                            <div class="payment-summary" id="paymentSummary" style="display: none;">
                                <div class="summary-row">
                                    <span class="label">Valor da conta</span>
                                    <span class="value" id="summaryAmount">R$ 0,00</span>
                                </div>
                                <div class="summary-row">
                                    <span class="label">Cashback (5%)</span>
                                    <span class="value cashback-highlight" id="summaryCashback">+ R$ 0,00</span>
                                </div>
                                <div class="summary-row">
                                    <span class="label">Saldo após pagamento</span>
                                    <span class="value" id="summaryBalance"><?= formatMoney($user['balance']) ?></span>
                                </div>
                            </div>

                            <button type="submit" class="btn btn-primary btn-block btn-lg" style="margin-top: 24px;">
                                Confirmar Pagamento &#10132;
                            </button>

                            <p style="text-align: center; margin-top: 12px; font-size: 13px; color: var(--text-muted);">
                                Saldo disponível: <strong><?= formatMoney($user['balance']) ?></strong>
                                <?php if ($user['cashback_balance'] > 0): ?>
                                    | Cashback: <strong style="color: var(--success);"><?= formatMoney($user['cashback_balance']) ?></strong>
                                <?php endif; ?>
                            </p>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="../assets/js/main.js"></script>
    <script>
        const amountInput = document.getElementById('amount');
        const summary = document.getElementById('paymentSummary');
        const userBalance = <?= $user['balance'] ?>;

        amountInput.addEventListener('input', function() {
            let raw = this.value.replace(/\D/g, '');
            let value = parseInt(raw) / 100;

            if (value > 0) {
                summary.style.display = 'block';
                let cashback = value * 0.05;
                let balanceAfter = userBalance - value;

                document.getElementById('summaryAmount').textContent = 'R$ ' + value.toFixed(2).replace('.', ',').replace(/\B(?=(\d{3})+(?!\d))/g, '.');
                document.getElementById('summaryCashback').textContent = '+ R$ ' + cashback.toFixed(2).replace('.', ',');
                document.getElementById('summaryBalance').textContent = 'R$ ' + balanceAfter.toFixed(2).replace('.', ',').replace(/\B(?=(\d{3})+(?!\d))/g, '.');

                if (balanceAfter < 0) {
                    document.getElementById('summaryBalance').style.color = 'var(--danger)';
                } else {
                    document.getElementById('summaryBalance').style.color = 'var(--text-primary)';
                }
            } else {
                summary.style.display = 'none';
            }
        });
    </script>
</body>
</html>
