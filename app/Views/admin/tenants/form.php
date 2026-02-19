<?php
$pageTitle = $tenant ? 'Editar Tenant' : 'Novo Tenant';
$action    = $tenant ? "/admin/tenants/{$tenant['id']}/update" : '/admin/tenants';
require APP_ROOT . '/app/Views/layouts/admin.php';
?>

<div class="card">
    <div class="card-body">
        <form method="POST" action="<?= $action ?>">
            <?= $csrf ?>
            <div class="form-row">
                <div class="form-group">
                    <label>Nome *</label>
                    <input type="text" name="name" required
                           value="<?= htmlspecialchars($tenant['name'] ?? '') ?>">
                </div>
                <div class="form-group">
                    <label>E-mail *</label>
                    <input type="email" name="email" required
                           value="<?= htmlspecialchars($tenant['email'] ?? '') ?>">
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Senha <?= $tenant ? '(deixe em branco para não alterar)' : '*' ?></label>
                    <input type="password" name="password" <?= !$tenant ? 'required' : '' ?>
                           placeholder="••••••••">
                </div>
                <div class="form-group">
                    <label>Plano</label>
                    <select name="plan_id">
                        <option value="">Sem plano</option>
                        <?php foreach ($plans as $p): ?>
                        <option value="<?= $p['id'] ?>"
                            <?= ($tenant['plan_id'] ?? '') == $p['id'] ? 'selected' : '' ?>>
                            <?= htmlspecialchars($p['name']) ?>
                        </option>
                        <?php endforeach; ?>
                    </select>
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Status</label>
                    <select name="status">
                        <?php foreach (['trial','active','inactive','past_due','canceled'] as $s): ?>
                        <option value="<?= $s ?>"
                            <?= ($tenant['status'] ?? 'trial') === $s ? 'selected' : '' ?>>
                            <?= ucfirst($s) ?>
                        </option>
                        <?php endforeach; ?>
                    </select>
                </div>
                <div class="form-group">
                    <label>Timezone</label>
                    <input type="text" name="timezone"
                           value="<?= htmlspecialchars($tenant['timezone'] ?? 'America/Sao_Paulo') ?>">
                </div>
            </div>
            <div class="form-group">
                <label>Notas internas</label>
                <textarea name="notes" rows="3"><?= htmlspecialchars($tenant['notes'] ?? '') ?></textarea>
            </div>
            <div class="form-actions">
                <a href="/admin/tenants" class="btn">Cancelar</a>
                <button type="submit" class="btn btn-primary">
                    <?= $tenant ? 'Salvar Alterações' : 'Criar Tenant' ?>
                </button>
            </div>
        </form>
    </div>
</div>

<?php require APP_ROOT . '/app/Views/layouts/admin_end.php'; ?>
