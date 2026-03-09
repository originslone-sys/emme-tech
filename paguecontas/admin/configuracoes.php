<?php
require_once __DIR__ . '/../includes/auth.php';
requireAdmin();

$stmt = $pdo->query("SELECT COUNT(*) as total FROM recharges WHERE status = 'pending'");
$pendingRecharges = $stmt->fetch()['total'];

$success = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $settings = [
        'cashback_percent' => $_POST['cashback_percent'] ?? '5',
        'min_deposit' => $_POST['min_deposit'] ?? '10.00',
        'max_deposit' => $_POST['max_deposit'] ?? '10000.00',
        'min_payment' => $_POST['min_payment'] ?? '5.00',
        'max_payment' => $_POST['max_payment'] ?? '50000.00',
        'pix_key' => $_POST['pix_key'] ?? '',
        'site_name' => $_POST['site_name'] ?? 'PagueContas',
        'site_description' => $_POST['site_description'] ?? ''
    ];

    foreach ($settings as $key => $value) {
        $stmt = $pdo->prepare("INSERT INTO settings (setting_key, setting_value) VALUES (?, ?) ON DUPLICATE KEY UPDATE setting_value = ?");
        $stmt->execute([$key, $value, $value]);
    }

    $success = 'Configurações salvas com sucesso!';
}

// Load current settings
$stmt = $pdo->query("SELECT setting_key, setting_value FROM settings");
$settingsRaw = $stmt->fetchAll();
$settings = [];
foreach ($settingsRaw as $s) {
    $settings[$s['setting_key']] = $s['setting_value'];
}
?>
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Configurações - Admin PagueContas</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="../assets/css/style.css">
    <link rel="stylesheet" href="../cliente/assets/css/dashboard.css">
    <link rel="stylesheet" href="assets/css/admin.css">
</head>
<body>
    <div class="dashboard-layout">
        <?php include 'includes/sidebar.php'; ?>

        <div class="main-content">
            <div class="content-header">
                <div>
                    <button class="sidebar-toggle" onclick="document.getElementById('sidebar').classList.toggle('active')">&#9776;</button>
                    <h1>Configurações</h1>
                    <p class="header-subtitle">Configure os parâmetros da plataforma</p>
                </div>
            </div>

            <div class="content-body">
                <?php if ($success): ?>
                    <div class="alert alert-success"><span>&#10003;</span> <?= $success ?></div>
                <?php endif; ?>

                <form method="POST">
                    <div class="dashboard-grid">
                        <div>
                            <!-- General -->
                            <div class="card" style="margin-bottom: 24px;">
                                <div class="card-header"><h3>&#9881; Geral</h3></div>
                                <div class="card-body" style="padding: 24px;">
                                    <div class="form-group">
                                        <label>Nome do Site</label>
                                        <input type="text" name="site_name" class="form-control" value="<?= sanitize($settings['site_name'] ?? 'PagueContas') ?>">
                                    </div>
                                    <div class="form-group">
                                        <label>Descrição</label>
                                        <input type="text" name="site_description" class="form-control" value="<?= sanitize($settings['site_description'] ?? '') ?>">
                                    </div>
                                </div>
                            </div>

                            <!-- Financial -->
                            <div class="card" style="margin-bottom: 24px;">
                                <div class="card-header"><h3>&#128176; Financeiro</h3></div>
                                <div class="card-body" style="padding: 24px;">
                                    <div class="form-group">
                                        <label>Cashback (%)</label>
                                        <input type="number" name="cashback_percent" class="form-control" min="0" max="100" step="0.5" value="<?= sanitize($settings['cashback_percent'] ?? '5') ?>">
                                        <div class="form-text">Porcentagem de cashback aplicada em cada pagamento</div>
                                    </div>
                                    <div class="form-row">
                                        <div class="form-group">
                                            <label>Depósito Mínimo (R$)</label>
                                            <input type="number" name="min_deposit" class="form-control" step="0.01" value="<?= sanitize($settings['min_deposit'] ?? '10.00') ?>">
                                        </div>
                                        <div class="form-group">
                                            <label>Depósito Máximo (R$)</label>
                                            <input type="number" name="max_deposit" class="form-control" step="0.01" value="<?= sanitize($settings['max_deposit'] ?? '10000.00') ?>">
                                        </div>
                                    </div>
                                    <div class="form-row">
                                        <div class="form-group">
                                            <label>Pagamento Mínimo (R$)</label>
                                            <input type="number" name="min_payment" class="form-control" step="0.01" value="<?= sanitize($settings['min_payment'] ?? '5.00') ?>">
                                        </div>
                                        <div class="form-group">
                                            <label>Pagamento Máximo (R$)</label>
                                            <input type="number" name="max_payment" class="form-control" step="0.01" value="<?= sanitize($settings['max_payment'] ?? '50000.00') ?>">
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- PIX -->
                            <div class="card">
                                <div class="card-header"><h3>&#128273; Dados PIX</h3></div>
                                <div class="card-body" style="padding: 24px;">
                                    <div class="form-group">
                                        <label>Chave PIX</label>
                                        <input type="text" name="pix_key" class="form-control" value="<?= sanitize($settings['pix_key'] ?? '') ?>" placeholder="E-mail, CPF, CNPJ ou chave aleatória">
                                        <div class="form-text">Esta chave será exibida para os clientes na página de recarga</div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div>
                            <div class="card" style="margin-bottom: 24px;">
                                <div class="card-body" style="padding: 24px; text-align: center;">
                                    <div style="font-size: 48px; margin-bottom: 12px;">&#9881;</div>
                                    <h3 style="font-size: 16px; margin-bottom: 8px;">Configurações</h3>
                                    <p style="font-size: 13px; color: var(--text-muted); margin-bottom: 20px;">Altere os parâmetros e clique em salvar para aplicar as mudanças.</p>
                                    <button type="submit" class="btn btn-primary btn-block">Salvar Configurações</button>
                                </div>
                            </div>

                            <div class="card">
                                <div class="card-header"><h3>Informações</h3></div>
                                <div class="card-body" style="padding: 24px;">
                                    <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
                                        <span style="font-size: 13px; color: var(--text-muted);">Versão</span>
                                        <span style="font-size: 13px; font-weight: 600;">v<?= APP_VERSION ?></span>
                                    </div>
                                    <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
                                        <span style="font-size: 13px; color: var(--text-muted);">PHP</span>
                                        <span style="font-size: 13px; font-weight: 600;"><?= phpversion() ?></span>
                                    </div>
                                    <div style="display: flex; justify-content: space-between;">
                                        <span style="font-size: 13px; color: var(--text-muted);">Banco de Dados</span>
                                        <span style="font-size: 13px; font-weight: 600;">MySQL</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </form>
            </div>
        </div>
    </div>
    <script src="../assets/js/main.js"></script>
</body>
</html>
