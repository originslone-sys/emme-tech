<?php
/**
 * Script de Instalacao - Nuvem Storage
 *
 * Execute este script uma vez para configurar a aplicacao.
 * Acesse: https://seudominio.com/nuvem/install.php
 *
 * IMPORTANTE: Apague este arquivo apos a instalacao!
 */

$step = $_GET['step'] ?? '1';
$error = '';
$success = '';

// Step 2: Salvar configuracao
if ($step === '2' && $_SERVER['REQUEST_METHOD'] === 'POST') {
    $endpoint = trim($_POST['endpoint'] ?? '');
    $region = trim($_POST['region'] ?? 'us-east-1');
    $key = trim($_POST['key'] ?? '');
    $secret = trim($_POST['secret'] ?? '');
    $bucket = trim($_POST['bucket'] ?? '');
    $password = trim($_POST['password'] ?? '');

    if (empty($endpoint) || empty($key) || empty($secret) || empty($bucket) || empty($password)) {
        $error = 'Todos os campos sao obrigatorios.';
        $step = '1';
    } else {
        $configContent = "<?php\nreturn [\n";
        $configContent .= "    'e2' => [\n";
        $configContent .= "        'endpoint' => " . var_export($endpoint, true) . ",\n";
        $configContent .= "        'region'   => " . var_export($region, true) . ",\n";
        $configContent .= "        'key'      => " . var_export($key, true) . ",\n";
        $configContent .= "        'secret'   => " . var_export($secret, true) . ",\n";
        $configContent .= "        'bucket'   => " . var_export($bucket, true) . ",\n";
        $configContent .= "        'version'  => 'latest',\n";
        $configContent .= "    ],\n";
        $configContent .= "    'app' => [\n";
        $configContent .= "        'name'       => 'Nuvem - Armazenamento',\n";
        $configContent .= "        'max_upload' => 500 * 1024 * 1024,\n";
        $configContent .= "        'password'   => " . var_export($password, true) . ",\n";
        $configContent .= "    ],\n";
        $configContent .= "];\n";

        if (file_put_contents(__DIR__ . '/config.php', $configContent)) {
            $success = 'Configuracao salva com sucesso!';
        } else {
            $error = 'Erro ao salvar config.php. Verifique as permissoes da pasta.';
            $step = '1';
        }
    }
}

// Step 3: Verificar composer
if ($step === '3') {
    if (!file_exists(__DIR__ . '/vendor/autoload.php')) {
        $error = 'vendor/autoload.php nao encontrado. Execute "composer install" no servidor.';
    }
}
?>
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Instalacao - Nuvem Storage</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
            color: #e0e0e0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .installer {
            width: 560px;
            max-width: 100%;
            background: #2d2d3f;
            border-radius: 8px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.4);
            border: 1px solid #404060;
            overflow: hidden;
        }
        .installer-header {
            background: #1a1a2e;
            padding: 12px 16px;
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 14px;
        }
        .installer-header i { color: #0078d4; }
        .installer-body { padding: 24px; }
        h2 { font-size: 18px; margin-bottom: 16px; }
        .steps {
            display: flex;
            gap: 8px;
            margin-bottom: 20px;
        }
        .step-dot {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            background: #404060;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 13px;
            font-weight: 600;
        }
        .step-dot.active { background: #0078d4; }
        .step-dot.done { background: #4caf50; }
        .form-group { margin-bottom: 14px; }
        .form-group label {
            display: block;
            margin-bottom: 4px;
            font-size: 13px;
            color: #a0a0b0;
        }
        .form-group input {
            width: 100%;
            padding: 8px 12px;
            background: #1e1e2e;
            border: 1px solid #404060;
            border-radius: 4px;
            color: #e0e0e0;
            font-size: 14px;
            outline: none;
        }
        .form-group input:focus { border-color: #0078d4; }
        .form-group small { color: #888; font-size: 11px; }
        .btn {
            padding: 8px 24px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            transition: background 0.2s;
        }
        .btn-primary { background: #0078d4; color: white; }
        .btn-primary:hover { background: #106ebe; }
        .alert {
            padding: 10px 14px;
            border-radius: 4px;
            margin-bottom: 14px;
            font-size: 13px;
        }
        .alert-error { background: rgba(244,67,54,0.15); color: #f44336; border: 1px solid rgba(244,67,54,0.3); }
        .alert-success { background: rgba(76,175,80,0.15); color: #4caf50; border: 1px solid rgba(76,175,80,0.3); }
        .checklist { list-style: none; }
        .checklist li {
            padding: 8px 0;
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 14px;
        }
        .check-ok { color: #4caf50; }
        .check-fail { color: #f44336; }
        pre {
            background: #1e1e2e;
            padding: 12px;
            border-radius: 4px;
            font-size: 12px;
            overflow-x: auto;
            margin: 8px 0;
        }
    </style>
</head>
<body>
    <div class="installer">
        <div class="installer-header">
            <span>Instalacao - Nuvem Storage</span>
        </div>
        <div class="installer-body">
            <div class="steps">
                <div class="step-dot <?= $step >= 1 ? ($step > 1 ? 'done' : 'active') : '' ?>">1</div>
                <div class="step-dot <?= $step >= 2 ? ($step > 2 ? 'done' : 'active') : '' ?>">2</div>
                <div class="step-dot <?= $step >= 3 ? 'active' : '' ?>">3</div>
            </div>

            <?php if ($error): ?>
                <div class="alert alert-error"><?= htmlspecialchars($error) ?></div>
            <?php endif; ?>

            <?php if ($step === '1'): ?>
                <h2>Passo 1: Configuracao do IDrive E2</h2>
                <p style="margin-bottom:16px; color:#a0a0b0; font-size:13px">
                    Preencha os dados da sua conta IDrive E2. Obtenha suas credenciais em
                    <a href="https://www.idrive.com/s3-storage-e2/" target="_blank" style="color:#0078d4">idrive.com/s3-storage-e2</a>
                </p>

                <form method="POST" action="?step=2">
                    <div class="form-group">
                        <label>Endpoint S3</label>
                        <input type="text" name="endpoint" placeholder="https://k3s5.fra.idrivee2-45.com" required>
                        <small>Encontre no painel IDrive E2 > Storage > Endpoint</small>
                    </div>
                    <div class="form-group">
                        <label>Regiao</label>
                        <input type="text" name="region" value="us-east-1" placeholder="us-east-1">
                    </div>
                    <div class="form-group">
                        <label>Access Key ID</label>
                        <input type="text" name="key" placeholder="Sua access key" required>
                    </div>
                    <div class="form-group">
                        <label>Secret Access Key</label>
                        <input type="password" name="secret" placeholder="Sua secret key" required>
                    </div>
                    <div class="form-group">
                        <label>Nome do Bucket</label>
                        <input type="text" name="bucket" placeholder="meu-bucket" required>
                        <small>Crie o bucket antes no painel IDrive E2</small>
                    </div>
                    <div class="form-group">
                        <label>Senha de Acesso ao Painel</label>
                        <input type="password" name="password" placeholder="Defina uma senha forte" required>
                        <small>Essa senha sera usada para acessar o painel de arquivos</small>
                    </div>
                    <button type="submit" class="btn btn-primary">Proximo</button>
                </form>

            <?php elseif ($step === '2'): ?>
                <?php if ($success): ?>
                    <div class="alert alert-success"><?= htmlspecialchars($success) ?></div>
                <?php endif; ?>

                <h2>Passo 2: Instalar Dependencias</h2>
                <p style="margin-bottom:16px; color:#a0a0b0; font-size:13px">
                    Acesse o servidor via SSH e execute o comando abaixo na pasta <code>nuvem/</code>:
                </p>

                <pre>cd ~/public_html/nuvem
composer install --no-dev --optimize-autoloader</pre>

                <p style="margin-bottom:16px; color:#a0a0b0; font-size:13px">
                    Se nao tiver o Composer no servidor, baixe em <a href="https://getcomposer.org" target="_blank" style="color:#0078d4">getcomposer.org</a>
                    ou use: <code>php composer.phar install</code>
                </p>

                <a href="?step=3" class="btn btn-primary">Verificar Instalacao</a>

            <?php elseif ($step === '3'): ?>
                <h2>Passo 3: Verificacao Final</h2>

                <ul class="checklist">
                    <?php
                    $checks = [
                        ['config.php existe', file_exists(__DIR__ . '/config.php')],
                        ['vendor/autoload.php existe', file_exists(__DIR__ . '/vendor/autoload.php')],
                        ['Pasta src/ acessivel', is_dir(__DIR__ . '/src')],
                        ['.htaccess presente', file_exists(__DIR__ . '/.htaccess')],
                        ['PHP >= 7.4', version_compare(PHP_VERSION, '7.4.0', '>=')],
                    ];

                    $allOk = true;
                    foreach ($checks as [$label, $ok]):
                        if (!$ok) $allOk = false;
                    ?>
                        <li>
                            <span class="<?= $ok ? 'check-ok' : 'check-fail' ?>">
                                <?= $ok ? '&#10003;' : '&#10007;' ?>
                            </span>
                            <?= htmlspecialchars($label) ?>
                        </li>
                    <?php endforeach; ?>
                </ul>

                <?php if ($allOk): ?>
                    <div class="alert alert-success" style="margin-top:16px">
                        Tudo pronto! Acesse <a href="index.php" style="color:#4caf50; font-weight:600">index.php</a> para usar o Nuvem Storage.
                        <br><br>
                        <strong>IMPORTANTE:</strong> Apague este arquivo (install.php) por seguranca!
                    </div>
                <?php else: ?>
                    <div class="alert alert-error" style="margin-top:16px">
                        Algumas verificacoes falharam. Corrija os problemas acima e tente novamente.
                    </div>
                    <a href="?step=3" class="btn btn-primary" style="margin-top:8px">Verificar Novamente</a>
                <?php endif; ?>

            <?php endif; ?>
        </div>
    </div>
</body>
</html>
