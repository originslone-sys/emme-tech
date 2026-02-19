<?php
$pageTitle = 'Agentes';
require APP_ROOT . '/app/Views/layouts/app.php';
$canCreate = \App\Core\Auth::canCreateAgent();
?>

<div class="card">
    <div class="card-header">
        <h3>Seus Agentes</h3>
        <?php if ($canCreate): ?>
        <a href="/app/agents/create" class="btn btn-primary">+ Novo Agente</a>
        <?php else: ?>
        <span class="badge badge-warning">Limite do plano atingido</span>
        <?php endif; ?>
    </div>
    <?php if (empty($agents)): ?>
    <div class="empty-state">
        <p>Nenhum agente ainda.</p>
        <?php if ($canCreate): ?>
        <a href="/app/agents/create" class="btn btn-primary">Criar primeiro agente</a>
        <?php endif; ?>
    </div>
    <?php else: ?>
    <table class="table">
        <thead>
        <tr><th>Nome</th><th>Modelo</th><th>Persona</th><th>Status</th><th>WhatsApp</th><th>Ações</th></tr>
        </thead>
        <tbody>
        <?php foreach ($agents as $a): ?>
        <tr>
            <td><?= htmlspecialchars($a['name']) ?></td>
            <td><?= htmlspecialchars($a['model_name'] ?? '—') ?></td>
            <td><?= htmlspecialchars($a['persona_name'] ?? '—') ?></td>
            <td><span class="badge badge-<?= $a['status'] ?>"><?= $a['status'] ?></span></td>
            <td><?= $a['whatsapp_phone_number_id'] ? '✅' : '⚠️ Não configurado' ?></td>
            <td>
                <a href="/app/agents/<?= $a['id'] ?>/edit" class="btn btn-sm">Editar</a>
                <form method="POST" action="/app/agents/<?= $a['id'] ?>/delete"
                      style="display:inline" onsubmit="return confirm('Remover agente?')">
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

<?php if ($plan): ?>
<p class="text-muted mt-2">
    Agentes: <?= count($agents) ?> / <?= $plan['max_agents'] ?> permitidos no plano <strong><?= htmlspecialchars($plan['name']) ?></strong>.
</p>
<?php endif; ?>

<?php require APP_ROOT . '/app/Views/layouts/app_end.php'; ?>
