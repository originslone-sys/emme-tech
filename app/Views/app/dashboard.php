<?php
$pageTitle = 'Visão Geral';
require APP_ROOT . '/app/Views/layouts/app.php';
$checklistTotal    = count($checklist);
$checklistDone     = count(array_filter($checklist));
$checklistPercent  = $checklistTotal ? round($checklistDone / $checklistTotal * 100) : 0;
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
                <a href="/app/agents">Configurar WhatsApp no Agente</a>
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

<!-- Plan + Subscription -->
<div class="grid-2 mt-4">
    <div class="card">
        <div class="card-header"><h3>Plano atual</h3></div>
        <div class="card-body">
            <?php if ($plan): ?>
            <p><strong><?= htmlspecialchars($plan['name']) ?></strong></p>
            <ul class="plan-limits">
                <li>Agentes: <?= $stats['agents'] ?> / <?= $plan['max_agents'] ?></li>
                <li>Docs: <?= $plan['feature_docs'] ? 'Habilitado' : 'Não disponível' ?></li>
                <li>Automações: <?= $plan['feature_crons'] ? 'Habilitado' : 'Não disponível' ?></li>
            </ul>
            <?php else: ?>
            <p class="text-muted">Sem plano ativo. <a href="/app/billing">Assine agora</a>.</p>
            <?php endif; ?>
        </div>
    </div>
    <div class="card">
        <div class="card-header"><h3>Assinatura</h3></div>
        <div class="card-body">
            <?php if ($tenant['status'] === 'trial'): ?>
            <p>Trial gratuito</p>
            <p class="text-muted">Expira em: <?= $tenant['trial_ends_at'] ? date('d/m/Y', strtotime($tenant['trial_ends_at'])) : '—' ?></p>
            <a href="/app/billing" class="btn btn-primary btn-sm">Ver planos</a>
            <?php elseif ($tenant['status'] === 'active'): ?>
            <p><span class="badge badge-active">Ativo</span></p>
            <a href="/app/billing" class="btn btn-secondary btn-sm">Gerenciar assinatura</a>
            <?php elseif ($tenant['status'] === 'past_due'): ?>
            <p><span class="badge badge-past_due">Pagamento pendente</span></p>
            <a href="/app/billing" class="btn btn-danger btn-sm">Regularizar</a>
            <?php else: ?>
            <p><span class="badge badge-inactive"><?= ucfirst($tenant['status']) ?></span></p>
            <a href="/app/billing" class="btn btn-primary btn-sm">Ver planos</a>
            <?php endif; ?>
        </div>
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
        <thead><tr><th>Nome</th><th>Status</th><th>WhatsApp</th></tr></thead>
        <tbody>
        <?php foreach ($agents as $a): ?>
        <tr>
            <td><?= htmlspecialchars($a['name']) ?></td>
            <td><span class="badge badge-<?= $a['status'] ?>"><?= $a['status'] ?></span></td>
            <td><?= $a['whatsapp_phone_number_id'] ? '✅ Configurado' : '⚠️ Não configurado' ?></td>
        </tr>
        <?php endforeach; ?>
        </tbody>
    </table>
</div>
<?php endif; ?>

<?php require APP_ROOT . '/app/Views/layouts/app_end.php'; ?>
