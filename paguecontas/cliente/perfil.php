<?php
require_once __DIR__ . '/../includes/auth.php';
requireLogin();

$user = getCurrentUser($pdo);
if (!$user || $user['is_admin']) redirect('../login.php');

$stmt = $pdo->prepare("SELECT COUNT(*) as count FROM notifications WHERE user_id = ? AND is_read = 0");
$stmt->execute([$user['id']]);
$unreadNotifications = $stmt->fetch()['count'];

$error = '';
$success = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $action = $_POST['action'] ?? '';

    if ($action === 'update_profile') {
        $name = sanitize($_POST['name'] ?? '');
        $phone = sanitize($_POST['phone'] ?? '');
        $cpf = sanitize($_POST['cpf'] ?? '');

        if (empty($name)) {
            $error = 'O nome é obrigatório.';
        } else {
            $stmt = $pdo->prepare("UPDATE users SET name = ?, phone = ?, cpf = ? WHERE id = ?");
            $stmt->execute([$name, $phone, $cpf, $user['id']]);
            $_SESSION['user_name'] = $name;
            $success = 'Perfil atualizado com sucesso!';
            $user = getCurrentUser($pdo);
        }
    } elseif ($action === 'change_password') {
        $currentPass = $_POST['current_password'] ?? '';
        $newPass = $_POST['new_password'] ?? '';
        $confirmPass = $_POST['confirm_password'] ?? '';

        if (!password_verify($currentPass, $user['password'] ?? '')) {
            // Re-fetch with password
            $stmt = $pdo->prepare("SELECT password FROM users WHERE id = ?");
            $stmt->execute([$user['id']]);
            $userData = $stmt->fetch();
            if (!password_verify($currentPass, $userData['password'])) {
                $error = 'Senha atual incorreta.';
            }
        }

        if (!$error) {
            if (strlen($newPass) < 6) {
                $error = 'A nova senha deve ter no mínimo 6 caracteres.';
            } elseif ($newPass !== $confirmPass) {
                $error = 'As senhas não coincidem.';
            } else {
                $hashed = password_hash($newPass, PASSWORD_DEFAULT);
                $stmt = $pdo->prepare("UPDATE users SET password = ? WHERE id = ?");
                $stmt->execute([$hashed, $user['id']]);
                $success = 'Senha alterada com sucesso!';
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
    <title>Meu Perfil - PagueContas</title>
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
                    <h1>Meu Perfil</h1>
                    <p class="header-subtitle">Gerencie suas informações pessoais</p>
                </div>
            </div>

            <div class="content-body">
                <?php if ($success): ?>
                    <div class="alert alert-success"><span>&#10003;</span> <?= $success ?></div>
                <?php endif; ?>
                <?php if ($error): ?>
                    <div class="alert alert-danger"><span>&#10007;</span> <?= sanitize($error) ?></div>
                <?php endif; ?>

                <div class="dashboard-grid">
                    <div>
                        <div class="card" style="margin-bottom: 24px;">
                            <div class="card-header"><h3>Informações Pessoais</h3></div>
                            <div class="card-body" style="padding: 24px;">
                                <form method="POST">
                                    <input type="hidden" name="action" value="update_profile">
                                    <div class="form-group">
                                        <label>Nome Completo</label>
                                        <input type="text" name="name" class="form-control" value="<?= sanitize($user['name']) ?>" required>
                                    </div>
                                    <div class="form-group">
                                        <label>E-mail</label>
                                        <input type="email" class="form-control" value="<?= sanitize($user['email']) ?>" disabled>
                                        <div class="form-text">O e-mail não pode ser alterado.</div>
                                    </div>
                                    <div class="form-row">
                                        <div class="form-group">
                                            <label>CPF</label>
                                            <input type="text" name="cpf" class="form-control" value="<?= sanitize($user['cpf'] ?? '') ?>" placeholder="000.000.000-00">
                                        </div>
                                        <div class="form-group">
                                            <label>Telefone</label>
                                            <input type="text" name="phone" class="form-control" value="<?= sanitize($user['phone'] ?? '') ?>" placeholder="(00) 00000-0000">
                                        </div>
                                    </div>
                                    <button type="submit" class="btn btn-primary">Salvar Alterações</button>
                                </form>
                            </div>
                        </div>

                        <div class="card">
                            <div class="card-header"><h3>Alterar Senha</h3></div>
                            <div class="card-body" style="padding: 24px;">
                                <form method="POST">
                                    <input type="hidden" name="action" value="change_password">
                                    <div class="form-group">
                                        <label>Senha Atual</label>
                                        <input type="password" name="current_password" class="form-control" required>
                                    </div>
                                    <div class="form-row">
                                        <div class="form-group">
                                            <label>Nova Senha</label>
                                            <input type="password" name="new_password" class="form-control" minlength="6" required>
                                        </div>
                                        <div class="form-group">
                                            <label>Confirmar Nova Senha</label>
                                            <input type="password" name="confirm_password" class="form-control" minlength="6" required>
                                        </div>
                                    </div>
                                    <button type="submit" class="btn btn-primary">Alterar Senha</button>
                                </form>
                            </div>
                        </div>
                    </div>

                    <div class="card" style="align-self: start;">
                        <div class="card-body" style="padding: 32px; text-align: center;">
                            <div style="width: 80px; height: 80px; background: var(--gradient-primary); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 32px; font-weight: 700; margin: 0 auto 16px;">
                                <?= strtoupper(substr($user['name'], 0, 1)) ?>
                            </div>
                            <h3 style="font-size: 18px;"><?= sanitize($user['name']) ?></h3>
                            <p style="font-size: 13px; color: var(--text-muted); margin-top: 4px;"><?= sanitize($user['email']) ?></p>
                            <div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid var(--dark-border);">
                                <div style="font-size: 12px; color: var(--text-muted);">Membro desde</div>
                                <div style="font-size: 14px; font-weight: 600;"><?= date('d/m/Y', strtotime($user['created_at'])) ?></div>
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
