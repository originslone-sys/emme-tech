<?php
$pageTitle = 'Automações / Crons';
require APP_ROOT . '/app/Views/layouts/app.php';
$canCreate = \App\Core\Auth::canCreateCron();
?>

<div class="card mb-4">
    <div class="card-header">
        <h3>Automações configuradas</h3>
        <?php if ($canCreate): ?>
        <a href="/app/crons/create" class="btn btn-primary">+ Nova Automação</a>
        <?php else: ?>
        <span class="text-muted">Limite do plano atingido</span>
        <?php endif; ?>
    </div>
    <?php if (empty($crons)): ?>
    <div class="empty-state">
        <p>Nenhuma automação. Configure envios automáticos por horário.</p>
        <?php if ($canCreate): ?>
        <a href="/app/crons/create" class="btn btn-primary">Criar automação</a>
        <?php endif; ?>
    </div>
    <?php else: ?>
    <table class="table">
        <thead><tr><th>Nome</th><th>Agente</th><th>Schedule</th><th>Tipo</th><th>Template</th><th>Ativo</th><th>Último run</th><th>Ações</th></tr></thead>
        <tbody>
        <?php foreach ($crons as $c): ?>
        <tr>
            <td><?= htmlspecialchars($c['name']) ?></td>
            <td><?= htmlspecialchars($c['agent_name'] ?? '—') ?></td>
            <td><code><?= htmlspecialchars($c['schedule']) ?></code></td>
            <td><?= $c['action_type'] ?></td>
            <td><?= htmlspecialchars($c['template_name'] ?? '—') ?></td>
            <td><?= $c['is_active'] ? '✅' : '⏸️' ?></td>
            <td><?= $c['last_run_at'] ? date('d/m H:i', strtotime($c['last_run_at'])) : '—' ?></td>
            <td>
                <a href="/app/crons/<?= $c['id'] ?>/edit" class="btn btn-sm">Editar</a>
                <form method="POST" action="/app/crons/<?= $c['id'] ?>/delete"
                      style="display:inline" onsubmit="return confirm('Remover automação?')">
                    <?= $csrf ?>
                    <button class="btn btn-sm btn-danger">Excluir</button>
                </form>
            </td>
        </tr>
        <?php endforeach; ?>
        </tbody>
    </table>
    <?php endif; ?>
</div>

<?php if (!empty($recentRuns)): ?>
<div class="card">
    <div class="card-header"><h3>Últimas execuções</h3></div>
    <table class="table table-sm">
        <thead><tr><th>Automação</th><th>Status</th><th>Iniciado</th><th>Finalizado</th><th>Erro</th></tr></thead>
        <tbody>
        <?php foreach ($recentRuns as $r): ?>
        <tr>
            <td><?= htmlspecialchars($r['cron_name']) ?></td>
            <td><span class="badge badge-<?= $r['status'] ?>"><?= $r['status'] ?></span></td>
            <td><?= date('d/m H:i:s', strtotime($r['started_at'])) ?></td>
            <td><?= $r['finished_at'] ? date('d/m H:i:s', strtotime($r['finished_at'])) : '—' ?></td>
            <td><?= $r['error'] ? '<span title="' . htmlspecialchars($r['error']) . '">⚠️</span>' : '—' ?></td>
        </tr>
        <?php endforeach; ?>
        </tbody>
    </table>
</div>
<?php endif; ?>

<?php require APP_ROOT . '/app/Views/layouts/app_end.php'; ?>
