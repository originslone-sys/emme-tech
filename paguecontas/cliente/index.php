<?php
require_once __DIR__ . '/../includes/auth.php';
requireLogin();

$user = getCurrentUser($pdo);
if (!$user || $user['is_admin']) {
    redirect('../login.php');
}

// Get recent transactions
$stmt = $pdo->prepare("SELECT * FROM transactions WHERE user_id = ? ORDER BY created_at DESC LIMIT 10");
$stmt->execute([$user['id']]);
$transactions = $stmt->fetchAll();

// Get unread notifications count
$stmt = $pdo->prepare("SELECT COUNT(*) as count FROM notifications WHERE user_id = ? AND is_read = 0");
$stmt->execute([$user['id']]);
$unreadNotifications = $stmt->fetch()['count'];

// Get monthly stats
$stmt = $pdo->prepare("SELECT
    COALESCE(SUM(CASE WHEN type = 'deposit' AND status = 'completed' THEN amount END), 0) as total_deposits,
    COALESCE(SUM(CASE WHEN type = 'payment' AND status = 'completed' THEN amount END), 0) as total_payments,
    COALESCE(SUM(CASE WHEN type = 'cashback' AND status = 'completed' THEN amount END), 0) as total_cashback
    FROM transactions WHERE user_id = ? AND MONTH(created_at) = MONTH(NOW()) AND YEAR(created_at) = YEAR(NOW())");
$stmt->execute([$user['id']]);
$monthlyStats = $stmt->fetch();
?>
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard - PagueContas</title>
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
                    <h1>Dashboard</h1>
                    <p class="header-subtitle">Bem-vindo de volta, <?= sanitize(explode(' ', $user['name'])[0]) ?>!</p>
                </div>
                <div class="header-actions">
                    <a href="notificacoes.php" class="notification-btn">
                        &#128276;
                        <?php if ($unreadNotifications > 0): ?>
                            <span class="badge"><?= $unreadNotifications ?></span>
                        <?php endif; ?>
                    </a>
                </div>
            </div>

            <div class="content-body">
                <!-- Balance Cards -->
                <div class="balance-cards">
                    <div class="balance-card primary">
                        <div class="card-label">Saldo Disponível</div>
                        <div class="card-value"><?= formatMoney($user['balance']) ?></div>
                        <div class="card-change neutral">&#128179; Saldo principal</div>
                        <div class="card-icon">&#128179;</div>
                    </div>
                    <div class="balance-card">
                        <div class="card-label">Saldo Cashback</div>
                        <div class="card-value" style="color: var(--success);"><?= formatMoney($user['cashback_balance']) ?></div>
                        <div class="card-change positive">&#128176; Disponível para uso</div>
                        <div class="card-icon">&#128176;</div>
                    </div>
                    <div class="balance-card">
                        <div class="card-label">Cashback do Mês</div>
                        <div class="card-value" style="color: var(--warning);"><?= formatMoney($monthlyStats['total_cashback']) ?></div>
                        <div class="card-change positive">&#127775; 5% em cada pagamento</div>
                        <div class="card-icon">&#127775;</div>
                    </div>
                </div>

                <!-- Quick Actions -->
                <div class="quick-actions">
                    <a href="pagar.php" class="quick-action">
                        <div class="action-icon purple">&#128179;</div>
                        <div class="action-title">Pagar Conta</div>
                        <div class="action-desc">Boletos e contas</div>
                    </a>
                    <a href="recarga.php" class="quick-action">
                        <div class="action-icon green">&#128178;</div>
                        <div class="action-title">Recarregar</div>
                        <div class="action-desc">Adicionar saldo</div>
                    </a>
                    <a href="extrato.php" class="quick-action">
                        <div class="action-icon blue">&#128202;</div>
                        <div class="action-title">Extrato</div>
                        <div class="action-desc">Ver movimentações</div>
                    </a>
                    <a href="cashback.php" class="quick-action">
                        <div class="action-icon pink">&#128176;</div>
                        <div class="action-title">Cashback</div>
                        <div class="action-desc">Seus ganhos</div>
                    </a>
                </div>

                <!-- Dashboard Grid -->
                <div class="dashboard-grid">
                    <!-- Recent Transactions -->
                    <div class="card">
                        <div class="card-header">
                            <h3>Últimas Movimentações</h3>
                            <a href="extrato.php" class="view-all">Ver tudo &#8594;</a>
                        </div>
                        <div class="card-body">
                            <?php if (empty($transactions)): ?>
                                <div class="empty-state">
                                    <div class="empty-icon">&#128203;</div>
                                    <h3>Nenhuma movimentação</h3>
                                    <p>Recarregue seu saldo e comece a pagar contas!</p>
                                </div>
                            <?php else: ?>
                                <?php foreach ($transactions as $tx): ?>
                                    <div class="transaction-item">
                                        <div class="tx-icon <?= $tx['type'] ?>">
                                            <?php
                                            $icons = [
                                                'deposit' => '&#128178;',
                                                'payment' => '&#128179;',
                                                'cashback' => '&#128176;',
                                                'cashback_used' => '&#128176;',
                                                'refund' => '&#128260;'
                                            ];
                                            echo $icons[$tx['type']] ?? '&#128179;';
                                            ?>
                                        </div>
                                        <div class="tx-details">
                                            <div class="tx-title"><?= sanitize($tx['description']) ?></div>
                                            <div class="tx-subtitle"><?= date('d/m/Y H:i', strtotime($tx['created_at'])) ?></div>
                                        </div>
                                        <div class="tx-amount">
                                            <?php
                                            $isPositive = in_array($tx['type'], ['deposit', 'cashback', 'refund']);
                                            $class = $isPositive ? 'positive' : 'negative';
                                            if ($tx['type'] === 'cashback') $class = 'cashback-color';
                                            $prefix = $isPositive ? '+' : '-';
                                            ?>
                                            <div class="tx-value <?= $class ?>"><?= $prefix . ' ' . formatMoney($tx['amount']) ?></div>
                                            <div class="tx-status <?= $tx['status'] ?>">
                                                <?php
                                                $statuses = [
                                                    'completed' => 'Concluído',
                                                    'pending' => 'Pendente',
                                                    'failed' => 'Falhou',
                                                    'cancelled' => 'Cancelado'
                                                ];
                                                echo $statuses[$tx['status']] ?? $tx['status'];
                                                ?>
                                            </div>
                                        </div>
                                    </div>
                                <?php endforeach; ?>
                            <?php endif; ?>
                        </div>
                    </div>

                    <!-- Monthly Summary -->
                    <div>
                        <div class="card" style="margin-bottom: 24px;">
                            <div class="card-header">
                                <h3>Resumo do Mês</h3>
                            </div>
                            <div class="card-body" style="padding: 24px;">
                                <div style="margin-bottom: 20px;">
                                    <div style="font-size: 13px; color: var(--text-muted); margin-bottom: 6px;">Entradas</div>
                                    <div style="font-size: 22px; font-weight: 700; color: var(--success);"><?= formatMoney($monthlyStats['total_deposits']) ?></div>
                                </div>
                                <div style="margin-bottom: 20px;">
                                    <div style="font-size: 13px; color: var(--text-muted); margin-bottom: 6px;">Saídas</div>
                                    <div style="font-size: 22px; font-weight: 700; color: var(--danger);"><?= formatMoney($monthlyStats['total_payments']) ?></div>
                                </div>
                                <div style="padding-top: 16px; border-top: 1px solid var(--dark-border);">
                                    <div style="font-size: 13px; color: var(--text-muted); margin-bottom: 6px;">Cashback Ganho</div>
                                    <div style="font-size: 22px; font-weight: 700; color: var(--warning);"><?= formatMoney($monthlyStats['total_cashback']) ?></div>
                                </div>
                            </div>
                        </div>

                        <div class="card">
                            <div class="card-body" style="padding: 24px; text-align: center;">
                                <div style="font-size: 48px; margin-bottom: 12px;">&#128176;</div>
                                <h3 style="font-size: 16px; margin-bottom: 8px;">Cashback Ativo</h3>
                                <p style="font-size: 13px; color: var(--text-muted); margin-bottom: 16px;">Ganhe 5% de cashback em cada conta paga!</p>
                                <a href="pagar.php" class="btn btn-primary btn-sm btn-block">Pagar Conta Agora</a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="../assets/js/main.js"></script>
</body>
</html>
