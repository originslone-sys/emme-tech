<?php
$pageTitle = 'Logs da Aplicação';
require APP_ROOT . '/app/Views/layouts/admin.php';
?>

<div class="card">
    <div class="card-header">
        <form method="GET" class="filter-form">
            <select name="lines">
                <?php foreach ([50,100,200,500,1000] as $n): ?>
                <option value="<?= $n ?>" <?= $lines === $n ? 'selected' : '' ?>><?= $n ?> linhas</option>
                <?php endforeach; ?>
            </select>
            <button type="submit" class="btn btn-secondary">Atualizar</button>
        </form>
        <span class="text-muted">Arquivo: <?= LOG_PATH ?></span>
    </div>
    <div class="log-viewer">
        <pre><?= htmlspecialchars($content ?: '(vazio)') ?></pre>
    </div>
</div>

<?php require APP_ROOT . '/app/Views/layouts/admin_end.php'; ?>
