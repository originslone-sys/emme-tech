<?php
$pageTitle = $package ? 'Editar Pacote' : 'Novo Pacote de Créditos';
$action    = $package ? "/admin/credits/{$package['id']}/update" : '/admin/credits';
require APP_ROOT . '/app/Views/layouts/admin.php';
?>

<div class="card">
    <div class="card-body">
        <form method="POST" action="<?= $action ?>">
            <?= $csrf ?>

            <div class="form-row">
                <div class="form-group">
                    <label>Nome *</label>
                    <input type="text" name="name" required
                           value="<?= htmlspecialchars($package['name'] ?? '') ?>"
                           placeholder="Ex: Pacote Básico">
                </div>
                <div class="form-group">
                    <label>Créditos *</label>
                    <input type="number" name="credits" min="1" required
                           value="<?= (int)($package['credits'] ?? '') ?>"
                           placeholder="Ex: 100">
                </div>
            </div>

            <div class="form-row">
                <div class="form-group">
                    <label>Preço (R$) *</label>
                    <input type="number" step="0.01" min="0" name="price" required
                           value="<?= number_format((float)($package['price'] ?? 0), 2, '.', '') ?>"
                           placeholder="Ex: 29.90">
                </div>
                <div class="form-group">
                    <label>Ordem de exibição</label>
                    <input type="number" name="sort_order" min="0"
                           value="<?= (int)($package['sort_order'] ?? 0) ?>">
                </div>
            </div>

            <div class="form-group">
                <label>Descrição</label>
                <textarea name="description" rows="2"><?= htmlspecialchars($package['description'] ?? '') ?></textarea>
            </div>

            <div class="form-row checkboxes">
                <label>
                    <input type="checkbox" name="is_featured" value="1"
                        <?= ($package['is_featured'] ?? 0) ? 'checked' : '' ?>>
                    Pacote em destaque
                </label>
                <label>
                    <input type="checkbox" name="is_active" value="1"
                        <?= ($package['is_active'] ?? 1) ? 'checked' : '' ?>>
                    Ativo (visível para clientes)
                </label>
            </div>

            <div class="form-actions">
                <a href="/admin/credits" class="btn">Cancelar</a>
                <button type="submit" class="btn btn-primary">
                    <?= $package ? 'Salvar Pacote' : 'Criar Pacote' ?>
                </button>
            </div>
        </form>
    </div>
</div>

<?php require APP_ROOT . '/app/Views/layouts/admin_end.php'; ?>
