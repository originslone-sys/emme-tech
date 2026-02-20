<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Admin Login — EMME Tech</title>
<link rel="stylesheet" href="/assets/css/app.css">
</head>
<body class="layout-auth">
<div class="auth-container">
    <div class="auth-card">
        <div class="auth-logo"><span class="brand-emme">EMME</span> Tech Admin</div>
        <h2>Acesso Administrativo</h2>

        <?php if ($flash = \App\Core\Session::flash('error')): ?>
            <div class="alert alert-error"><?= htmlspecialchars($flash) ?></div>
        <?php endif; ?>

        <form method="POST" action="/admin/login">
            <?= $csrf ?>
            <div class="form-group">
                <label for="email">E-mail</label>
                <input type="email" id="email" name="email" required
                       placeholder="admin@exemplo.com" autocomplete="email">
            </div>
            <div class="form-group">
                <label for="password">Senha</label>
                <input type="password" id="password" name="password" required
                       placeholder="••••••••" autocomplete="current-password">
            </div>
            <button type="submit" class="btn btn-primary btn-block">Entrar</button>
        </form>
    </div>
</div>
</body>
</html>
