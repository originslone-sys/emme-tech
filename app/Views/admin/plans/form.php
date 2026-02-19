<?php
$pageTitle = $plan ? 'Editar Plano' : 'Novo Plano';
$action    = $plan ? "/admin/plans/{$plan['id']}/update" : '/admin/plans';
require APP_ROOT . '/app/Views/layouts/admin.php';
?>

<div class="card">
    <div class="card-body">
        <form method="POST" action="<?= $action ?>">
            <?= $csrf ?>
            <div class="form-row">
                <div class="form-group">
                    <label>Nome *</label>
                    <input type="text" name="name" required value="<?= htmlspecialchars($plan['name'] ?? '') ?>">
                </div>
                <div class="form-group">
                    <label>Slug *</label>
                    <input type="text" name="slug" required value="<?= htmlspecialchars($plan['slug'] ?? '') ?>">
                </div>
            </div>
            <div class="form-group">
                <label>Descrição</label>
                <textarea name="description" rows="2"><?= htmlspecialchars($plan['description'] ?? '') ?></textarea>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Preço Mensal (R$)</label>
                    <input type="number" step="0.01" name="price_monthly"
                           value="<?= $plan['price_monthly'] ?? 0 ?>">
                </div>
                <div class="form-group">
                    <label>Preço Anual (R$)</label>
                    <input type="number" step="0.01" name="price_yearly"
                           value="<?= $plan['price_yearly'] ?? 0 ?>">
                </div>
            </div>
            <h4>Limites</h4>
            <div class="form-row">
                <div class="form-group">
                    <label>Máx. Agentes</label>
                    <input type="number" name="max_agents" value="<?= $plan['max_agents'] ?? 1 ?>">
                </div>
                <div class="form-group">
                    <label>Máx. Msgs/Mês (0=ilimitado)</label>
                    <input type="number" name="max_messages_per_month" value="<?= $plan['max_messages_per_month'] ?? 1000 ?>">
                </div>
                <div class="form-group">
                    <label>Máx. Crons</label>
                    <input type="number" name="max_crons" value="<?= $plan['max_crons'] ?? 0 ?>">
                </div>
                <div class="form-group">
                    <label>Máx. Documentos</label>
                    <input type="number" name="max_docs" value="<?= $plan['max_docs'] ?? 5 ?>">
                </div>
                <div class="form-group">
                    <label>Storage (MB)</label>
                    <input type="number" name="storage_limit_mb" value="<?= $plan['storage_limit_mb'] ?? 50 ?>">
                </div>
                <div class="form-group">
                    <label>Ordem</label>
                    <input type="number" name="sort_order" value="<?= $plan['sort_order'] ?? 0 ?>">
                </div>
            </div>
            <h4>Features</h4>
            <div class="form-row checkboxes">
                <label><input type="checkbox" name="feature_crons" value="1"
                    <?= ($plan['feature_crons'] ?? 0) ? 'checked' : '' ?>> Crons/Automações</label>
                <label><input type="checkbox" name="feature_docs" value="1"
                    <?= ($plan['feature_docs'] ?? 1) ? 'checked' : '' ?>> Documentos/RAG</label>
                <label><input type="checkbox" name="feature_api_access" value="1"
                    <?= ($plan['feature_api_access'] ?? 0) ? 'checked' : '' ?>> Acesso à API</label>
                <label><input type="checkbox" name="feature_custom_persona" value="1"
                    <?= ($plan['feature_custom_persona'] ?? 1) ? 'checked' : '' ?>> Persona customizável</label>
                <label><input type="checkbox" name="is_active" value="1"
                    <?= ($plan['is_active'] ?? 1) ? 'checked' : '' ?>> Plano ativo</label>
            </div>
            <h4>Stripe</h4>
            <div class="form-row">
                <div class="form-group">
                    <label>Stripe Product ID</label>
                    <input type="text" name="stripe_product_id"
                           value="<?= htmlspecialchars($plan['stripe_product_id'] ?? '') ?>">
                </div>
                <div class="form-group">
                    <label>Stripe Price Mensal ID</label>
                    <input type="text" name="stripe_price_monthly_id"
                           value="<?= htmlspecialchars($plan['stripe_price_monthly_id'] ?? '') ?>">
                </div>
                <div class="form-group">
                    <label>Stripe Price Anual ID</label>
                    <input type="text" name="stripe_price_yearly_id"
                           value="<?= htmlspecialchars($plan['stripe_price_yearly_id'] ?? '') ?>">
                </div>
            </div>
            <div class="form-actions">
                <a href="/admin/plans" class="btn">Cancelar</a>
                <button type="submit" class="btn btn-primary">
                    <?= $plan ? 'Salvar' : 'Criar Plano' ?>
                </button>
            </div>
        </form>
    </div>
</div>

<?php require APP_ROOT . '/app/Views/layouts/admin_end.php'; ?>
