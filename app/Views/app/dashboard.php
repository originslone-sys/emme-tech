<?php
$pageTitle = 'Visão Geral';
require APP_ROOT . '/app/Views/layouts/app.php';
$checklistTotal   = count($checklist);
$checklistDone    = count(array_filter($checklist));
$checklistPercent = $checklistTotal ? round($checklistDone / $checklistTotal * 100) : 0;
?>

<!-- Onboarding -->
<?php if ($checklistPercent < 100): ?>
<div class="card card-onboarding mb-4">
    <div class="card-body">
        <h3>🚀 Primeiros passos</h3>
        <div class="progress-bar-wrap">
            <div class="progress-bar" style="width:<?= $checklistPercent ?>%"></div>
        </div>
        <p><?= $checklistPercent ?>% concluído</p>
        <ul class="checklist">
            <li class="<?= $checklist['whatsapp'] ? 'done' : '' ?>">
                <?= $checklist['whatsapp'] ? '✅' : '⬜' ?>
                <a href="/app/agents">Conectar WhatsApp no Agente</a>
            </li>
            <li class="<?= $checklist['persona'] ? 'done' : '' ?>">
                <?= $checklist['persona'] ? '✅' : '⬜' ?>
                <a href="/app/personas">Definir uma Persona</a>
            </li>
            <li class="<?= $checklist['docs'] ? 'done' : '' ?>">
                <?= $checklist['docs'] ? '✅' : '⬜' ?>
                <a href="/app/docs">Subir um documento de memória</a>
            </li>
            <li class="<?= $checklist['message'] ? 'done' : '' ?>">
                <?= $checklist['message'] ? '✅' : '⬜' ?>
                Receber a primeira conversa hoje
            </li>
        </ul>
    </div>
</div>
<?php endif; ?>

<!-- Stats -->
<div class="stats-grid">
    <div class="stat-card">
        <div class="stat-value"><?= $stats['agents'] ?></div>
        <div class="stat-label">Agentes</div>
    </div>
    <div class="stat-card stat-success">
        <div class="stat-value"><?= $stats['contacts'] ?></div>
        <div class="stat-label">Contatos</div>
    </div>
    <div class="stat-card">
        <div class="stat-value"><?= $stats['messages_today'] ?></div>
        <div class="stat-label">Mensagens hoje</div>
    </div>
    <div class="stat-card">
        <div class="stat-value"><?= $stats['threads_open'] ?></div>
        <div class="stat-label">Conversas abertas</div>
    </div>
</div>

<!-- Credits -->
<div class="card mt-4">
    <div class="card-body" style="display:flex;align-items:center;justify-content:space-between;gap:16px">
        <div>
            <div style="font-size:2rem;font-weight:700;color:var(--primary)"><?= number_format($credits) ?></div>
            <div class="text-muted">créditos disponíveis · 1 crédito = 1 resposta do agente</div>
        </div>
        <?php if ($credits < 20): ?>
        <div>
            <div class="alert alert-warning" style="margin:0">⚠️ Créditos baixos!</div>
        </div>
        <?php endif; ?>
        <a href="/app/credits" class="btn btn-primary">Comprar créditos</a>
    </div>
</div>

<!-- Agents list -->
<?php if (!empty($agents)): ?>
<div class="card mt-4">
    <div class="card-header">
        <h3>Seus Agentes</h3>
        <a href="/app/agents" class="btn btn-sm">Ver todos</a>
    </div>
    <table class="table">
        <thead>
        <tr><th>Nome</th><th>Status</th><th>WhatsApp</th><th>Conexão</th></tr>
        </thead>
        <tbody>
        <?php foreach ($agents as $a): ?>
        <tr>
            <td><?= htmlspecialchars($a['name']) ?></td>
            <td><span class="badge badge-<?= $a['status'] ?>"><?= $a['status'] ?></span></td>
            <td>
                <?php if ($a['whatsapp_phone_number_id'] || $a['evo_instance_name']): ?>
                    ✅ Configurado
                <?php else: ?>
                    <a href="/app/agents/<?= $a['id'] ?>/edit" class="text-warning">⚠️ Configurar</a>
                <?php endif; ?>
            </td>
            <td>
                <?php if ($a['whatsapp_mode'] === 'whatsapp_web'): ?>
                    <span class="badge badge-info">WhatsApp Web</span>
                <?php else: ?>
                    <span class="badge badge-secondary">Cloud API</span>
                <?php endif; ?>
            </td>
        </tr>
        <?php endforeach; ?>
        </tbody>
    </table>
</div>
<?php endif; ?>

<?php require APP_ROOT . '/app/Views/layouts/app_end.php'; ?>
