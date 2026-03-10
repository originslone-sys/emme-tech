<?php
require_once __DIR__ . '/../includes/auth.php';
requireAdmin();

$success = '';
$error = '';

$stmt = $pdo->query("SELECT COUNT(*) as total FROM recharges WHERE status = 'pending'");
$pendingRecharges = $stmt->fetch()['total'];

// Handle approve/reject
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $action = $_POST['action'] ?? '';
    $rechargeId = intval($_POST['recharge_id'] ?? 0);

    if ($rechargeId > 0) {
        $stmt = $pdo->prepare("SELECT * FROM recharges WHERE id = ? AND status = 'pending'");
        $stmt->execute([$rechargeId]);
        $recharge = $stmt->fetch();

        if ($recharge) {
            if ($action === 'approve') {
                try {
                    $pdo->beginTransaction();

                    // Update recharge status
                    $stmt = $pdo->prepare("UPDATE recharges SET status = 'approved', approved_by = ?, approved_at = NOW() WHERE id = ?");
                    $stmt->execute([$_SESSION['user_id'], $rechargeId]);

                    // Add balance to user
                    $stmt = $pdo->prepare("UPDATE users SET balance = balance + ? WHERE id = ?");
                    $stmt->execute([$recharge['amount'], $recharge['user_id']]);

                    // Get new balance
                    $stmt = $pdo->prepare("SELECT balance FROM users WHERE id = ?");
                    $stmt->execute([$recharge['user_id']]);
                    $newBalance = $stmt->fetch()['balance'];

                    // Record transaction
                    $methods = ['pix' => 'PIX', 'credit_card' => 'Cartão de Crédito', 'bank_transfer' => 'Transferência'];
                    $methodName = $methods[$recharge['payment_method']] ?? $recharge['payment_method'];

                    $stmt = $pdo->prepare("INSERT INTO transactions (user_id, type, amount, balance_after, description, status, reference_id) VALUES (?, 'deposit', ?, ?, ?, 'completed', ?)");
                    $stmt->execute([
                        $recharge['user_id'],
                        $recharge['amount'],
                        $newBalance,
                        'Recarga via ' . $methodName,
                        $recharge['reference_code']
                    ]);

                    // Notify user
                    $stmt = $pdo->prepare("INSERT INTO notifications (user_id, title, message, type) VALUES (?, ?, ?, 'success')");
                    $stmt->execute([
                        $recharge['user_id'],
                        'Recarga Aprovada!',
                        'Sua recarga de ' . formatMoney($recharge['amount']) . ' foi aprovada e o saldo já está disponível.'
                    ]);

                    $pdo->commit();
                    $success = 'Recarga de ' . formatMoney($recharge['amount']) . ' aprovada com sucesso!';
                } catch (Exception $e) {
                    $pdo->rollBack();
                    $error = 'Erro ao aprovar recarga.';
                }
            } elseif ($action === 'reject') {
                $stmt = $pdo->prepare("UPDATE recharges SET status = 'rejected', approved_by = ?, approved_at = NOW(), notes = ? WHERE id = ?");
                $stmt->execute([$_SESSION['user_id'], $_POST['notes'] ?? 'Recarga rejeitada', $rechargeId]);

                $stmt = $pdo->prepare("INSERT INTO notifications (user_id, title, message, type) VALUES (?, ?, ?, 'danger')");
                $stmt->execute([
                    $recharge['user_id'],
                    'Recarga Rejeitada',
                    'Sua recarga de ' . formatMoney($recharge['amount']) . ' foi rejeitada. Motivo: ' . sanitize($_POST['notes'] ?? 'Não especificado')
                ]);

                $success = 'Recarga rejeitada.';
            }
        }
    }

    // Refresh count
    $stmt = $pdo->query("SELECT COUNT(*) as total FROM recharges WHERE status = 'pending'");
    $pendingRecharges = $stmt->fetch()['total'];
}

// Get recharges
$filterStatus = $_GET['status'] ?? 'all';
$sql = "SELECT r.*, u.name as user_name, u.email as user_email FROM recharges r JOIN users u ON r.user_id = u.id";
$params = [];
if ($filterStatus !== 'all') {
    $sql .= " WHERE r.status = ?";
    $params[] = $filterStatus;
}
$sql .= " ORDER BY r.created_at DESC LIMIT 50";
$stmt = $pdo->prepare($sql);
$stmt->execute($params);
$recharges = $stmt->fetchAll();
?>
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Recargas - Admin PagueContas</title>
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
                    <h1>Gerenciar Recargas</h1>
                    <p class="header-subtitle"><?= $pendingRecharges ?> recarga(s) pendente(s)</p>
                </div>
            </div>

            <div class="content-body">
                <?php if ($success): ?>
                    <div class="alert alert-success"><span>&#10003;</span> <?= $success ?></div>
                <?php endif; ?>
                <?php if ($error): ?>
                    <div class="alert alert-danger"><span>&#10007;</span> <?= $error ?></div>
                <?php endif; ?>

                <!-- Filter -->
                <div class="card" style="margin-bottom: 24px;">
                    <div class="card-body" style="padding: 16px 24px;">
                        <div class="tabs" style="max-width: 500px;">
                            <a href="?status=all" class="tab <?= $filterStatus === 'all' ? 'active' : '' ?>" style="text-decoration:none;">Todas</a>
                            <a href="?status=pending" class="tab <?= $filterStatus === 'pending' ? 'active' : '' ?>" style="text-decoration:none;">Pendentes</a>
                            <a href="?status=approved" class="tab <?= $filterStatus === 'approved' ? 'active' : '' ?>" style="text-decoration:none;">Aprovadas</a>
                            <a href="?status=rejected" class="tab <?= $filterStatus === 'rejected' ? 'active' : '' ?>" style="text-decoration:none;">Rejeitadas</a>
                        </div>
                    </div>
                </div>

                <div class="card">
                    <div class="card-body" style="overflow-x: auto;">
                        <table class="admin-table">
                            <thead>
                                <tr>
                                    <th>Código</th>
                                    <th>Usuário</th>
                                    <th>Valor</th>
                                    <th>Método</th>
                                    <th>Status</th>
                                    <th>Data</th>
                                    <th>Ações</th>
                                </tr>
                            </thead>
                            <tbody>
                                <?php if (empty($recharges)): ?>
                                    <tr><td colspan="7" style="text-align: center; padding: 32px; color: var(--text-muted);">Nenhuma recarga encontrada</td></tr>
                                <?php else: ?>
                                    <?php foreach ($recharges as $rec): ?>
                                    <tr>
                                        <td style="font-family: monospace; font-size: 12px;"><?= $rec['reference_code'] ?></td>
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
                                            $methods = ['pix' => 'PIX', 'credit_card' => 'Cartão', 'bank_transfer' => 'Transfer.'];
                                            echo $methods[$rec['payment_method']] ?? $rec['payment_method'];
                                        ?></td>
                                        <td>
                                            <span class="status-badge <?= $rec['status'] ?>">
                                                <?php
                                                $statuses = ['pending' => 'Pendente', 'approved' => 'Aprovada', 'rejected' => 'Rejeitada', 'cancelled' => 'Cancelada'];
                                                echo $statuses[$rec['status']] ?? $rec['status'];
                                                ?>
                                            </span>
                                        </td>
                                        <td style="font-size: 13px;"><?= date('d/m/Y H:i', strtotime($rec['created_at'])) ?></td>
                                        <td>
                                            <?php if ($rec['status'] === 'pending'): ?>
                                                <div class="action-btns">
                                                    <form method="POST" style="display:inline;">
                                                        <input type="hidden" name="recharge_id" value="<?= $rec['id'] ?>">
                                                        <input type="hidden" name="action" value="approve">
                                                        <button type="submit" class="action-btn approve" title="Aprovar">&#10003;</button>
                                                    </form>
                                                    <form method="POST" style="display:inline;">
                                                        <input type="hidden" name="recharge_id" value="<?= $rec['id'] ?>">
                                                        <input type="hidden" name="action" value="reject">
                                                        <button type="submit" class="action-btn reject" title="Rejeitar" onclick="return confirm('Rejeitar esta recarga?')">&#10007;</button>
                                                    </form>
                                                </div>
                                            <?php else: ?>
                                                <span style="font-size: 12px; color: var(--text-muted);">-</span>
                                            <?php endif; ?>
                                        </td>
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
