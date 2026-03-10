<?php
require_once __DIR__ . '/../includes/auth.php';
requireLogin();

$user = getCurrentUser($pdo);
if (!$user || $user['is_admin']) {
    redirect('../login.php');
}

$error = '';
$success = '';

$stmt = $pdo->prepare("SELECT COUNT(*) as count FROM notifications WHERE user_id = ? AND is_read = 0");
$stmt->execute([$user['id']]);
$unreadNotifications = $stmt->fetch()['count'];

// Get pending recharges
$stmt = $pdo->prepare("SELECT * FROM recharges WHERE user_id = ? ORDER BY created_at DESC LIMIT 10");
$stmt->execute([$user['id']]);
$recharges = $stmt->fetchAll();

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $amount = floatval(str_replace(['.', ','], ['', '.'], preg_replace('/[^\d,.]/', '', $_POST['amount'] ?? '0')));
    $paymentMethod = $_POST['payment_method'] ?? 'pix';

    if ($amount < 10) {
        $error = 'O valor mínimo para recarga é R$ 10,00.';
    } elseif ($amount > 10000) {
        $error = 'O valor máximo para recarga é R$ 10.000,00.';
    } else {
        $refCode = 'REC-' . strtoupper(substr(md5(uniqid()), 0, 10));

        $stmt = $pdo->prepare("INSERT INTO recharges (user_id, amount, payment_method, reference_code) VALUES (?, ?, ?, ?)");
        $stmt->execute([$user['id'], $amount, $paymentMethod, $refCode]);

        // Create notification
        $stmt = $pdo->prepare("INSERT INTO notifications (user_id, title, message, type) VALUES (?, ?, ?, 'info')");
        $methods = ['pix' => 'PIX', 'credit_card' => 'Cartão de Crédito', 'bank_transfer' => 'Transferência'];
        $stmt->execute([
            $user['id'],
            'Recarga Solicitada',
            'Sua recarga de ' . formatMoney($amount) . ' via ' . ($methods[$paymentMethod] ?? $paymentMethod) . ' foi solicitada. Código: ' . $refCode
        ]);

        $success = 'Recarga de ' . formatMoney($amount) . ' solicitada com sucesso! Código de referência: ' . $refCode . '. Aguarde a aprovação.';

        // Refresh recharges list
        $stmt = $pdo->prepare("SELECT * FROM recharges WHERE user_id = ? ORDER BY created_at DESC LIMIT 10");
        $stmt->execute([$user['id']]);
        $recharges = $stmt->fetchAll();
    }
}

// Get PIX key from settings
$stmt = $pdo->prepare("SELECT setting_value FROM settings WHERE setting_key = 'pix_key'");
$stmt->execute();
$pixKey = $stmt->fetch()['setting_value'] ?? 'paguecontas@pix.com';
?>
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Recarregar Saldo - PagueContas</title>
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
                    <h1>Recarregar Saldo</h1>
                    <p class="header-subtitle">Adicione saldo à sua conta</p>
                </div>
            </div>

            <div class="content-body">
                <?php if ($success): ?>
                    <div class="alert alert-success">
                        <span>&#10003;</span> <?= $success ?>
                    </div>
                <?php endif; ?>

                <?php if ($error): ?>
                    <div class="alert alert-danger">
                        <span>&#10007;</span> <?= sanitize($error) ?>
                    </div>
                <?php endif; ?>

                <div class="dashboard-grid">
                    <div class="card">
                        <div class="card-header">
                            <h3>&#128178; Nova Recarga</h3>
                        </div>
                        <div class="card-body" style="padding: 24px;">
                            <form method="POST" action="">
                                <div class="form-group">
                                    <label>Método de Pagamento</label>
                                    <div class="tabs">
                                        <button type="button" class="tab active" onclick="selectMethod(this, 'pix')">PIX</button>
                                        <button type="button" class="tab" onclick="selectMethod(this, 'credit_card')">Cartão</button>
                                        <button type="button" class="tab" onclick="selectMethod(this, 'bank_transfer')">Transferência</button>
                                    </div>
                                    <input type="hidden" name="payment_method" id="payment_method" value="pix">
                                </div>

                                <div id="pixInfo" style="background: rgba(108, 43, 217, 0.08); border: 1px solid rgba(108, 43, 217, 0.2); border-radius: var(--radius-sm); padding: 20px; margin-bottom: 20px;">
                                    <p style="font-size: 14px; font-weight: 600; margin-bottom: 8px;">&#128273; Chave PIX para transferência:</p>
                                    <div style="background: var(--dark-surface); padding: 12px 16px; border-radius: var(--radius-sm); font-family: monospace; font-size: 15px; display: flex; justify-content: space-between; align-items: center;">
                                        <span id="pixKeyText"><?= sanitize($pixKey) ?></span>
                                        <button type="button" onclick="navigator.clipboard.writeText('<?= sanitize($pixKey) ?>'); this.textContent='Copiado!'; setTimeout(()=>this.textContent='Copiar',2000);" class="btn btn-sm btn-secondary" style="padding: 6px 14px; font-size: 12px;">Copiar</button>
                                    </div>
                                    <p style="font-size: 12px; color: var(--text-muted); margin-top: 8px;">Faça o PIX e solicite a recarga abaixo. A aprovação será feita pelo admin.</p>
                                </div>

                                <div class="form-group">
                                    <label for="amount">Valor da Recarga</label>
                                    <input type="text" id="amount" name="amount" class="form-control money-input" placeholder="R$ 0,00" required>
                                    <div class="form-text">Mínimo: R$ 10,00 | Máximo: R$ 10.000,00</div>
                                </div>

                                <button type="submit" class="btn btn-success btn-block btn-lg">
                                    Solicitar Recarga &#10132;
                                </button>
                            </form>
                        </div>
                    </div>

                    <div>
                        <div class="card" style="margin-bottom: 24px;">
                            <div class="card-body" style="padding: 24px; text-align: center;">
                                <div style="font-size: 13px; color: var(--text-muted); margin-bottom: 6px;">Saldo Atual</div>
                                <div style="font-size: 28px; font-weight: 800;"><?= formatMoney($user['balance']) ?></div>
                            </div>
                        </div>

                        <div class="card">
                            <div class="card-header">
                                <h3>Histórico de Recargas</h3>
                            </div>
                            <div class="card-body">
                                <?php if (empty($recharges)): ?>
                                    <div class="empty-state" style="padding: 32px;">
                                        <p style="font-size: 13px;">Nenhuma recarga realizada</p>
                                    </div>
                                <?php else: ?>
                                    <?php foreach ($recharges as $rec): ?>
                                        <div class="transaction-item">
                                            <div class="tx-icon deposit">&#128178;</div>
                                            <div class="tx-details">
                                                <div class="tx-title"><?= formatMoney($rec['amount']) ?></div>
                                                <div class="tx-subtitle"><?= date('d/m/Y H:i', strtotime($rec['created_at'])) ?></div>
                                            </div>
                                            <div class="tx-amount">
                                                <span class="status-badge <?= $rec['status'] ?>">
                                                    <?php
                                                    $statuses = [
                                                        'pending' => 'Pendente',
                                                        'approved' => 'Aprovada',
                                                        'rejected' => 'Rejeitada',
                                                        'cancelled' => 'Cancelada'
                                                    ];
                                                    echo $statuses[$rec['status']] ?? $rec['status'];
                                                    ?>
                                                </span>
                                            </div>
                                        </div>
                                    <?php endforeach; ?>
                                <?php endif; ?>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="../assets/js/main.js"></script>
    <script>
        function selectMethod(btn, method) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById('payment_method').value = method;

            const pixInfo = document.getElementById('pixInfo');
            if (method === 'pix') {
                pixInfo.style.display = 'block';
            } else {
                pixInfo.style.display = 'none';
            }
        }
    </script>
</body>
</html>
