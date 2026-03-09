<?php
require_once __DIR__ . '/../includes/auth.php';
requireAdmin();

// Dashboard Stats
$stmt = $pdo->query("SELECT COUNT(*) as total FROM users WHERE is_admin = 0");
$totalUsers = $stmt->fetch()['total'];

$stmt = $pdo->query("SELECT COUNT(*) as total FROM users WHERE is_admin = 0 AND status = 'active'");
$activeUsers = $stmt->fetch()['total'];

$stmt = $pdo->query("SELECT COALESCE(SUM(amount), 0) as total FROM transactions WHERE type = 'payment' AND status = 'completed'");
$totalPayments = $stmt->fetch()['total'];

$stmt = $pdo->query("SELECT COALESCE(SUM(amount), 0) as total FROM transactions WHERE type = 'cashback' AND status = 'completed'");
$totalCashback = $stmt->fetch()['total'];

$stmt = $pdo->query("SELECT COALESCE(SUM(balance), 0) + COALESCE(SUM(cashback_balance), 0) as total FROM users WHERE is_admin = 0");
$totalBalance = $stmt->fetch()['total'];

$stmt = $pdo->query("SELECT COUNT(*) as total FROM recharges WHERE status = 'pending'");
$pendingRecharges = $stmt->fetch()['total'];

$stmt = $pdo->query("SELECT COUNT(*) as total FROM transactions WHERE type = 'payment' AND status = 'completed'");
$totalTransactions = $stmt->fetch()['total'];

// Recent transactions
$stmt = $pdo->query("SELECT t.*, u.name as user_name, u.email as user_email FROM transactions t JOIN users u ON t.user_id = u.id ORDER BY t.created_at DESC LIMIT 10");
$recentTx = $stmt->fetchAll();

// Pending recharges
$stmt = $pdo->query("SELECT r.*, u.name as user_name, u.email as user_email FROM recharges r JOIN users u ON r.user_id = u.id WHERE r.status = 'pending' ORDER BY r.created_at DESC LIMIT 5");
$pendingRec = $stmt->fetchAll();

// Monthly revenue
$stmt = $pdo->query("SELECT
    COALESCE(SUM(CASE WHEN type = 'deposit' AND status = 'completed' THEN amount END), 0) as deposits,
    COALESCE(SUM(CASE WHEN type = 'payment' AND status = 'completed' THEN amount END), 0) as payments,
    COALESCE(SUM(CASE WHEN type = 'cashback' AND status = 'completed' THEN amount END), 0) as cashback_given
    FROM transactions WHERE MONTH(created_at) = MONTH(NOW()) AND YEAR(created_at) = YEAR(NOW())");
$monthly = $stmt->fetch();
?>
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Dashboard - PagueContas</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="../assets/css/style.css">
    <link rel="stylesheet" href="../cliente/assets/css/dashboard.css">
    <link rel="stylesheet" href="assets/css/admin.css">
</head>
<body>
    <div class="dashboard-layout">
        <?php include 'includes/sidebar.php'; ?>

        <div class="main-content">
            <div class="content-header">
                <div>
                    <button class="sidebar-toggle" onclick="document.getElementById('sidebar').classList.toggle('active')">&#9776;</button>
                    <h1>Dashboard Admin</h1>
                    <p class="header-subtitle">Visão geral da plataforma</p>
                </div>
                <div class="header-actions">
                    <?php if ($pendingRecharges > 0): ?>
                        <a href="recargas.php" class="btn btn-primary btn-sm">
                            <?= $pendingRecharges ?> recarga(s) pendente(s)
                        </a>
                    <?php endif; ?>
                </div>
            </div>

            <div class="content-body">
                <!-- Stats -->
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-icon" style="background: rgba(108, 43, 217, 0.15);">&#128101;</div>
                        <div class="stat-value"><?= number_format($totalUsers) ?></div>
                        <div class="stat-label">Total de Usuários (<?= $activeUsers ?> ativos)</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon" style="background: rgba(6, 214, 160, 0.15);">&#128179;</div>
                        <div class="stat-value"><?= formatMoney($totalPayments) ?></div>
                        <div class="stat-label">Total em Pagamentos</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon" style="background: rgba(255, 182, 39, 0.15);">&#128176;</div>
                        <div class="stat-value"><?= formatMoney($totalCashback) ?></div>
                        <div class="stat-label">Cashback Distribuído</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon" style="background: rgba(247, 37, 133, 0.15);">&#128178;</div>
                        <div class="stat-value"><?= formatMoney($totalBalance) ?></div>
                        <div class="stat-label">Saldo Total dos Usuários</div>
                    </div>
                </div>

                <!-- Monthly Summary -->
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 32px;">
                    <div class="balance-card">
                        <div class="card-label">Depósitos do Mês</div>
                        <div class="card-value" style="font-size: 24px; color: var(--success);"><?= formatMoney($monthly['deposits']) ?></div>
                    </div>
                    <div class="balance-card">
                        <div class="card-label">Pagamentos do Mês</div>
                        <div class="card-value" style="font-size: 24px; color: var(--info);"><?= formatMoney($monthly['payments']) ?></div>
                    </div>
                    <div class="balance-card">
                        <div class="card-label">Cashback Distribuído Mês</div>
                        <div class="card-value" style="font-size: 24px; color: var(--warning);"><?= formatMoney($monthly['cashback_given']) ?></div>
                    </div>
                </div>

                <div class="dashboard-grid">
                    <!-- Pending Recharges -->
                    <div>
                        <?php if (!empty($pendingRec)): ?>
                        <div class="card" style="margin-bottom: 24px; border-color: rgba(255, 182, 39, 0.3);">
                            <div class="card-header">
                                <h3>&#9888; Recargas Pendentes</h3>
                                <a href="recargas.php" class="view-all">Ver todas &#8594;</a>
                            </div>
                            <div class="card-body" style="overflow-x: auto;">
                                <table class="admin-table">
                                    <thead>
                                        <tr>
                                            <th>Usuário</th>
                                            <th>Valor</th>
                                            <th>Método</th>
                                            <th>Data</th>
                                            <th>Ações</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <?php foreach ($pendingRec as $rec): ?>
                                        <tr>
                                            <td>
                                                <div class="user-cell">
                                                    <div class="user-avatar-sm"><?= strtoupper(substr($rec['user_name'], 0, 1)) ?></div>
                                                    <div>
                                                        <div class="user-name"><?= sanitize($rec['user_name']) ?></div>
                                                        <div class="user-email"><?= sanitize($rec['user_email']) ?></div>
                                                    </div>
                                                </div>
                                            </td>
                                            <td><strong><?= formatMoney($rec['amount']) ?></strong></td>
                                            <td><?php
                                                $methods = ['pix' => 'PIX', 'credit_card' => 'Cartão', 'bank_transfer' => 'Transferência'];
                                                echo $methods[$rec['payment_method']] ?? $rec['payment_method'];
                                            ?></td>
                                            <td><?= date('d/m H:i', strtotime($rec['created_at'])) ?></td>
                                            <td>
                                                <div class="action-btns">
                                                    <form method="POST" action="recargas.php" style="display: inline;">
                                                        <input type="hidden" name="recharge_id" value="<?= $rec['id'] ?>">
                                                        <input type="hidden" name="action" value="approve">
                                                        <button type="submit" class="action-btn approve" title="Aprovar">&#10003;</button>
                                                    </form>
                                                    <form method="POST" action="recargas.php" style="display: inline;">
                                                        <input type="hidden" name="recharge_id" value="<?= $rec['id'] ?>">
                                                        <input type="hidden" name="action" value="reject">
                                                        <button type="submit" class="action-btn reject" title="Rejeitar">&#10007;</button>
                                                    </form>
                                                </div>
                                            </td>
                                        </tr>
                                        <?php endforeach; ?>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                        <?php endif; ?>

                        <!-- Recent Transactions -->
                        <div class="card">
                            <div class="card-header">
                                <h3>Transações Recentes</h3>
                                <a href="transacoes.php" class="view-all">Ver todas &#8594;</a>
                            </div>
                            <div class="card-body">
                                <?php foreach ($recentTx as $tx): ?>
                                <div class="transaction-item">
                                    <div class="tx-icon <?= $tx['type'] ?>">
                                        <?php
                                        $icons = ['deposit' => '&#128178;', 'payment' => '&#128179;', 'cashback' => '&#128176;', 'cashback_used' => '&#128176;', 'refund' => '&#128260;'];
                                        echo $icons[$tx['type']] ?? '&#128179;';
                                        ?>
                                    </div>
                                    <div class="tx-details">
                                        <div class="tx-title"><?= sanitize($tx['user_name']) ?></div>
                                        <div class="tx-subtitle"><?= sanitize($tx['description']) ?> &middot; <?= date('d/m H:i', strtotime($tx['created_at'])) ?></div>
                                    </div>
                                    <div class="tx-amount">
                                        <?php
                                        $isPositive = in_array($tx['type'], ['deposit', 'cashback', 'refund']);
                                        $class = $isPositive ? 'positive' : 'negative';
                                        $prefix = $isPositive ? '+' : '-';
                                        ?>
                                        <div class="tx-value <?= $class ?>"><?= $prefix . ' ' . formatMoney($tx['amount']) ?></div>
                                    </div>
                                </div>
                                <?php endforeach; ?>
                            </div>
                        </div>
                    </div>

                    <!-- Side Panel -->
                    <div>
                        <div class="card" style="margin-bottom: 24px;">
                            <div class="card-body" style="padding: 24px; text-align: center;">
                                <div style="font-size: 48px; margin-bottom: 12px;">&#128202;</div>
                                <h3 style="font-size: 16px; margin-bottom: 4px;">Plataforma Ativa</h3>
                                <p style="font-size: 13px; color: var(--text-muted);">v<?= APP_VERSION ?></p>
                                <div style="margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--dark-border);">
                                    <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                                        <span style="font-size: 13px; color: var(--text-muted);">Transações</span>
                                        <span style="font-size: 13px; font-weight: 700;"><?= number_format($totalTransactions) ?></span>
                                    </div>
                                    <div style="display: flex; justify-content: space-between;">
                                        <span style="font-size: 13px; color: var(--text-muted);">Cashback %</span>
                                        <span style="font-size: 13px; font-weight: 700;"><?= CASHBACK_PERCENT ?>%</span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div class="card">
                            <div class="card-header">
                                <h3>Ações Rápidas</h3>
                            </div>
                            <div class="card-body" style="padding: 16px;">
                                <a href="usuarios.php" class="sidebar-link">
                                    <span class="link-icon">&#128101;</span>
                                    Gerenciar Usuários
                                </a>
                                <a href="recargas.php" class="sidebar-link">
                                    <span class="link-icon">&#128178;</span>
                                    Gerenciar Recargas
                                </a>
                                <a href="configuracoes.php" class="sidebar-link">
                                    <span class="link-icon">&#9881;</span>
                                    Configurações
                                </a>
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
