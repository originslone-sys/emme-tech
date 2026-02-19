<?php
$pageTitle = 'Configurações';
require APP_ROOT . '/app/Views/layouts/app.php';
?>

<div class="grid-2">

<!-- Profile -->
<div class="card">
    <div class="card-header"><h3>Perfil do Negócio</h3></div>
    <div class="card-body">
        <form method="POST" action="/app/settings/profile">
            <?= $csrf ?>
            <div class="form-group">
                <label>Nome</label>
                <input type="text" name="name" value="<?= htmlspecialchars($tenant['name'] ?? '') ?>">
            </div>
            <div class="form-group">
                <label>Nome do Negócio</label>
                <input type="text" name="business_name" value="<?= htmlspecialchars($tenant['business_name'] ?? '') ?>">
            </div>
            <div class="form-group">
                <label>Telefone do Negócio</label>
                <input type="text" name="business_phone" value="<?= htmlspecialchars($tenant['business_phone'] ?? '') ?>">
            </div>
            <div class="form-group">
                <label>Timezone</label>
                <select name="timezone">
                    <?php
                    $zones = ['America/Sao_Paulo','America/Manaus','America/Belem','America/Fortaleza',
                              'America/New_York','America/Los_Angeles','Europe/London','Europe/Lisbon'];
                    foreach ($zones as $z): ?>
                    <option value="<?= $z ?>" <?= ($tenant['timezone'] ?? 'America/Sao_Paulo') === $z ? 'selected' : '' ?>><?= $z ?></option>
                    <?php endforeach; ?>
                </select>
            </div>
            <button type="submit" class="btn btn-primary">Salvar perfil</button>
        </form>
    </div>
</div>

<!-- Password -->
<div class="card">
    <div class="card-header"><h3>Alterar Senha</h3></div>
    <div class="card-body">
        <form method="POST" action="/app/settings/password">
            <?= $csrf ?>
            <div class="form-group">
                <label>Senha atual</label>
                <input type="password" name="current_password" required>
            </div>
            <div class="form-group">
                <label>Nova senha (min. 8 chars)</label>
                <input type="password" name="new_password" required minlength="8">
            </div>
            <div class="form-group">
                <label>Confirmar nova senha</label>
                <input type="password" name="confirm_password" required>
            </div>
            <button type="submit" class="btn btn-primary">Alterar senha</button>
        </form>
    </div>
</div>

</div><!-- .grid-2 -->

<!-- OpenRouter Token -->
<div class="card mt-4">
    <div class="card-header"><h3>Token OpenRouter (padrão do tenant)</h3></div>
    <div class="card-body">
        <?php if ($hasToken): ?>
        <p class="text-muted">Token configurado: <code><?= htmlspecialchars($tokenPreview) ?></code></p>
        <?php else: ?>
        <p class="text-warning">Nenhum token configurado. Obtenha em <a href="https://openrouter.ai/keys" target="_blank">openrouter.ai/keys</a>.</p>
        <?php endif; ?>
        <form method="POST" action="/app/settings/openrouter-token">
            <?= $csrf ?>
            <div class="form-group">
                <label><?= $hasToken ? 'Novo token (substituir)' : 'Token OpenRouter' ?></label>
                <input type="password" name="openrouter_token" required
                       placeholder="sk-or-v1-...">
            </div>
            <button type="submit" class="btn btn-primary">Salvar token</button>
        </form>
    </div>
</div>

<?php require APP_ROOT . '/app/Views/layouts/app_end.php'; ?>
