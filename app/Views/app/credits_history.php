<?php
$pageTitle = 'Histórico de Créditos';
require APP_ROOT . '/app/Views/layouts/app.php';
?>

<div class="card">
    <div class="card-header">
        <h3>Histórico Completo de Transações</h3>
        <div>
            <span class="text-muted">Saldo atual: <strong><?= number_format($credits) ?> créditos</strong></span>
            <a href="/app/credits" class="btn btn-secondary btn-sm ml-2">Comprar créditos</a>
        </div>
    </div>
    <table class="table">
        <thead>
        <tr>
            <th>Data</th>
            <th>Tipo</th>
            <th>Créditos</th>
            <th>Descrição</th>
            <th>Referência</th>
        </tr>
        </thead>
        <tbody>
        <?php foreach ($transactions as $tx): ?>
        <tr>
            <td><?= date('d/m/Y H:i', strtotime($tx['created_at'])) ?></td>
            <td>
                <span class="badge badge-<?= match($tx['type']) {
                    'usage'    => 'secondary',
                    'purchase' => 'success',
                    'bonus'    => 'info',
                    default    => 'default'
                } ?>">
                    <?= htmlspecialchars($tx['type']) ?>
                </span>
            </td>
            <td class="<?= $tx['amount'] < 0 ? 'text-danger' : 'text-success' ?>">
                <?= $tx['amount'] > 0 ? '+' : '' ?><?= $tx['amount'] ?>
            </td>
            <td><?= htmlspecialchars($tx['description'] ?? '') ?></td>
            <td class="text-muted text-sm"><?= htmlspecialchars($tx['reference_id'] ?? '') ?></td>
        </tr>
        <?php endforeach; ?>
        <?php if (empty($transactions)): ?>
        <tr><td colspan="5" class="text-center text-muted">Nenhuma transação registrada.</td></tr>
        <?php endif; ?>
        </tbody>
    </table>
</div>

<?php require APP_ROOT . '/app/Views/layouts/app_end.php'; ?>
