<?php
$pageTitle = 'Dashboard';
require APP_ROOT . '/app/Views/layouts/admin.php';
?>

<div class="stats-grid">
    <div class="stat-card">
        <div class="stat-value"><?= $stats['tenants'] ?></div>
        <div class="stat-label">Total Clientes</div>
    </div>
    <div class="stat-card stat-success">
        <div class="stat-value"><?= $stats['active'] ?></div>
        <div class="stat-label">Clientes Ativos</div>
    </div>
    <div class="stat-card">
        <div class="stat-value"><?= $stats['agents'] ?></div>
        <div class="stat-label">Agentes</div>
    </div>
    <div class="stat-card">
        <div class="stat-value"><?= number_format($stats['messages']) ?></div>
        <div class="stat-label">Mensagens Total</div>
    </div>
    <div class="stat-card stat-warning">
        <div class="stat-value"><?= $stats['jobs_pending'] ?></div>
        <div class="stat-label">Jobs Pendentes</div>
    </div>
    <div class="stat-card stat-danger">
        <div class="stat-value"><?= $stats['jobs_failed'] ?></div>
        <div class="stat-label">Jobs com Erro</div>
    </div>
</div>

<div class="card mt-4">
    <div class="card-header">
        <h3>Últimos Clientes</h3>
        <a href="/admin/tenants/create" class="btn btn-primary btn-sm">+ Novo Cliente</a>
    </div>
    <table class="table">
        <thead>
        <tr>
            <th>#</th>
            <th>Nome</th>
            <th>E-mail</th>
            <th>Créditos</th>
            <th>Status</th>
            <th>Criado em</th>
            <th>Ações</th>
        </tr>
        </thead>
        <tbody>
        <?php foreach ($recentTenants as $t): ?>
        <tr>
            <td><?= $t['id'] ?></td>
            <td><?= htmlspecialchars($t['name'] ?? '') ?></td>
            <td><?= htmlspecialchars($t['email']) ?></td>
            <td><?= number_format((int)$t['credits']) ?></td>
            <td><span class="badge badge-<?= $t['status'] ?>"><?= $t['status'] ?></span></td>
            <td><?= date('d/m/Y', strtotime($t['created_at'])) ?></td>
            <td><a href="/admin/tenants/<?= $t['id'] ?>/edit" class="btn btn-sm">Editar</a></td>
        </tr>
        <?php endforeach; ?>
        </tbody>
    </table>
</div>

<?php require APP_ROOT . '/app/Views/layouts/admin_end.php'; ?>
