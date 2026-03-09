<?php
require_once __DIR__ . '/../includes/auth.php';
requireLogin();

$user = getCurrentUser($pdo);
if (!$user || $user['is_admin']) redirect('../login.php');

// Mark all as read if requested
if (isset($_GET['mark_read'])) {
    $stmt = $pdo->prepare("UPDATE notifications SET is_read = 1 WHERE user_id = ?");
    $stmt->execute([$user['id']]);
    redirect('notificacoes.php');
}

$stmt = $pdo->prepare("SELECT COUNT(*) as count FROM notifications WHERE user_id = ? AND is_read = 0");
$stmt->execute([$user['id']]);
$unreadNotifications = $stmt->fetch()['count'];

$stmt = $pdo->prepare("SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT 50");
$stmt->execute([$user['id']]);
$notifications = $stmt->fetchAll();
?>
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Notificações - PagueContas</title>
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
                    <h1>Notificações</h1>
                    <p class="header-subtitle"><?= $unreadNotifications ?> não lida(s)</p>
                </div>
                <?php if ($unreadNotifications > 0): ?>
                    <a href="?mark_read=1" class="btn btn-secondary btn-sm">Marcar todas como lidas</a>
                <?php endif; ?>
            </div>

            <div class="content-body">
                <div class="card">
                    <div class="card-body">
                        <?php if (empty($notifications)): ?>
                            <div class="empty-state">
                                <div class="empty-icon">&#128276;</div>
                                <h3>Nenhuma notificação</h3>
                                <p>Você será notificado sobre suas transações e novidades.</p>
                            </div>
                        <?php else: ?>
                            <?php foreach ($notifications as $notif): ?>
                                <div class="transaction-item" style="<?= !$notif['is_read'] ? 'background: rgba(108, 43, 217, 0.05); border-left: 3px solid var(--primary);' : '' ?>">
                                    <div class="tx-icon" style="background: rgba(<?php
                                        $colors = ['success' => '6, 214, 160', 'warning' => '255, 182, 39', 'danger' => '247, 37, 133', 'info' => '76, 201, 240'];
                                        echo $colors[$notif['type']] ?? '108, 43, 217';
                                    ?>, 0.12);">
                                        <?php
                                        $icons = ['success' => '&#10003;', 'warning' => '&#9888;', 'danger' => '&#10007;', 'info' => '&#8505;'];
                                        echo $icons[$notif['type']] ?? '&#128276;';
                                        ?>
                                    </div>
                                    <div class="tx-details">
                                        <div class="tx-title"><?= sanitize($notif['title']) ?></div>
                                        <div style="font-size: 13px; color: var(--text-secondary); margin-top: 4px;"><?= sanitize($notif['message']) ?></div>
                                        <div class="tx-subtitle" style="margin-top: 6px;"><?= date('d/m/Y H:i', strtotime($notif['created_at'])) ?></div>
                                    </div>
                                    <?php if (!$notif['is_read']): ?>
                                        <div style="width: 8px; height: 8px; background: var(--primary); border-radius: 50; flex-shrink: 0;"></div>
                                    <?php endif; ?>
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
