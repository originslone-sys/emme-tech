<?php
$pageTitle = 'Tenants';
require APP_ROOT . '/app/Views/layouts/admin.php';
?>

<div class="card">
    <div class="card-header">
        <form method="GET" class="filter-form">
            <input type="text" name="q" value="<?= htmlspecialchars($search) ?>" placeholder="Buscar nome/e-mail...">
            <select name="status">
                <option value="">Todos status</option>
                <?php foreach (['active','trial','inactive','past_due','canceled'] as $s): ?>
                <option value="<?= $s ?>" <?= $status === $s ? 'selected' : '' ?>><?= ucfirst($s) ?></option>
                <?php endforeach; ?>
            </select>
            <button type="submit" class="btn btn-secondary">Filtrar</button>
        </form>
        <a href="/admin/tenants/create" class="btn btn-primary">+ Novo Tenant</a>
    </div>
    <table class="table">
        <thead>
        <tr>
            <th>#</th>
            <th>Nome</th>
            <th>E-mail</th>
            <th>Plano</th>
            <th>Agentes</th>
            <th>Status</th>
            <th>Trial até</th>
            <th>Criado</th>
            <th>Ações</th>
        </tr>
        </thead>
        <tbody>
        <?php foreach ($tenants as $t): ?>
        <tr>
            <td><?= $t['id'] ?></td>
            <td><?= htmlspecialchars($t['name']) ?></td>
            <td><?= htmlspecialchars($t['email']) ?></td>
            <td><?= htmlspecialchars($t['plan_name'] ?? '—') ?></td>
            <td><?= $t['agent_count'] ?></td>
            <td><span class="badge badge-<?= $t['status'] ?>"><?= $t['status'] ?></span></td>
            <td><?= $t['trial_ends_at'] ? date('d/m/Y', strtotime($t['trial_ends_at'])) : '—' ?></td>
            <td><?= date('d/m/Y', strtotime($t['created_at'])) ?></td>
            <td>
                <a href="/admin/tenants/<?= $t['id'] ?>/edit" class="btn btn-sm">Editar</a>
                <form method="POST" action="/admin/tenants/<?= $t['id'] ?>/delete"
                      style="display:inline"
                      onsubmit="return confirm('Remover tenant?')">
                    <?= $csrf ?>
                    <button class="btn btn-sm btn-danger">Excluir</button>
                </form>
            </td>
        </tr>
        <?php endforeach; ?>
        <?php if (empty($tenants)): ?>
        <tr><td colspan="9" class="text-center text-muted">Nenhum tenant encontrado.</td></tr>
        <?php endif; ?>
        </tbody>
    </table>
</div>

<?php require APP_ROOT . '/app/Views/layouts/admin_end.php'; ?>
