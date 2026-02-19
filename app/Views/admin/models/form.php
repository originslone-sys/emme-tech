<?php
$pageTitle = $model ? 'Editar Modelo' : 'Novo Modelo';
$action    = $model ? "/admin/models/{$model['id']}/update" : '/admin/models';
require APP_ROOT . '/app/Views/layouts/admin.php';
?>

<div class="card">
    <div class="card-body">
        <form method="POST" action="<?= $action ?>">
            <?= $csrf ?>
            <div class="form-row">
                <div class="form-group">
                    <label>Provedor</label>
                    <select name="provider">
                        <option value="openrouter" <?= ($model['provider'] ?? 'openrouter') === 'openrouter' ? 'selected' : '' ?>>OpenRouter</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Model ID * <small>(ex: openai/gpt-4o-mini)</small></label>
                    <input type="text" name="model_id" required
                           value="<?= htmlspecialchars($model['model_id'] ?? '') ?>"
                           placeholder="openai/gpt-4o-mini">
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Nome de Exibição *</label>
                    <input type="text" name="display_name" required
                           value="<?= htmlspecialchars($model['display_name'] ?? '') ?>">
                </div>
                <div class="form-group">
                    <label>Contexto (tokens)</label>
                    <input type="number" name="context_length"
                           value="<?= $model['context_length'] ?? 4096 ?>">
                </div>
            </div>
            <div class="form-group">
                <label>Descrição</label>
                <textarea name="description" rows="2"><?= htmlspecialchars($model['description'] ?? '') ?></textarea>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Temperature padrão (0-2)</label>
                    <input type="number" step="0.05" min="0" max="2" name="default_temperature"
                           value="<?= $model['default_temperature'] ?? 0.7 ?>">
                </div>
                <div class="form-group">
                    <label>Max Tokens padrão</label>
                    <input type="number" name="default_max_tokens"
                           value="<?= $model['default_max_tokens'] ?? 1024 ?>">
                </div>
                <div class="form-group">
                    <label>Ordem</label>
                    <input type="number" name="sort_order" value="<?= $model['sort_order'] ?? 0 ?>">
                </div>
            </div>
            <div class="form-row checkboxes">
                <label><input type="checkbox" name="supports_functions" value="1"
                    <?= ($model['supports_functions'] ?? 0) ? 'checked' : '' ?>> Suporta Functions</label>
                <label><input type="checkbox" name="is_active" value="1"
                    <?= ($model['is_active'] ?? 1) ? 'checked' : '' ?>> Ativo / disponível para clientes</label>
            </div>
            <div class="form-actions">
                <a href="/admin/models" class="btn">Cancelar</a>
                <button type="submit" class="btn btn-primary">
                    <?= $model ? 'Salvar' : 'Adicionar' ?>
                </button>
            </div>
        </form>
    </div>
</div>

<?php require APP_ROOT . '/app/Views/layouts/admin_end.php'; ?>
