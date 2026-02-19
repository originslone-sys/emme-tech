<?php
$pageTitle = 'Planos';
require APP_ROOT . '/app/Views/layouts/admin.php';
?>

<div class="card">
    <div class="card-header">
        <h3>Planos de Assinatura</h3>
        <a href="/admin/plans/create" class="btn btn-primary">+ Novo Plano</a>
    </div>
    <table class="table">
        <thead>
        <tr>
            <th>#</th><th>Nome</th><th>Preço Mensal</th><th>Agentes</th>
            <th>Crons</th><th>Docs</th><th>Tenants</th><th>Status</th><th>Ações</th>
        </tr>
        </thead>
        <tbody>
        <?php foreach ($plans as $p): ?>
        <tr>
            <td><?= $p['id'] ?></td>
            <td><strong><?= htmlspecialchars($p['name']) ?></strong><br>
                <small class="text-muted"><?= $p['slug'] ?></small></td>
            <td>R$ <?= number_format($p['price_monthly'], 2, ',', '.') ?></td>
            <td><?= $p['max_agents'] ?></td>
            <td><?= $p['feature_crons'] ? $p['max_crons'] : '—' ?></td>
            <td><?= $p['feature_docs'] ? $p['max_docs'] : '—' ?></td>
            <td><?= $p['tenant_count'] ?></td>
            <td><span class="badge badge-<?= $p['is_active'] ? 'active' : 'inactive' ?>">
                <?= $p['is_active'] ? 'Ativo' : 'Inativo' ?></span></td>
            <td>
                <a href="/admin/plans/<?= $p['id'] ?>/edit" class="btn btn-sm">Editar</a>
                <form method="POST" action="/admin/plans/<?= $p['id'] ?>/delete"
                      style="display:inline" onsubmit="return confirm('Remover plano?')">
                    <?= $csrf ?>
                    <button class="btn btn-sm btn-danger">Excluir</button>
                </form>
            </td>
        </tr>
        <?php endforeach; ?>
        </tbody>
    </table>
</div>

<?php require APP_ROOT . '/app/Views/layouts/admin_end.php'; ?>
