<?php
$pageTitle = 'Conversas';
require APP_ROOT . '/app/Views/layouts/app.php';
$pages = (int)ceil($total / $perPage);
?>

<div class="card">
    <div class="card-header">
        <form method="GET" class="filter-form">
            <select name="agent_id">
                <option value="">Todos agentes</option>
                <?php foreach ($agents as $a): ?>
                <option value="<?= $a['id'] ?>" <?= $agentId == $a['id'] ? 'selected' : '' ?>>
                    <?= htmlspecialchars($a['name']) ?>
                </option>
                <?php endforeach; ?>
            </select>
            <input type="text" name="contact" value="<?= htmlspecialchars($contactQ) ?>" placeholder="Buscar contato (nome/tel)...">
            <select name="status">
                <option value="">Todos status</option>
                <?php foreach (['open','handoff','closed'] as $s): ?>
                <option value="<?= $s ?>" <?= $status === $s ? 'selected' : '' ?>><?= ucfirst($s) ?></option>
                <?php endforeach; ?>
            </select>
            <input type="date" name="date_from" value="<?= htmlspecialchars($dateFrom) ?>">
            <input type="date" name="date_to" value="<?= htmlspecialchars($dateTo) ?>">
            <button type="submit" class="btn btn-secondary">Filtrar</button>
        </form>
        <span class="text-muted"><?= number_format($total) ?> conversas</span>
    </div>
    <?php if (empty($threads)): ?>
    <div class="empty-state"><p>Nenhuma conversa encontrada.</p></div>
    <?php else: ?>
    <table class="table">
        <thead>
        <tr><th>Contato</th><th>Agente</th><th>Msgs</th><th>Status</th><th>Última msg</th><th>Ação</th></tr>
        </thead>
        <tbody>
        <?php foreach ($threads as $t): ?>
        <tr>
            <td>
                <strong><?= htmlspecialchars($t['contact_name'] ?: $t['contact_phone']) ?></strong><br>
                <small class="text-muted"><?= htmlspecialchars($t['contact_phone']) ?></small>
            </td>
            <td><?= htmlspecialchars($t['agent_name'] ?? '—') ?></td>
            <td><?= $t['msg_count'] ?></td>
            <td><span class="badge badge-<?= $t['status'] ?>"><?= $t['status'] ?></span></td>
            <td>
                <?= $t['last_message_at'] ? date('d/m H:i', strtotime($t['last_message_at'])) : '—' ?>
                <?php if ($t['last_message']): ?>
                <br><small class="text-muted"><?= htmlspecialchars(mb_substr($t['last_message'], 0, 60)) ?>...</small>
                <?php endif; ?>
            </td>
            <td><a href="/app/thread?id=<?= $t['id'] ?>" class="btn btn-sm">Ver</a></td>
        </tr>
        <?php endforeach; ?>
        </tbody>
    </table>
    <?php if ($pages > 1): ?>
    <div class="pagination">
        <?php for ($i = 1; $i <= $pages; $i++): ?>
        <a href="?page=<?= $i ?>&agent_id=<?= urlencode($agentId) ?>&contact=<?= urlencode($contactQ) ?>&status=<?= urlencode($status) ?>"
           class="page-link <?= $i === $page ? 'active' : '' ?>"><?= $i ?></a>
        <?php endfor; ?>
    </div>
    <?php endif; ?>
    <?php endif; ?>
</div>

<?php require APP_ROOT . '/app/Views/layouts/app_end.php'; ?>
