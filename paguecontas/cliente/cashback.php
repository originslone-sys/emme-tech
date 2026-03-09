<?php
require_once __DIR__ . '/../includes/auth.php';
requireLogin();

$user = getCurrentUser($pdo);
if (!$user || $user['is_admin']) redirect('../login.php');

$stmt = $pdo->prepare("SELECT COUNT(*) as count FROM notifications WHERE user_id = ? AND is_read = 0");
$stmt->execute([$user['id']]);
$unreadNotifications = $stmt->fetch()['count'];

// Get cashback transactions
$stmt = $pdo->prepare("SELECT * FROM transactions WHERE user_id = ? AND type IN ('cashback', 'cashback_used') ORDER BY created_at DESC LIMIT 50");
$stmt->execute([$user['id']]);
$cashbackTransactions = $stmt->fetchAll();

// Total cashback earned
$stmt = $pdo->prepare("SELECT COALESCE(SUM(amount), 0) as total FROM transactions WHERE user_id = ? AND type = 'cashback' AND status = 'completed'");
$stmt->execute([$user['id']]);
$totalEarned = $stmt->fetch()['total'];

// Total cashback used
$stmt = $pdo->prepare("SELECT COALESCE(SUM(amount), 0) as total FROM transactions WHERE user_id = ? AND type = 'cashback_used' AND status = 'completed'");
$stmt->execute([$user['id']]);
$totalUsed = $stmt->fetch()['total'];
?>
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Meu Cashback - PagueContas</title>
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
                    <h1>Meu Cashback</h1>
                    <p class="header-subtitle">Acompanhe seus ganhos de cashback</p>
                </div>
            </div>

            <div class="content-body">
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 20px; margin-bottom: 32px;">
                    <div class="balance-card" style="background: var(--gradient-secondary); border: none;">
                        <div class="card-label">Saldo Cashback</div>
                        <div class="card-value"><?= formatMoney($user['cashback_balance']) ?></div>
                        <div class="card-icon">&#128176;</div>
                    </div>
                    <div class="balance-card">
                        <div class="card-label">Total Ganho</div>
                        <div class="card-value" style="color: var(--success); font-size: 26px;"><?= formatMoney($totalEarned) ?></div>
                    </div>
                    <div class="balance-card">
                        <div class="card-label">Total Utilizado</div>
                        <div class="card-value" style="color: var(--info); font-size: 26px;"><?= formatMoney($totalUsed) ?></div>
                    </div>
                </div>

                <div class="card">
                    <div class="card-header">
                        <h3>Histórico de Cashback</h3>
                    </div>
                    <div class="card-body">
                        <?php if (empty($cashbackTransactions)): ?>
                            <div class="empty-state">
                                <div class="empty-icon">&#128176;</div>
                                <h3>Nenhum cashback ainda</h3>
                                <p>Pague contas pela plataforma e ganhe 5% de cashback!</p>
                            </div>
                        <?php else: ?>
                            <?php foreach ($cashbackTransactions as $tx): ?>
                                <div class="transaction-item">
                                    <div class="tx-icon cashback">&#128176;</div>
                                    <div class="tx-details">
                                        <div class="tx-title"><?= sanitize($tx['description']) ?></div>
                                        <div class="tx-subtitle"><?= date('d/m/Y H:i', strtotime($tx['created_at'])) ?></div>
                                    </div>
                                    <div class="tx-amount">
                                        <?php if ($tx['type'] === 'cashback'): ?>
                                            <div class="tx-value positive">+ <?= formatMoney($tx['amount']) ?></div>
                                        <?php else: ?>
                                            <div class="tx-value negative">- <?= formatMoney($tx['amount']) ?></div>
                                        <?php endif; ?>
                                    </div>
                                </div>
                            <?php endforeach; ?>
                        <?php endif; ?>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <script src="../assets/js/main.js"></script>
</body>
</html>
