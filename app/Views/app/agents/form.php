<?php
$pageTitle = $agent ? 'Editar Agente' : 'Novo Agente';
$action    = $agent ? "/app/agents/{$agent['id']}/update" : '/app/agents';
$waMode    = $agent['whatsapp_mode'] ?? 'cloud_api';
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

            <!-- WhatsApp Mode -->
            <h4>Modo de Conexão WhatsApp</h4>
            <div class="form-group">
                <div class="radio-group">
                    <label class="radio-label">
                        <input type="radio" name="whatsapp_mode" value="cloud_api"
                            <?= $waMode === 'cloud_api' ? 'checked' : '' ?>
                            onchange="toggleWaMode(this.value)">
                        <strong>WhatsApp Cloud API</strong> — Número verificado pelo Meta
                    </label>
                    <label class="radio-label">
                        <input type="radio" name="whatsapp_mode" value="whatsapp_web"
                            <?= $waMode === 'whatsapp_web' ? 'checked' : '' ?>
                            onchange="toggleWaMode(this.value)">
                        <strong>WhatsApp Web (QR Code)</strong> — Qualquer número via Evolution API
                    </label>
                </div>
            </div>

            <!-- Cloud API fields -->
            <div id="section-cloud-api" style="<?= $waMode !== 'cloud_api' ? 'display:none' : '' ?>">
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
            </div>

            <!-- WhatsApp Web / Evolution API fields -->
            <div id="section-whatsapp-web" style="<?= $waMode !== 'whatsapp_web' ? 'display:none' : '' ?>">
                <?php if ($agent && $agent['whatsapp_mode'] === 'whatsapp_web' && $agent['evo_instance_name']): ?>
                <div class="alert alert-info">
                    Instância: <strong><?= htmlspecialchars($agent['evo_instance_name']) ?></strong>
                    <?php if (isset($evoState)): ?>
                    — Estado: <span class="badge badge-<?= $evoState === 'open' ? 'success' : 'warning' ?>">
                        <?= htmlspecialchars($evoState) ?>
                    </span>
                    <?php endif; ?>
                </div>

                <?php if (isset($evoState) && $evoState !== 'open'): ?>
                <div class="qrcode-section mb-3">
                    <p>Escaneie o QR Code com o WhatsApp para conectar:</p>
                    <div id="qrcode-container">
                        <button type="button" class="btn btn-secondary" onclick="loadQRCode(<?= $agent['id'] ?>)">
                            Carregar QR Code
                        </button>
                        <div id="qrcode-img" style="margin-top:12px"></div>
                    </div>
                </div>
                <?php else: ?>
                <div class="alert alert-success">WhatsApp conectado!</div>
                <?php endif; ?>
                <?php else: ?>
                <p class="text-muted text-sm">
                    Após salvar o agente, você poderá escanear o QR Code para conectar o WhatsApp.
                </p>
                <?php endif; ?>
                <p class="text-muted text-sm">
                    URL do webhook Evolution: <code><?= APP_URL ?>/webhook/evolution</code>
                </p>
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

<script>
function toggleWaMode(mode) {
    document.getElementById('section-cloud-api').style.display   = mode === 'cloud_api'   ? '' : 'none';
    document.getElementById('section-whatsapp-web').style.display = mode === 'whatsapp_web' ? '' : 'none';
}

function loadQRCode(agentId) {
    const container = document.getElementById('qrcode-img');
    container.innerHTML = '<span class="text-muted">Carregando...</span>';
    fetch('/app/agents/' + agentId + '/qrcode')
        .then(r => r.json())
        .then(data => {
            if (data.qrcode) {
                container.innerHTML = '<img src="' + data.qrcode + '" style="max-width:280px;border:1px solid #ddd;padding:8px;border-radius:8px">';
            } else {
                container.innerHTML = '<span class="text-danger">' + (data.error || 'Erro ao carregar QR Code') + '</span>';
            }
        })
        .catch(() => {
            container.innerHTML = '<span class="text-danger">Falha na requisição.</span>';
        });
}
</script>

<?php require APP_ROOT . '/app/Views/layouts/app_end.php'; ?>
