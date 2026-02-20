<?php
$pageTitle = 'Configurações Globais';
require APP_ROOT . '/app/Views/layouts/admin.php';
?>

<div class="card">
    <div class="card-header">
        <h3>Configurações Globais da Plataforma</h3>
    </div>
    <div class="card-body">
        <form method="POST" action="/admin/settings">
            <?= $csrf ?>

            <h4>OpenRouter (IA)</h4>
            <div class="form-row">
                <div class="form-group">
                    <label>API Key</label>
                    <input type="password" name="openrouter_api_key"
                           placeholder="<?= $settings['openrouter_api_key'] ? '(configurado — deixe vazio para manter)' : 'sk-or-v1-...' ?>">
                    <?php if ($settings['openrouter_api_key']): ?>
                    <small class="text-muted">Configurado: <code><?= htmlspecialchars(substr($settings['openrouter_api_key'], 0, 12)) ?>...</code></small>
                    <?php endif; ?>
                </div>
                <div class="form-group">
                    <label>API URL</label>
                    <input type="text" name="openrouter_api_url"
                           value="<?= htmlspecialchars($settings['openrouter_api_url'] ?? 'https://openrouter.ai/api/v1') ?>">
                </div>
            </div>

            <h4>Mercado Pago</h4>
            <div class="form-row">
                <div class="form-group">
                    <label>Access Token (privado)</label>
                    <input type="password" name="mp_access_token"
                           placeholder="<?= $settings['mp_access_token'] ? '(configurado — deixe vazio para manter)' : 'APP_USR-...' ?>">
                    <?php if ($settings['mp_access_token']): ?>
                    <small class="text-muted">Configurado</small>
                    <?php endif; ?>
                </div>
                <div class="form-group">
                    <label>Public Key</label>
                    <input type="text" name="mp_public_key"
                           value="<?= htmlspecialchars($settings['mp_public_key'] ?? '') ?>"
                           placeholder="APP_USR-...">
                </div>
            </div>
            <div class="form-group" style="max-width:480px">
                <label>Webhook Secret (para validar assinatura IPN)</label>
                <input type="password" name="mp_webhook_secret"
                       placeholder="<?= $settings['mp_webhook_secret'] ? '(configurado — deixe vazio para manter)' : 'Opcional' ?>">
            </div>

            <h4>Evolution API (WhatsApp Web)</h4>
            <div class="form-row">
                <div class="form-group">
                    <label>URL da API</label>
                    <input type="text" name="evo_api_url"
                           value="<?= htmlspecialchars($settings['evo_api_url'] ?? '') ?>"
                           placeholder="https://evolution.seudominio.com">
                </div>
                <div class="form-group">
                    <label>API Key</label>
                    <input type="password" name="evo_api_key"
                           placeholder="<?= $settings['evo_api_key'] ? '(configurado — deixe vazio para manter)' : 'Chave de autenticação' ?>">
                    <?php if ($settings['evo_api_key']): ?>
                    <small class="text-muted">Configurado</small>
                    <?php endif; ?>
                </div>
            </div>

            <div class="form-actions">
                <button type="submit" class="btn btn-primary">Salvar Configurações</button>
            </div>
        </form>
    </div>
</div>

<?php require APP_ROOT . '/app/Views/layouts/admin_end.php'; ?>
