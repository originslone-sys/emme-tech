<?php
$pageTitle = 'Créditos';
require APP_ROOT . '/app/Views/layouts/app.php';
?>

<?php if (isset($_GET['success'])): ?>
<div class="alert alert-success">✅ Pagamento aprovado! Seus créditos foram adicionados.</div>
<?php elseif (isset($_GET['pending'])): ?>
<div class="alert alert-warning">⏳ Pagamento pendente. Seus créditos serão adicionados assim que o pagamento for confirmado.</div>
<?php elseif (isset($_GET['failure'])): ?>
<div class="alert alert-error">❌ Pagamento não aprovado. Tente novamente.</div>
<?php endif; ?>

<!-- Balance -->
<div class="card mb-4">
    <div class="card-body" style="text-align:center;padding:32px">
        <div style="font-size:3rem;font-weight:700;color:var(--primary)"><?= number_format($credits) ?></div>
        <div style="font-size:1.1rem;color:var(--text-muted);margin-top:4px">créditos disponíveis</div>
        <p class="text-muted text-sm mt-2">1 crédito = 1 resposta do agente</p>
        <a href="/app/credits/history" class="btn btn-secondary btn-sm mt-2">Ver histórico completo</a>
    </div>
</div>

<!-- Packages -->
<h3>Comprar Créditos</h3>
<div class="plans-grid">
    <?php foreach ($packages as $p): ?>
    <div class="plan-card <?= $p['is_featured'] ? 'plan-featured' : '' ?>">
        <?php if ($p['is_featured']): ?>
        <div class="plan-badge">Mais popular</div>
        <?php endif; ?>
        <h3><?= htmlspecialchars($p['name']) ?></h3>
        <div class="plan-price">
            R$ <?= number_format((float)$p['price'], 2, ',', '.') ?>
        </div>
        <div style="font-size:1.5rem;font-weight:600;color:var(--primary);margin:8px 0">
            <?= number_format((int)$p['credits']) ?> créditos
        </div>
        <?php if ($p['description']): ?>
        <p class="text-muted text-sm"><?= htmlspecialchars($p['description']) ?></p>
        <?php endif; ?>
        <form method="POST" action="/app/credits/buy">
            <?= $csrf ?>
            <input type="hidden" name="package_id" value="<?= $p['id'] ?>">
            <button type="submit" class="btn btn-primary btn-block">Comprar</button>
        </form>
    </div>
    <?php endforeach; ?>
    <?php if (empty($packages)): ?>
    <p class="text-muted">Nenhum pacote disponível no momento. Entre em contato com o suporte.</p>
    <?php endif; ?>
</div>

<!-- Recent Transactions -->
<?php if (!empty($transactions)): ?>
<div class="card mt-4">
    <div class="card-header">
        <h3>Transações Recentes</h3>
        <a href="/app/credits/history" class="btn btn-sm">Ver todas</a>
    </div>
    <table class="table">
        <thead>
        <tr><th>Data</th><th>Tipo</th><th>Créditos</th><th>Descrição</th></tr>
        </thead>
        <tbody>
        <?php foreach ($transactions as $tx): ?>
        <tr>
            <td><?= date('d/m/Y H:i', strtotime($tx['created_at'])) ?></td>
            <td><span class="badge badge-<?= $tx['type'] === 'usage' ? 'secondary' : ($tx['type'] === 'purchase' ? 'success' : 'info') ?>"><?= $tx['type'] ?></span></td>
            <td class="<?= $tx['amount'] < 0 ? 'text-danger' : 'text-success' ?>">
                <?= $tx['amount'] > 0 ? '+' : '' ?><?= $tx['amount'] ?>
            </td>
            <td><?= htmlspecialchars($tx['description'] ?? '') ?></td>
        </tr>
        <?php endforeach; ?>
        </tbody>
    </table>
</div>
<?php endif; ?>

<?php require APP_ROOT . '/app/Views/layouts/app_end.php'; ?>
