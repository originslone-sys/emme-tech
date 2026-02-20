<?php
$pageTitle = 'Clientes';
require APP_ROOT . '/app/Views/layouts/admin.php';
?>

<div class="card">
    <div class="card-header">
        <form method="GET" class="filter-form">
            <input type="text" name="q" value="<?= htmlspecialchars($search) ?>" placeholder="Buscar nome/e-mail...">
            <select name="status">
                <option value="">Todos status</option>
                <?php foreach (['active','trial','inactive'] as $s): ?>
                <option value="<?= $s ?>" <?= $status === $s ? 'selected' : '' ?>><?= ucfirst($s) ?></option>
                <?php endforeach; ?>
            </select>
            <button type="submit" class="btn btn-secondary">Filtrar</button>
        </form>
        <a href="/admin/tenants/create" class="btn btn-primary">+ Novo Cliente</a>
    </div>
    <table class="table">
        <thead>
        <tr>
            <th>#</th>
            <th>Nome</th>
            <th>E-mail</th>
            <th>Créditos</th>
            <th>Agentes</th>
            <th>Status</th>
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
            <td><?= number_format((int)$t['credits']) ?></td>
            <td><?= $t['agent_count'] ?></td>
            <td><span class="badge badge-<?= $t['status'] ?>"><?= $t['status'] ?></span></td>
            <td><?= date('d/m/Y', strtotime($t['created_at'])) ?></td>
            <td>
                <a href="/admin/tenants/<?= $t['id'] ?>/edit" class="btn btn-sm">Editar</a>
                <form method="POST" action="/admin/tenants/<?= $t['id'] ?>/toggle" style="display:inline">
                    <?= $csrf ?>
                    <button class="btn btn-sm <?= $t['status'] === 'active' ? 'btn-warning' : 'btn-success' ?>">
                        <?= $t['status'] === 'active' ? 'Desativar' : 'Ativar' ?>
                    </button>
                </form>
                <form method="POST" action="/admin/tenants/<?= $t['id'] ?>/delete"
                      style="display:inline"
                      onsubmit="return confirm('Remover cliente?')">
                    <?= $csrf ?>
                    <button class="btn btn-sm btn-danger">Excluir</button>
                </form>
            </td>
        </tr>
        <?php endforeach; ?>
        <?php if (empty($tenants)): ?>
        <tr><td colspan="8" class="text-center text-muted">Nenhum cliente encontrado.</td></tr>
        <?php endif; ?>
        </tbody>
    </table>
</div>

<?php require APP_ROOT . '/app/Views/layouts/admin_end.php'; ?>
