<?php
require_once __DIR__ . '/../includes/auth.php';
requireAdmin();

$success = '';
$error = '';

// Count pending recharges for sidebar badge
$stmt = $pdo->query("SELECT COUNT(*) as total FROM recharges WHERE status = 'pending'");
$pendingRecharges = $stmt->fetch()['total'];

// Handle actions
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $action = $_POST['action'] ?? '';
    $userId = intval($_POST['user_id'] ?? 0);

    if ($userId > 0) {
        if ($action === 'block') {
            $stmt = $pdo->prepare("UPDATE users SET status = 'blocked' WHERE id = ? AND is_admin = 0");
            $stmt->execute([$userId]);
            $success = 'Usuário bloqueado com sucesso.';
        } elseif ($action === 'activate') {
            $stmt = $pdo->prepare("UPDATE users SET status = 'active' WHERE id = ? AND is_admin = 0");
            $stmt->execute([$userId]);
            $success = 'Usuário ativado com sucesso.';
        } elseif ($action === 'add_balance') {
            $amount = floatval($_POST['amount'] ?? 0);
            if ($amount > 0) {
                $pdo->beginTransaction();
                $stmt = $pdo->prepare("UPDATE users SET balance = balance + ? WHERE id = ?");
                $stmt->execute([$amount, $userId]);

                $stmt = $pdo->prepare("SELECT balance FROM users WHERE id = ?");
                $stmt->execute([$userId]);
                $newBalance = $stmt->fetch()['balance'];

                $stmt = $pdo->prepare("INSERT INTO transactions (user_id, type, amount, balance_after, description, status) VALUES (?, 'deposit', ?, ?, 'Crédito manual pelo administrador', 'completed')");
                $stmt->execute([$userId, $amount, $newBalance]);
                $pdo->commit();
                $success = 'Saldo de ' . formatMoney($amount) . ' adicionado com sucesso.';
            }
        }
    }
}

// Search
$search = sanitize($_GET['search'] ?? '');
$sql = "SELECT * FROM users WHERE is_admin = 0";
$params = [];
if ($search) {
    $sql .= " AND (name LIKE ? OR email LIKE ?)";
    $params = ["%$search%", "%$search%"];
}
$sql .= " ORDER BY created_at DESC";
$stmt = $pdo->prepare($sql);
$stmt->execute($params);
$users = $stmt->fetchAll();
?>
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Usuários - Admin PagueContas</title>
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
                    <h1>Gerenciar Usuários</h1>
                    <p class="header-subtitle"><?= count($users) ?> usuário(s) cadastrado(s)</p>
                </div>
            </div>

            <div class="content-body">
                <?php if ($success): ?>
                    <div class="alert alert-success"><span>&#10003;</span> <?= $success ?></div>
                <?php endif; ?>
                <?php if ($error): ?>
                    <div class="alert alert-danger"><span>&#10007;</span> <?= $error ?></div>
                <?php endif; ?>

                <!-- Search -->
                <div class="card" style="margin-bottom: 24px;">
                    <div class="card-body" style="padding: 16px 24px;">
                        <form method="GET" style="display: flex; gap: 12px;">
                            <input type="text" name="search" class="form-control" placeholder="Buscar por nome ou e-mail..." value="<?= $search ?>" style="flex: 1;">
                            <button type="submit" class="btn btn-primary btn-sm">Buscar</button>
                            <?php if ($search): ?>
                                <a href="usuarios.php" class="btn btn-secondary btn-sm">Limpar</a>
                            <?php endif; ?>
                        </form>
                    </div>
                </div>

                <!-- Users Table -->
                <div class="card">
                    <div class="card-body" style="overflow-x: auto;">
                        <table class="admin-table">
                            <thead>
                                <tr>
                                    <th>Usuário</th>
                                    <th>Saldo</th>
                                    <th>Cashback</th>
                                    <th>Status</th>
                                    <th>Cadastro</th>
                                    <th>Ações</th>
                                </tr>
                            </thead>
                            <tbody>
                                <?php foreach ($users as $u): ?>
                                <tr>
                                    <td>
                                        <div class="user-cell">
                                            <div class="user-avatar-sm"><?= strtoupper(substr($u['name'], 0, 1)) ?></div>
                                            <div>
                                                <div class="user-name"><?= sanitize($u['name']) ?></div>
                                                <div class="user-email"><?= sanitize($u['email']) ?></div>
                                            </div>
                                        </div>
                                    </td>
                                    <td><strong><?= formatMoney($u['balance']) ?></strong></td>
                                    <td style="color: var(--success);"><?= formatMoney($u['cashback_balance']) ?></td>
                                    <td><span class="status-badge <?= $u['status'] ?>"><?= $u['status'] === 'active' ? 'Ativo' : ($u['status'] === 'blocked' ? 'Bloqueado' : 'Inativo') ?></span></td>
                                    <td style="font-size: 13px; color: var(--text-muted);"><?= date('d/m/Y', strtotime($u['created_at'])) ?></td>
                                    <td>
                                        <div class="action-btns">
                                            <?php if ($u['status'] === 'active'): ?>
                                                <form method="POST" style="display:inline;">
                                                    <input type="hidden" name="user_id" value="<?= $u['id'] ?>">
                                                    <input type="hidden" name="action" value="block">
                                                    <button type="submit" class="action-btn reject" title="Bloquear" onclick="return confirm('Bloquear este usuário?')">&#128683;</button>
                                                </form>
                                            <?php else: ?>
                                                <form method="POST" style="display:inline;">
                                                    <input type="hidden" name="user_id" value="<?= $u['id'] ?>">
                                                    <input type="hidden" name="action" value="activate">
                                                    <button type="submit" class="action-btn approve" title="Ativar">&#10003;</button>
                                                </form>
                                            <?php endif; ?>
                                            <button class="action-btn" title="Adicionar saldo" onclick="document.getElementById('balanceModal<?= $u['id'] ?>').style.display='flex'">&#128178;</button>
                                        </div>

                                        <!-- Balance Modal -->
                                        <div class="modal-overlay" id="balanceModal<?= $u['id'] ?>">
                                            <div class="modal">
                                                <button class="modal-close" onclick="this.closest('.modal-overlay').style.display='none'">&times;</button>
                                                <h2>Adicionar Saldo</h2>
                                                <p class="modal-subtitle">Adicionar saldo para <?= sanitize($u['name']) ?></p>
                                                <form method="POST">
                                                    <input type="hidden" name="user_id" value="<?= $u['id'] ?>">
                                                    <input type="hidden" name="action" value="add_balance">
                                                    <div class="form-group">
                                                        <label>Valor</label>
                                                        <input type="number" name="amount" class="form-control" min="1" step="0.01" placeholder="0.00" required>
                                                    </div>
                                                    <button type="submit" class="btn btn-success btn-block">Adicionar Saldo</button>
                                                </form>
                                            </div>
                                        </div>
                                    </td>
                                </tr>
                                <?php endforeach; ?>
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
