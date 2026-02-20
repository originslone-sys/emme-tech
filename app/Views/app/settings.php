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

<?php require APP_ROOT . '/app/Views/layouts/app_end.php'; ?>
