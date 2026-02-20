<?php
$pageTitle = 'Agentes';
require APP_ROOT . '/app/Views/layouts/app.php';
?>

<div class="card">
    <div class="card-header">
        <h3>Seus Agentes</h3>
        <a href="/app/agents/create" class="btn btn-primary">+ Novo Agente</a>
    </div>
    <?php if (empty($agents)): ?>
    <div class="empty-state">
        <p>Nenhum agente ainda.</p>
        <a href="/app/agents/create" class="btn btn-primary">Criar primeiro agente</a>
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
            <td>
                <?php if ($a['whatsapp_phone_number_id'] || $a['evo_instance_name']): ?>
                    ✅ <?= $a['whatsapp_mode'] === 'whatsapp_web' ? 'Web' : 'Cloud API' ?>
                <?php else: ?>
                    ⚠️ Não configurado
                <?php endif; ?>
            </td>
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

<?php require APP_ROOT . '/app/Views/layouts/app_end.php'; ?>
