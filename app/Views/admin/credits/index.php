<?php
$pageTitle = 'Pacotes de Créditos';
require APP_ROOT . '/app/Views/layouts/admin.php';
?>

<div class="card">
    <div class="card-header">
        <h3>Pacotes de Créditos</h3>
        <a href="/admin/credits/create" class="btn btn-primary">+ Novo Pacote</a>
    </div>
    <table class="table">
        <thead>
        <tr>
            <th>#</th>
            <th>Nome</th>
            <th>Créditos</th>
            <th>Preço</th>
            <th>Destaque</th>
            <th>Ativo</th>
            <th>Ordem</th>
            <th>Ações</th>
        </tr>
        </thead>
        <tbody>
        <?php foreach ($packages as $p): ?>
        <tr>
            <td><?= $p['id'] ?></td>
            <td><?= htmlspecialchars($p['name']) ?></td>
            <td><?= number_format((int)$p['credits']) ?></td>
            <td>R$ <?= number_format((float)$p['price'], 2, ',', '.') ?></td>
            <td><?= $p['is_featured'] ? '⭐ Sim' : '—' ?></td>
            <td><?= $p['is_active'] ? '✅' : '❌' ?></td>
            <td><?= $p['sort_order'] ?></td>
            <td>
                <a href="/admin/credits/<?= $p['id'] ?>/edit" class="btn btn-sm">Editar</a>
                <form method="POST" action="/admin/credits/<?= $p['id'] ?>/delete" style="display:inline"
                      onsubmit="return confirm('Excluir pacote?')">
                    <?= $csrf ?>
                    <button class="btn btn-sm btn-danger">Excluir</button>
                </form>
            </td>
        </tr>
        <?php endforeach; ?>
        <?php if (empty($packages)): ?>
        <tr><td colspan="8" class="text-center text-muted">Nenhum pacote cadastrado.</td></tr>
        <?php endif; ?>
        </tbody>
    </table>
</div>

<?php require APP_ROOT . '/app/Views/layouts/admin_end.php'; ?>
