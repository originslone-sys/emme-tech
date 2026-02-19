<?php
$pageTitle = 'Conversa #' . $thread['id'];
require APP_ROOT . '/app/Views/layouts/app.php';
?>

<div class="thread-header">
    <div>
        <h2><?= htmlspecialchars($thread['contact_name'] ?: $thread['contact_phone']) ?></h2>
        <p class="text-muted">
            <?= htmlspecialchars($thread['contact_phone']) ?> |
            Agente: <?= htmlspecialchars($thread['agent_name']) ?> |
            Status: <span class="badge badge-<?= $thread['status'] ?>"><?= $thread['status'] ?></span>
            <?php if ($thread['opt_out']): ?>
            | <span class="badge badge-danger">Opt-out</span>
            <?php endif; ?>
            <?php if ($thread['handoff']): ?>
            | <span class="badge badge-warning">Handoff</span>
            <?php endif; ?>
        </p>
    </div>
    <a href="/app/threads" class="btn">← Voltar</a>
</div>

<div class="thread-messages">
    <?php if (empty($messages)): ?>
    <p class="text-center text-muted">Nenhuma mensagem.</p>
    <?php endif; ?>

    <?php foreach ($messages as $m): ?>
    <div class="message message-<?= $m['direction'] ?>">
        <div class="message-bubble">
            <div class="message-content"><?= nl2br(htmlspecialchars($m['content'])) ?></div>
            <div class="message-meta">
                <?= date('d/m H:i', strtotime($m['created_at'])) ?>
                | <?= $m['direction'] === 'inbound' ? 'Recebida' : 'Enviada' ?>
                | <span class="badge badge-<?= $m['status'] ?>"><?= $m['status'] ?></span>
                <?php if ($m['message_type'] !== 'text'): ?>
                | [<?= $m['message_type'] ?>]
                <?php endif; ?>
            </div>
        </div>
    </div>
    <?php endforeach; ?>
</div>

<?php require APP_ROOT . '/app/Views/layouts/app_end.php'; ?>
