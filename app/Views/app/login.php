<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title><?= $mode === 'register' ? 'Criar Conta' : 'Entrar' ?> — WAMS</title>
<link rel="stylesheet" href="/assets/css/app.css">
</head>
<body class="layout-auth">
<div class="auth-container">
    <div class="auth-card">
        <div class="auth-logo">🤖 WAMS</div>
        <div class="auth-tabs">
            <a href="/app/login" class="<?= $mode === 'login' ? 'active' : '' ?>">Entrar</a>
            <a href="/app/register" class="<?= $mode === 'register' ? 'active' : '' ?>">Criar conta</a>
        </div>

        <?php if ($flash = \App\Core\Session::flash('error')): ?>
            <div class="alert alert-error"><?= htmlspecialchars($flash) ?></div>
        <?php endif; ?>

        <?php if ($mode === 'login'): ?>
        <form method="POST" action="/app/login">
            <?= $csrf ?>
            <div class="form-group">
                <label>E-mail</label>
                <input type="email" name="email" required placeholder="voce@empresa.com">
            </div>
            <div class="form-group">
                <label>Senha</label>
                <input type="password" name="password" required placeholder="••••••••">
            </div>
            <button type="submit" class="btn btn-primary btn-block">Entrar</button>
        </form>

        <?php else: // register ?>
        <form method="POST" action="/app/register">
            <?= $csrf ?>
            <div class="form-group">
                <label>Nome *</label>
                <input type="text" name="name" required placeholder="Seu nome ou empresa">
            </div>
            <div class="form-group">
                <label>E-mail *</label>
                <input type="email" name="email" required placeholder="voce@empresa.com">
            </div>
            <div class="form-group">
                <label>Senha * (mínimo 8 caracteres)</label>
                <input type="password" name="password" required minlength="8" placeholder="••••••••">
            </div>
            <div class="form-group">
                <label>Confirmar senha *</label>
                <input type="password" name="password_confirm" required placeholder="••••••••">
            </div>
            <p class="text-muted text-sm">Ao se registrar, você inicia um trial gratuito de 14 dias.</p>
            <button type="submit" class="btn btn-primary btn-block">Criar conta grátis</button>
        </form>
        <?php endif; ?>

        <p class="auth-alt">
            <?= $mode === 'login'
                ? 'Não tem conta? <a href="/app/register">Registre-se grátis</a>'
                : 'Já tem conta? <a href="/app/login">Entrar</a>' ?>
        </p>
    </div>
</div>
</body>
</html>
