<?php
require_once __DIR__ . '/../includes/auth.php';
requireLogin();

$user = getCurrentUser($pdo);
if (!$user || $user['is_admin']) redirect('../login.php');

$stmt = $pdo->prepare("SELECT COUNT(*) as count FROM notifications WHERE user_id = ? AND is_read = 0");
$stmt->execute([$user['id']]);
$unreadNotifications = $stmt->fetch()['count'];

// Filters
$filterType = $_GET['type'] ?? 'all';
$filterMonth = $_GET['month'] ?? date('Y-m');

$sql = "SELECT * FROM transactions WHERE user_id = ?";
$params = [$user['id']];

if ($filterType !== 'all') {
    $sql .= " AND type = ?";
    $params[] = $filterType;
}

if ($filterMonth) {
    $sql .= " AND DATE_FORMAT(created_at, '%Y-%m') = ?";
    $params[] = $filterMonth;
}

$sql .= " ORDER BY created_at DESC LIMIT 50";
$stmt = $pdo->prepare($sql);
$stmt->execute($params);
$transactions = $stmt->fetchAll();

// Totals for filtered period
$sqlTotals = "SELECT
    COALESCE(SUM(CASE WHEN type IN ('deposit','cashback','refund') AND status='completed' THEN amount END), 0) as entradas,
    COALESCE(SUM(CASE WHEN type IN ('payment','cashback_used') AND status='completed' THEN amount END), 0) as saidas
    FROM transactions WHERE user_id = ?";
$paramsT = [$user['id']];
if ($filterMonth) {
    $sqlTotals .= " AND DATE_FORMAT(created_at, '%Y-%m') = ?";
    $paramsT[] = $filterMonth;
}
$stmt = $pdo->prepare($sqlTotals);
$stmt->execute($paramsT);
$totals = $stmt->fetch();
?>
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Extrato - PagueContas</title>
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
                    <h1>Extrato</h1>
                    <p class="header-subtitle">Todas as suas movimentações</p>
                </div>
            </div>

            <div class="content-body">
                <!-- Summary cards -->
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px;">
                    <div class="balance-card">
                        <div class="card-label">Entradas</div>
                        <div class="card-value" style="font-size: 24px; color: var(--success);"><?= formatMoney($totals['entradas']) ?></div>
                    </div>
                    <div class="balance-card">
                        <div class="card-label">Saídas</div>
                        <div class="card-value" style="font-size: 24px; color: var(--danger);"><?= formatMoney($totals['saidas']) ?></div>
                    </div>
                    <div class="balance-card">
                        <div class="card-label">Saldo Atual</div>
                        <div class="card-value" style="font-size: 24px;"><?= formatMoney($user['balance']) ?></div>
                    </div>
                </div>

                <!-- Filters -->
                <div class="card" style="margin-bottom: 24px;">
                    <div class="card-body" style="padding: 16px 24px;">
                        <form method="GET" style="display: flex; gap: 16px; align-items: end; flex-wrap: wrap;">
                            <div class="form-group" style="margin-bottom: 0; flex: 1; min-width: 150px;">
                                <label style="font-size: 12px;">Tipo</label>
                                <select name="type" class="form-control" style="padding: 10px 14px;">
                                    <option value="all" <?= $filterType === 'all' ? 'selected' : '' ?>>Todos</option>
                                    <option value="deposit" <?= $filterType === 'deposit' ? 'selected' : '' ?>>Depósitos</option>
                                    <option value="payment" <?= $filterType === 'payment' ? 'selected' : '' ?>>Pagamentos</option>
                                    <option value="cashback" <?= $filterType === 'cashback' ? 'selected' : '' ?>>Cashback</option>
                                </select>
                            </div>
                            <div class="form-group" style="margin-bottom: 0; flex: 1; min-width: 150px;">
                                <label style="font-size: 12px;">Mês</label>
                                <input type="month" name="month" value="<?= $filterMonth ?>" class="form-control" style="padding: 10px 14px;">
                            </div>
                            <button type="submit" class="btn btn-primary btn-sm">Filtrar</button>
                        </form>
                    </div>
                </div>

                <!-- Transactions -->
                <div class="card">
                    <div class="card-header">
                        <h3>Movimentações</h3>
                        <span style="font-size: 13px; color: var(--text-muted);"><?= count($transactions) ?> registro(s)</span>
                    </div>
                    <div class="card-body">
                        <?php if (empty($transactions)): ?>
                            <div class="empty-state">
                                <div class="empty-icon">&#128203;</div>
                                <h3>Nenhuma movimentação encontrada</h3>
                                <p>Altere os filtros ou faça sua primeira transação.</p>
                            </div>
                        <?php else: ?>
                            <?php foreach ($transactions as $tx): ?>
                                <div class="transaction-item">
                                    <div class="tx-icon <?= $tx['type'] ?>">
                                        <?php
                                        $icons = ['deposit' => '&#128178;', 'payment' => '&#128179;', 'cashback' => '&#128176;', 'cashback_used' => '&#128176;', 'refund' => '&#128260;'];
                                        echo $icons[$tx['type']] ?? '&#128179;';
                                        ?>
                                    </div>
                                    <div class="tx-details">
                                        <div class="tx-title"><?= sanitize($tx['description']) ?></div>
                                        <div class="tx-subtitle">
                                            <?= date('d/m/Y H:i', strtotime($tx['created_at'])) ?>
                                            <?php if ($tx['reference_id']): ?>
                                                &middot; <?= $tx['reference_id'] ?>
                                            <?php endif; ?>
                                        </div>
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
                                            Saldo: <?= formatMoney($tx['balance_after']) ?>
                                        </div>
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
