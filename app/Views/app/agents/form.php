<?php
$pageTitle = $agent ? 'Editar Agente' : 'Novo Agente';
$action    = $agent ? "/app/agents/{$agent['id']}/update" : '/app/agents';
require APP_ROOT . '/app/Views/layouts/app.php';
?>

<div class="card">
    <div class="card-body">
        <form method="POST" action="<?= $action ?>">
            <?= $csrf ?>

            <div class="form-row">
                <div class="form-group">
                    <label>Nome do Agente *</label>
                    <input type="text" name="name" required
                           value="<?= htmlspecialchars($agent['name'] ?? '') ?>"
                           placeholder="Ex: Suporte TechBot">
                </div>
                <div class="form-group">
                    <label>Status</label>
                    <select name="status">
                        <?php foreach (['inactive','active','paused'] as $s): ?>
                        <option value="<?= $s ?>" <?= ($agent['status'] ?? 'inactive') === $s ? 'selected' : '' ?>>
                            <?= ucfirst($s) ?>
                        </option>
                        <?php endforeach; ?>
                    </select>
                </div>
            </div>

            <div class="form-row">
                <div class="form-group">
                    <label>Modelo de IA</label>
                    <select name="model_catalog_id">
                        <option value="">Selecione um modelo</option>
                        <?php foreach ($models as $m): ?>
                        <option value="<?= $m['id'] ?>"
                            <?= ($agent['model_catalog_id'] ?? '') == $m['id'] ? 'selected' : '' ?>>
                            <?= htmlspecialchars($m['display_name']) ?>
                            (<?= htmlspecialchars($m['model_id']) ?>)
                        </option>
                        <?php endforeach; ?>
                    </select>
                </div>
                <div class="form-group">
                    <label>Persona</label>
                    <select name="persona_id">
                        <option value="">Sem persona</option>
                        <?php foreach ($personas as $p): ?>
                        <option value="<?= $p['id'] ?>"
                            <?= ($agent['persona_id'] ?? '') == $p['id'] ? 'selected' : '' ?>>
                            <?= htmlspecialchars($p['name']) ?>
                        </option>
                        <?php endforeach; ?>
                    </select>
                </div>
            </div>

            <div class="form-row">
                <div class="form-group">
                    <label>Temperature (0-2)</label>
                    <input type="number" step="0.05" min="0" max="2" name="temperature"
                           value="<?= $agent['temperature'] ?? 0.7 ?>">
                </div>
                <div class="form-group">
                    <label>Max Tokens</label>
                    <input type="number" name="max_tokens" value="<?= $agent['max_tokens'] ?? 1024 ?>">
                </div>
            </div>

            <div class="form-group">
                <label>Prompt do Sistema</label>
                <textarea name="system_prompt" rows="5"
                          placeholder="Você é um assistente de suporte da empresa..."><?= htmlspecialchars($agent['system_prompt'] ?? '') ?></textarea>
            </div>

            <h4>WhatsApp Cloud API</h4>
            <div class="form-row">
                <div class="form-group">
                    <label>Phone Number ID</label>
                    <input type="text" name="whatsapp_phone_number_id"
                           value="<?= htmlspecialchars($agent['whatsapp_phone_number_id'] ?? '') ?>"
                           placeholder="123456789012345">
                </div>
                <div class="form-group">
                    <label>WABA ID</label>
                    <input type="text" name="whatsapp_waba_id"
                           value="<?= htmlspecialchars($agent['whatsapp_waba_id'] ?? '') ?>">
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Access Token <?= $agent && $agent['whatsapp_access_token_encrypted'] ? '(deixe vazio para manter)' : '' ?></label>
                    <input type="password" name="whatsapp_access_token"
                           placeholder="<?= $agent && $agent['whatsapp_access_token_encrypted'] ? '(mantido)' : 'EAA...' ?>">
                </div>
                <div class="form-group">
                    <label>Verify Token (webhook)</label>
                    <input type="text" name="whatsapp_verify_token"
                           value="<?= htmlspecialchars($agent['whatsapp_verify_token'] ?? '') ?>">
                </div>
            </div>
            <p class="text-muted text-sm">
                URL do webhook: <code><?= APP_URL ?>/webhook/whatsapp</code>
            </p>

            <h4>OpenRouter (override por agente)</h4>
            <div class="form-group">
                <label>Token OpenRouter específico deste agente (opcional, sobrescreve o padrão)</label>
                <input type="password" name="openrouter_token_override"
                       placeholder="<?= $agent && $agent['openrouter_token_override_enc'] ? '(mantido)' : 'sk-or-v1-...' ?>">
            </div>

            <h4>Base de Conhecimento (RAG)</h4>
            <div class="form-row checkboxes">
                <label>
                    <input type="checkbox" name="enable_kb" value="1"
                        <?= ($agent['enable_kb'] ?? 1) ? 'checked' : '' ?>>
                    Habilitar busca em documentos
                </label>
            </div>
            <div class="form-group">
                <label>Top-K chunks (quantos trechos incluir no contexto)</label>
                <input type="number" min="1" max="10" name="kb_top_k"
                       value="<?= $agent['kb_top_k'] ?? 3 ?>">
            </div>

            <h4>Palavras-chave de controle</h4>
            <div class="form-row">
                <div class="form-group">
                    <label>Keyword de Opt-out</label>
                    <input type="text" name="optout_keyword"
                           value="<?= htmlspecialchars($agent['optout_keyword'] ?? 'sair') ?>">
                </div>
                <div class="form-group">
                    <label>Keyword de Handoff (atendimento humano)</label>
                    <input type="text" name="handoff_keyword"
                           value="<?= htmlspecialchars($agent['handoff_keyword'] ?? 'humano') ?>">
                </div>
            </div>

            <div class="form-actions">
                <a href="/app/agents" class="btn">Cancelar</a>
                <button type="submit" class="btn btn-primary">
                    <?= $agent ? 'Salvar Agente' : 'Criar Agente' ?>
                </button>
            </div>
        </form>
    </div>
</div>

<?php require APP_ROOT . '/app/Views/layouts/app_end.php'; ?>
