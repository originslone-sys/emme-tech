<?php
$pageTitle = $cron ? 'Editar Automação' : 'Nova Automação';
$action    = $cron ? "/app/crons/{$cron['id']}/update" : '/app/crons';
require APP_ROOT . '/app/Views/layouts/app.php';
?>

<div class="card">
    <div class="card-body">
        <form method="POST" action="<?= $action ?>">
            <?= $csrf ?>
            <div class="form-row">
                <div class="form-group">
                    <label>Nome *</label>
                    <input type="text" name="name" required
                           value="<?= htmlspecialchars($cron['name'] ?? '') ?>"
                           placeholder="Ex: Lembrete matinal">
                </div>
                <div class="form-group">
                    <label>Agente *</label>
                    <select name="agent_id" required>
                        <option value="">Selecione</option>
                        <?php foreach ($agents as $a): ?>
                        <option value="<?= $a['id'] ?>" <?= ($cron['agent_id'] ?? '') == $a['id'] ? 'selected' : '' ?>>
                            <?= htmlspecialchars($a['name']) ?>
                        </option>
                        <?php endforeach; ?>
                    </select>
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Schedule (cron expression)</label>
                    <input type="text" name="schedule"
                           value="<?= htmlspecialchars($cron['schedule'] ?? '0 9 * * *') ?>"
                           placeholder="0 9 * * *">
                    <small class="text-muted">
                        Exemplos: <code>0 9 * * *</code> (diário 9h) | <code>0 9 * * 1</code> (segunda 9h) |
                        <code>*/30 * * * *</code> (a cada 30min)
                    </small>
                </div>
                <div class="form-group">
                    <label>Tipo de ação</label>
                    <select name="action_type">
                        <option value="send_template" <?= ($cron['action_type'] ?? '') === 'send_template' ? 'selected' : '' ?>>Enviar Template</option>
                        <option value="send_message"  <?= ($cron['action_type'] ?? '') === 'send_message'  ? 'selected' : '' ?>>Enviar Mensagem (janela 24h)</option>
                    </select>
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Nome do Template WhatsApp</label>
                    <input type="text" name="template_name"
                           value="<?= htmlspecialchars($cron['template_name'] ?? '') ?>"
                           placeholder="hello_world">
                    <small class="text-muted">Obrigatório para <em>send_template</em>. Crie o template no Meta.</small>
                </div>
                <div class="form-group">
                    <label>Variáveis do template (JSON array ou vírgulas)</label>
                    <input type="text" name="template_vars"
                           value="<?= htmlspecialchars($cron['template_vars'] ?? '') ?>"
                           placeholder='["Valor 1","Valor 2"]'>
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Destinatário</label>
                    <select name="target_type">
                        <option value="specific_phone" <?= ($cron['target_type'] ?? '') === 'specific_phone' ? 'selected' : '' ?>>Telefone específico</option>
                        <option value="all_contacts"   <?= ($cron['target_type'] ?? '') === 'all_contacts'   ? 'selected' : '' ?>>Todos os contatos do agente</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Valor (telefone ou tag)</label>
                    <input type="text" name="target_value"
                           value="<?= htmlspecialchars($cron['target_value'] ?? '') ?>"
                           placeholder="5511999999999">
                </div>
            </div>
            <div class="form-row checkboxes">
                <label>
                    <input type="checkbox" name="is_active" value="1"
                        <?= ($cron['is_active'] ?? 1) ? 'checked' : '' ?>>
                    Automação ativa
                </label>
            </div>
            <div class="form-actions">
                <a href="/app/crons" class="btn">Cancelar</a>
                <button type="submit" class="btn btn-primary">
                    <?= $cron ? 'Salvar' : 'Criar Automação' ?>
                </button>
            </div>
        </form>
    </div>
</div>

<?php require APP_ROOT . '/app/Views/layouts/app_end.php'; ?>
