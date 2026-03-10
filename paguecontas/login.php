<?php
require_once 'includes/auth.php';

if (isLoggedIn()) {
    redirect(isAdmin() ? 'admin/index.php' : 'cliente/index.php');
}

$error = '';
$success = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $result = loginUser($_POST['email'] ?? '', $_POST['password'] ?? '', $pdo);

    if ($result['success']) {
        if ($result['is_admin']) {
            redirect('admin/index.php');
        } else {
            redirect('cliente/index.php');
        }
    } else {
        $error = $result['message'];
    }
}
?>
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - PagueContas</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="assets/css/style.css">
</head>
<body>
    <div class="auth-page">
        <div class="auth-container">
            <a href="index.php" class="auth-logo">
                <div class="logo-icon" style="width:42px;height:42px;background:var(--gradient-primary);border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:20px;">&#9889;</div>
                <span>Pague<span class="text-gradient">Contas</span></span>
            </a>

            <div class="auth-card">
                <h2>Bem-vindo de volta</h2>
                <p class="auth-subtitle">Entre na sua conta para continuar</p>

                <?php if ($error): ?>
                    <div class="alert alert-danger">
                        <span>&#10007;</span> <?= sanitize($error) ?>
                    </div>
                <?php endif; ?>

                <?php if (isset($_GET['registered'])): ?>
                    <div class="alert alert-success">
                        <span>&#10003;</span> Conta criada com sucesso! Faça login para continuar.
                    </div>
                <?php endif; ?>

                <?php if (isset($_GET['logout'])): ?>
                    <div class="alert alert-info">
                        <span>&#8505;</span> Você saiu da sua conta.
                    </div>
                <?php endif; ?>

                <form method="POST" action="">
                    <div class="form-group">
                        <label for="email">E-mail</label>
                        <input type="email" id="email" name="email" class="form-control" placeholder="seu@email.com" value="<?= sanitize($_POST['email'] ?? '') ?>" required>
                    </div>

                    <div class="form-group">
                        <label for="password">Senha</label>
                        <div class="password-toggle">
                            <input type="password" id="password" name="password" class="form-control" placeholder="Sua senha" required>
                            <button type="button" class="toggle-btn">&#128065;</button>
                        </div>
                    </div>

                    <button type="submit" class="btn btn-primary btn-block btn-lg" style="margin-top: 8px;">Entrar</button>
                </form>

                <div class="auth-footer">
                    Não tem uma conta? <a href="register.php">Cadastre-se grátis</a>
                </div>
            </div>

            <div style="text-align: center; margin-top: 20px;">
                <a href="index.php" style="color: var(--text-muted); font-size: 14px;">&#8592; Voltar para o início</a>
            </div>
        </div>
    </div>

    <script src="assets/js/main.js"></script>
</body>
</html>
