<?php
$pageTitle = 'Personas';
require APP_ROOT . '/app/Views/layouts/app.php';
?>

<div class="card">
    <div class="card-header">
        <h3>Personas</h3>
        <a href="/app/personas/create" class="btn btn-primary">+ Nova Persona</a>
    </div>
    <?php if (empty($personas)): ?>
    <div class="empty-state">
        <p>Nenhuma persona criada ainda.</p>
        <a href="/app/personas/create" class="btn btn-primary">Criar persona</a>
    </div>
    <?php else: ?>
    <table class="table">
        <thead><tr><th>Nome</th><th>Tom</th><th>Idioma</th><th>Agente vinculado</th><th>Ações</th></tr></thead>
        <tbody>
        <?php foreach ($personas as $p): ?>
        <tr>
            <td><?= htmlspecialchars($p['name']) ?></td>
            <td><?= htmlspecialchars($p['tone'] ?? '—') ?></td>
            <td><?= htmlspecialchars($p['language'] ?? '—') ?></td>
            <td><?= htmlspecialchars($p['agent_name'] ?? 'Global') ?></td>
            <td>
                <a href="/app/personas/<?= $p['id'] ?>/edit" class="btn btn-sm">Editar</a>
                <form method="POST" action="/app/personas/<?= $p['id'] ?>/delete"
                      style="display:inline" onsubmit="return confirm('Remover persona?')">
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
