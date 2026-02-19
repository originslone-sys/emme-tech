<?php
$pageTitle = 'Documentos / Memória';
require APP_ROOT . '/app/Views/layouts/app.php';
$canUpload = \App\Core\Auth::canUploadDoc();
?>

<div class="card mb-4">
    <div class="card-header">
        <h3>Upload de Documento</h3>
    </div>
    <?php if ($canUpload): ?>
    <div class="card-body">
        <form method="POST" action="/app/docs/upload" enctype="multipart/form-data">
            <?= $csrf ?>
            <div class="form-row">
                <div class="form-group">
                    <label>Agente *</label>
                    <select name="agent_id" required>
                        <option value="">Selecione o agente</option>
                        <?php foreach ($agents as $a): ?>
                        <option value="<?= $a['id'] ?>" <?= $selected_agent == $a['id'] ? 'selected' : '' ?>>
                            <?= htmlspecialchars($a['name']) ?>
                        </option>
                        <?php endforeach; ?>
                    </select>
                </div>
                <div class="form-group">
                    <label>Arquivo (txt, md, pdf)</label>
                    <input type="file" name="document" accept=".txt,.md,.pdf" required>
                </div>
            </div>
            <button type="submit" class="btn btn-primary">Enviar e Processar</button>
        </form>
    </div>
    <?php else: ?>
    <div class="card-body">
        <p class="text-warning">Limite de documentos atingido. <a href="/app/billing">Faça upgrade</a>.</p>
    </div>
    <?php endif; ?>
</div>

<div class="card">
    <div class="card-header">
        <h3>Documentos enviados</h3>
        <form method="GET" class="filter-form">
            <select name="agent_id" onchange="this.form.submit()">
                <option value="">Todos agentes</option>
                <?php foreach ($agents as $a): ?>
                <option value="<?= $a['id'] ?>" <?= $selected_agent == $a['id'] ? 'selected' : '' ?>>
                    <?= htmlspecialchars($a['name']) ?>
                </option>
                <?php endforeach; ?>
            </select>
        </form>
    </div>
    <?php if (empty($docs)): ?>
    <div class="empty-state"><p>Nenhum documento ainda.</p></div>
    <?php else: ?>
    <table class="table">
        <thead><tr><th>Nome</th><th>Agente</th><th>Tipo</th><th>Tamanho</th><th>Chunks</th><th>Status</th><th>Ações</th></tr></thead>
        <tbody>
        <?php foreach ($docs as $d): ?>
        <tr>
            <td><?= htmlspecialchars($d['original_name']) ?></td>
            <td><?= htmlspecialchars($d['agent_name'] ?? '—') ?></td>
            <td><?= strtoupper($d['file_type']) ?></td>
            <td><?= round($d['file_size'] / 1024, 1) ?> KB</td>
            <td><?= $d['chunk_count'] ?></td>
            <td>
                <span class="badge badge-<?= $d['status'] ?>"><?= $d['status'] ?></span>
                <?php if ($d['error']): ?>
                <span title="<?= htmlspecialchars($d['error']) ?>" style="cursor:help">⚠️</span>
                <?php endif; ?>
            </td>
            <td>
                <form method="POST" action="/app/docs/<?= $d['id'] ?>/reprocess" style="display:inline">
                    <?= $csrf ?>
                    <button class="btn btn-sm">Reprocessar</button>
                </form>
                <form method="POST" action="/app/docs/<?= $d['id'] ?>/delete"
                      style="display:inline" onsubmit="return confirm('Remover documento?')">
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
    Documentos: <?= count($docs) ?> / <?= $plan['max_docs'] ?> | Storage: <?= $plan['storage_limit_mb'] ?>MB
</p>
<?php endif; ?>

<?php require APP_ROOT . '/app/Views/layouts/app_end.php'; ?>
