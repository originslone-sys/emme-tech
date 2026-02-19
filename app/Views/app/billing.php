<?php
$pageTitle = 'Assinatura';
require APP_ROOT . '/app/Views/layouts/app.php';
?>

<?php if ($flash = \App\Core\Session::flash('success')): ?>
<div class="alert alert-success"><?= htmlspecialchars($flash) ?></div>
<?php endif; ?>
<?php if (isset($_GET['success'])): ?>
<div class="alert alert-success">✅ Assinatura realizada com sucesso! Bem-vindo ao plano.</div>
<?php elseif (isset($_GET['canceled'])): ?>
<div class="alert alert-warning">Checkout cancelado. Selecione um plano para continuar.</div>
<?php endif; ?>

<!-- Current Subscription -->
<div class="card mb-4">
    <div class="card-header"><h3>Assinatura Atual</h3></div>
    <div class="card-body">
        <?php if ($subscription): ?>
        <p>Status: <span class="badge badge-<?= $subscription['status'] ?>"><?= $subscription['status'] ?></span></p>
        <p>Plano: <strong><?= htmlspecialchars($plan['name'] ?? '—') ?></strong></p>
        <?php if ($subscription['current_period_end']): ?>
        <p>Próxima cobrança: <?= date('d/m/Y', strtotime($subscription['current_period_end'])) ?></p>
        <?php endif; ?>
        <?php if ($subscription['cancel_at_period_end']): ?>
        <div class="alert alert-warning">Sua assinatura será cancelada ao fim do período.</div>
        <?php endif; ?>
        <?php if ($stripeCustomer): ?>
        <form method="POST" action="/app/billing/portal">
            <?= $csrf ?>
            <button type="submit" class="btn btn-secondary">Gerenciar assinatura (Portal Stripe)</button>
        </form>
        <?php endif; ?>
        <?php elseif ($tenant['status'] === 'trial'): ?>
        <p>Trial gratuito até <?= date('d/m/Y', strtotime($tenant['trial_ends_at'] ?? '+14 days')) ?></p>
        <p class="text-muted">Assine um plano abaixo para continuar após o trial.</p>
        <?php else: ?>
        <p class="text-muted">Nenhuma assinatura ativa.</p>
        <?php endif; ?>
    </div>
</div>

<!-- Plans -->
<h3>Planos disponíveis</h3>
<div class="plans-grid">
    <?php foreach ($plans as $p): ?>
    <div class="plan-card <?= $plan && $plan['id'] == $p['id'] ? 'plan-current' : '' ?>">
        <?php if ($plan && $plan['id'] == $p['id']): ?>
        <div class="plan-badge">Plano atual</div>
        <?php endif; ?>
        <h3><?= htmlspecialchars($p['name']) ?></h3>
        <div class="plan-price">
            R$ <?= number_format($p['price_monthly'], 2, ',', '.') ?><span>/mês</span>
        </div>
        <ul class="plan-features">
            <li><?= $p['max_agents'] ?> agente<?= $p['max_agents'] > 1 ? 's' : '' ?></li>
            <li><?= $p['max_messages_per_month'] > 0 ? number_format($p['max_messages_per_month']) . ' msgs/mês' : 'Mensagens ilimitadas' ?></li>
            <li><?= $p['feature_docs']  ? '✅ Documentos/RAG' : '❌ Sem documentos' ?></li>
            <li><?= $p['feature_crons'] ? '✅ Automações (' . $p['max_crons'] . ')' : '❌ Sem automações' ?></li>
        </ul>
        <?php if ($p['stripe_price_monthly_id'] && (!$plan || $plan['id'] != $p['id'])): ?>
        <form method="POST" action="/app/billing/checkout">
            <?= $csrf ?>
            <input type="hidden" name="price_id"  value="<?= htmlspecialchars($p['stripe_price_monthly_id']) ?>">
            <input type="hidden" name="interval"  value="monthly">
            <button type="submit" class="btn btn-primary btn-block">Assinar</button>
        </form>
        <?php elseif (!$p['stripe_price_monthly_id']): ?>
        <p class="text-muted text-sm">Contate o suporte para assinar este plano.</p>
        <?php else: ?>
        <button class="btn btn-secondary btn-block" disabled>Plano atual</button>
        <?php endif; ?>
    </div>
    <?php endforeach; ?>
</div>

<?php require APP_ROOT . '/app/Views/layouts/app_end.php'; ?>
