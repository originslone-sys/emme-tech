<?php
$pageTitle = $tenant ? 'Editar Cliente' : 'Novo Cliente';
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
                    <label>Créditos iniciais</label>
                    <input type="number" name="credits" min="0"
                           value="<?= (int)($tenant['credits'] ?? 50) ?>">
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Status</label>
                    <select name="status">
                        <?php foreach (['active','trial','inactive'] as $s): ?>
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
                    <?= $tenant ? 'Salvar Alterações' : 'Criar Cliente' ?>
                </button>
            </div>
        </form>
    </div>
</div>

<?php if ($tenant): ?>
<!-- Add Credits -->
<div class="card mt-4">
    <div class="card-header">
        <h3>Adicionar Créditos Manualmente</h3>
        <span class="text-muted">Saldo atual: <strong><?= number_format((int)$tenant['credits']) ?> créditos</strong></span>
    </div>
    <div class="card-body">
        <form method="POST" action="/admin/tenants/<?= $tenant['id'] ?>/add-credits" class="form-inline">
            <?= $csrf ?>
            <div class="form-group">
                <label>Quantidade de créditos</label>
                <input type="number" name="credits" min="1" required placeholder="Ex: 100">
            </div>
            <div class="form-group">
                <label>Motivo (opcional)</label>
                <input type="text" name="description" placeholder="Ex: Cortesia, compensação...">
            </div>
            <button type="submit" class="btn btn-success">Adicionar Créditos</button>
        </form>
    </div>
</div>

<?php if (!empty($recentTransactions)): ?>
<!-- Recent Transactions -->
<div class="card mt-4">
    <div class="card-header"><h3>Últimas Transações</h3></div>
    <table class="table">
        <thead>
        <tr><th>Data</th><th>Tipo</th><th>Qtd</th><th>Descrição</th></tr>
        </thead>
        <tbody>
        <?php foreach ($recentTransactions as $tx): ?>
        <tr>
            <td><?= date('d/m/Y H:i', strtotime($tx['created_at'])) ?></td>
            <td><span class="badge badge-<?= $tx['type'] === 'usage' ? 'secondary' : 'success' ?>"><?= $tx['type'] ?></span></td>
            <td class="<?= $tx['amount'] < 0 ? 'text-danger' : 'text-success' ?>">
                <?= $tx['amount'] > 0 ? '+' : '' ?><?= $tx['amount'] ?>
            </td>
            <td><?= htmlspecialchars($tx['description'] ?? '') ?></td>
        </tr>
        <?php endforeach; ?>
        </tbody>
    </table>
</div>
<?php endif; ?>
<?php endif; ?>

<?php require APP_ROOT . '/app/Views/layouts/admin_end.php'; ?>
