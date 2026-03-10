<?php
require_once __DIR__ . '/../includes/auth.php';
requireAdmin();

$stmt = $pdo->query("SELECT COUNT(*) as total FROM recharges WHERE status = 'pending'");
$pendingRecharges = $stmt->fetch()['total'];

$filterType = $_GET['type'] ?? 'all';
$search = sanitize($_GET['search'] ?? '');

$sql = "SELECT t.*, u.name as user_name, u.email as user_email FROM transactions t JOIN users u ON t.user_id = u.id WHERE 1=1";
$params = [];

if ($filterType !== 'all') {
    $sql .= " AND t.type = ?";
    $params[] = $filterType;
}

if ($search) {
    $sql .= " AND (u.name LIKE ? OR u.email LIKE ? OR t.reference_id LIKE ?)";
    $params = array_merge($params, ["%$search%", "%$search%", "%$search%"]);
}

$sql .= " ORDER BY t.created_at DESC LIMIT 100";
$stmt = $pdo->prepare($sql);
$stmt->execute($params);
$transactions = $stmt->fetchAll();
?>
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Transações - Admin PagueContas</title>
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
                    <h1>Transações</h1>
                    <p class="header-subtitle">Todas as transações da plataforma</p>
                </div>
            </div>

            <div class="content-body">
                <!-- Filters -->
                <div class="card" style="margin-bottom: 24px;">
                    <div class="card-body" style="padding: 16px 24px;">
                        <form method="GET" style="display: flex; gap: 12px; flex-wrap: wrap; align-items: end;">
                            <div class="form-group" style="margin-bottom: 0; flex: 1; min-width: 200px;">
                                <input type="text" name="search" class="form-control" placeholder="Buscar por nome, e-mail ou referência..." value="<?= $search ?>" style="padding: 10px 14px;">
                            </div>
                            <select name="type" class="form-control" style="width: auto; padding: 10px 14px;">
                                <option value="all" <?= $filterType === 'all' ? 'selected' : '' ?>>Todos os tipos</option>
                                <option value="deposit" <?= $filterType === 'deposit' ? 'selected' : '' ?>>Depósitos</option>
                                <option value="payment" <?= $filterType === 'payment' ? 'selected' : '' ?>>Pagamentos</option>
                                <option value="cashback" <?= $filterType === 'cashback' ? 'selected' : '' ?>>Cashback</option>
                                <option value="cashback_used" <?= $filterType === 'cashback_used' ? 'selected' : '' ?>>Cashback Usado</option>
                                <option value="refund" <?= $filterType === 'refund' ? 'selected' : '' ?>>Reembolso</option>
                            </select>
                            <button type="submit" class="btn btn-primary btn-sm">Filtrar</button>
                        </form>
                    </div>
                </div>

                <div class="card">
                    <div class="card-header">
                        <h3>Resultados</h3>
                        <span style="font-size: 13px; color: var(--text-muted);"><?= count($transactions) ?> transação(ões)</span>
                    </div>
                    <div class="card-body" style="overflow-x: auto;">
                        <table class="admin-table">
                            <thead>
                                <tr>
                                    <th>Ref.</th>
                                    <th>Usuário</th>
                                    <th>Tipo</th>
                                    <th>Descrição</th>
                                    <th>Valor</th>
                                    <th>Status</th>
                                    <th>Data</th>
                                </tr>
                            </thead>
                            <tbody>
                                <?php if (empty($transactions)): ?>
                                    <tr><td colspan="7" style="text-align: center; padding: 32px; color: var(--text-muted);">Nenhuma transação encontrada</td></tr>
                                <?php else: ?>
                                    <?php foreach ($transactions as $tx): ?>
                                    <tr>
                                        <td style="font-family: monospace; font-size: 11px;"><?= $tx['reference_id'] ?? '-' ?></td>
                                        <td>
                                            <div class="user-cell">
                                                <div class="user-avatar-sm"><?= strtoupper(substr($tx['user_name'], 0, 1)) ?></div>
                                                <div>
                                                    <div class="user-name"><?= sanitize($tx['user_name']) ?></div>
                                                </div>
                                            </div>
                                        </td>
                                        <td>
                                            <?php
                                            $types = ['deposit' => ['Depósito', 'var(--success)'], 'payment' => ['Pagamento', 'var(--danger)'], 'cashback' => ['Cashback', 'var(--warning)'], 'cashback_used' => ['Cashback Usado', 'var(--info)'], 'refund' => ['Reembolso', 'var(--success)']];
                                            $type = $types[$tx['type']] ?? ['Outro', 'var(--text-muted)'];
                                            ?>
                                            <span style="color: <?= $type[1] ?>; font-size: 13px; font-weight: 600;"><?= $type[0] ?></span>
                                        </td>
                                        <td style="font-size: 13px; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;"><?= sanitize($tx['description']) ?></td>
                                        <td>
                                            <?php
                                            $isPositive = in_array($tx['type'], ['deposit', 'cashback', 'refund']);
                                            ?>
                                            <strong style="color: <?= $isPositive ? 'var(--success)' : 'var(--danger)' ?>;">
                                                <?= ($isPositive ? '+' : '-') . ' ' . formatMoney($tx['amount']) ?>
                                            </strong>
                                        </td>
                                        <td><span class="status-badge <?= $tx['status'] ?>"><?= ucfirst($tx['status']) ?></span></td>
                                        <td style="font-size: 13px; color: var(--text-muted);"><?= date('d/m/Y H:i', strtotime($tx['created_at'])) ?></td>
                                    </tr>
                                    <?php endforeach; ?>
                                <?php endif; ?>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <script src="../assets/js/main.js"></script>
</body>
</html>
