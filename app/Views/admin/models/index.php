<?php
$pageTitle = 'Catálogo de Modelos de IA';
require APP_ROOT . '/app/Views/layouts/admin.php';
?>

<div class="card">
    <div class="card-header">
        <h3>Modelos disponíveis no OpenRouter</h3>
        <a href="/admin/models/create" class="btn btn-primary">+ Adicionar Modelo</a>
    </div>
    <table class="table">
        <thead>
        <tr>
            <th>#</th><th>Provedor</th><th>Model ID</th><th>Nome</th>
            <th>Contexto</th><th>Temp. Padrão</th><th>Status</th><th>Ações</th>
        </tr>
        </thead>
        <tbody>
        <?php foreach ($models as $m): ?>
        <tr class="<?= !$m['is_active'] ? 'row-disabled' : '' ?>">
            <td><?= $m['id'] ?></td>
            <td><?= htmlspecialchars($m['provider']) ?></td>
            <td><code><?= htmlspecialchars($m['model_id']) ?></code></td>
            <td><?= htmlspecialchars($m['display_name']) ?></td>
            <td><?= number_format($m['context_length']) ?></td>
            <td><?= $m['default_temperature'] ?></td>
            <td><span class="badge badge-<?= $m['is_active'] ? 'active' : 'inactive' ?>">
                <?= $m['is_active'] ? 'Ativo' : 'Inativo' ?></span></td>
            <td>
                <a href="/admin/models/<?= $m['id'] ?>/edit" class="btn btn-sm">Editar</a>
                <form method="POST" action="/admin/models/<?= $m['id'] ?>/delete"
                      style="display:inline" onsubmit="return confirm('Desativar modelo?')">
                    <?= $csrf ?>
                    <button class="btn btn-sm btn-danger">Desativar</button>
                </form>
            </td>
        </tr>
        <?php endforeach; ?>
        </tbody>
    </table>
</div>

<?php require APP_ROOT . '/app/Views/layouts/admin_end.php'; ?>
