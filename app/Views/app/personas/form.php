<?php
$pageTitle = $persona ? 'Editar Persona' : 'Nova Persona';
$action    = $persona ? "/app/personas/{$persona['id']}/update" : '/app/personas';
require APP_ROOT . '/app/Views/layouts/app.php';
?>

<div class="card">
    <div class="card-body">
        <form method="POST" action="<?= $action ?>">
            <?= $csrf ?>
            <div class="form-row">
                <div class="form-group">
                    <label>Nome da Persona *</label>
                    <input type="text" name="name" required
                           value="<?= htmlspecialchars($persona['name'] ?? '') ?>"
                           placeholder="Ex: Assistente Amigável">
                </div>
                <div class="form-group">
                    <label>Agente vinculado (opcional)</label>
                    <select name="agent_id">
                        <option value="">Global (todos os agentes)</option>
                        <?php foreach ($agents as $a): ?>
                        <option value="<?= $a['id'] ?>"
                            <?= ($persona['agent_id'] ?? '') == $a['id'] ? 'selected' : '' ?>>
                            <?= htmlspecialchars($a['name']) ?>
                        </option>
                        <?php endforeach; ?>
                    </select>
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Tom de voz</label>
                    <select name="tone">
                        <?php foreach (['professional','friendly','casual','formal','empathetic','concise'] as $t): ?>
                        <option value="<?= $t ?>" <?= ($persona['tone'] ?? 'professional') === $t ? 'selected' : '' ?>>
                            <?= ucfirst($t) ?>
                        </option>
                        <?php endforeach; ?>
                    </select>
                </div>
                <div class="form-group">
                    <label>Idioma</label>
                    <select name="language">
                        <option value="pt-BR" <?= ($persona['language'] ?? 'pt-BR') === 'pt-BR' ? 'selected' : '' ?>>Português (BR)</option>
                        <option value="en-US" <?= ($persona['language'] ?? '') === 'en-US' ? 'selected' : '' ?>>English (US)</option>
                        <option value="es"    <?= ($persona['language'] ?? '') === 'es'    ? 'selected' : '' ?>>Español</option>
                    </select>
                </div>
            </div>
            <div class="form-group">
                <label>Descrição</label>
                <textarea name="description" rows="2"
                          placeholder="Breve descrição da persona"><?= htmlspecialchars($persona['description'] ?? '') ?></textarea>
            </div>
            <div class="form-group">
                <label>Instruções detalhadas (System Prompt da Persona)</label>
                <textarea name="instructions" rows="10"
                          placeholder="Você é um assistente simpático chamado Ana...&#10;Responda sempre em português.&#10;Nunca invente informações."><?= htmlspecialchars($persona['instructions'] ?? '') ?></textarea>
                <small class="text-muted">Estas instruções são inseridas no início do prompt do sistema do agente.</small>
            </div>
            <div class="form-actions">
                <a href="/app/personas" class="btn">Cancelar</a>
                <button type="submit" class="btn btn-primary">
                    <?= $persona ? 'Salvar Persona' : 'Criar Persona' ?>
                </button>
            </div>
        </form>
    </div>
</div>

<?php require APP_ROOT . '/app/Views/layouts/app_end.php'; ?>
