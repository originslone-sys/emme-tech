<?php
$pageTitle = 'Auditoria';
require APP_ROOT . '/app/Views/layouts/admin.php';
$pages = (int)ceil($total / $perPage);
?>

<div class="card">
    <div class="card-header">
        <form method="GET" class="filter-form">
            <select name="actor_type">
                <option value="">Todos atores</option>
                <?php foreach (['admin','tenant','system'] as $at): ?>
                <option value="<?= $at ?>" <?= $actorType === $at ? 'selected' : '' ?>><?= ucfirst($at) ?></option>
                <?php endforeach; ?>
            </select>
            <input type="text" name="action" value="<?= htmlspecialchars($action) ?>" placeholder="Filtrar ação...">
            <button type="submit" class="btn btn-secondary">Filtrar</button>
        </form>
        <span class="text-muted"><?= number_format($total) ?> registros</span>
    </div>
    <table class="table table-sm">
        <thead>
        <tr>
            <th>Data</th><th>Ator</th><th>Tenant</th>
            <th>Ação</th><th>Recurso</th><th>IP</th>
        </tr>
        </thead>
        <tbody>
        <?php foreach ($logs as $l): ?>
        <tr>
            <td><?= date('d/m/Y H:i:s', strtotime($l['created_at'])) ?></td>
            <td><span class="badge badge-<?= $l['actor_type'] ?>"><?= $l['actor_type'] ?></span>
                #<?= $l['actor_id'] ?? '—' ?></td>
            <td><?= htmlspecialchars($l['tenant_name'] ?? '—') ?></td>
            <td><code><?= htmlspecialchars($l['action']) ?></code></td>
            <td><?= htmlspecialchars($l['resource_type'] ?? '') ?> <?= $l['resource_id'] ? '#' . $l['resource_id'] : '' ?></td>
            <td><?= htmlspecialchars($l['ip'] ?? '') ?></td>
        </tr>
        <?php endforeach; ?>
        </tbody>
    </table>
    <?php if ($pages > 1): ?>
    <div class="pagination">
        <?php for ($i = 1; $i <= $pages; $i++): ?>
        <a href="?page=<?= $i ?>&actor_type=<?= urlencode($actorType) ?>&action=<?= urlencode($action) ?>"
           class="page-link <?= $i === $page ? 'active' : '' ?>"><?= $i ?></a>
        <?php endfor; ?>
    </div>
    <?php endif; ?>
</div>

<?php require APP_ROOT . '/app/Views/layouts/admin_end.php'; ?>
