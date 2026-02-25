<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Setup — Video Downloader</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
</head>
<body class="bg-gray-100 min-h-screen">

<header class="bg-gray-900 text-white shadow">
    <div class="max-w-3xl mx-auto px-4 py-3 flex items-center gap-4">
        <i class="fa-solid fa-screwdriver-wrench text-yellow-400 text-xl"></i>
        <span class="font-bold text-lg">Setup — Video Downloader</span>
        <a href="index.php" class="ml-auto text-sm text-gray-400 hover:text-white transition">
            <i class="fa-solid fa-arrow-left mr-1"></i> Voltar ao app
        </a>
    </div>
</header>

<main class="max-w-3xl mx-auto px-4 py-8 space-y-6">

<?php
$BIN_DIR  = __DIR__ . '/bin';
$BIN_PATH = $BIN_DIR . '/yt-dlp';

// ── Ação: instalar binário ────────────────────────────────────────────────────
if (isset($_POST['action']) && $_POST['action'] === 'install') {
    $url    = 'https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp';
    $result = ['ok' => false, 'msg' => ''];

    if (!is_dir($BIN_DIR)) {
        @mkdir($BIN_DIR, 0755, true);
    }

    // Tenta com file_get_contents primeiro, depois curl
    $content = false;
    if (ini_get('allow_url_fopen')) {
        $ctx     = stream_context_create(['http' => ['follow_location' => true, 'timeout' => 60]]);
        $content = @file_get_contents($url, false, $ctx);
    }
    if ($content === false && function_exists('curl_init')) {
        $ch = curl_init($url);
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_FOLLOWLOCATION => true,
            CURLOPT_TIMEOUT        => 60,
            CURLOPT_SSL_VERIFYPEER => true,
            CURLOPT_USERAGENT      => 'Mozilla/5.0',
        ]);
        $content = curl_exec($ch);
        if (curl_errno($ch)) $content = false;
        curl_close($ch);
    }

    if ($content === false || strlen($content) < 1000) {
        $result['msg'] = 'Falha ao baixar o binário. Tente pelo SSH (instruções abaixo).';
    } else {
        file_put_contents($BIN_PATH, $content);
        @chmod($BIN_PATH, 0755);

        // Testa
        $out = []; $rc = -1;
        exec(escapeshellarg($BIN_PATH) . ' --version 2>/dev/null', $out, $rc);
        if ($rc === 0) {
            $result = ['ok' => true, 'msg' => 'yt-dlp instalado com sucesso! Versão: ' . trim($out[0] ?? '')];
        } else {
            $result['msg'] = 'Binário baixado mas não executou (exec() pode estar bloqueado ou arquitetura incompatível).';
        }
    }
    ?>
    <div class="rounded-xl p-5 border <?= $result['ok'] ? 'bg-green-50 border-green-300' : 'bg-red-50 border-red-300' ?>">
        <div class="flex items-center gap-3">
            <i class="fa-solid <?= $result['ok'] ? 'fa-circle-check text-green-500' : 'fa-circle-xmark text-red-500' ?> text-2xl"></i>
            <div>
                <p class="font-semibold <?= $result['ok'] ? 'text-green-800' : 'text-red-800' ?>"><?= htmlspecialchars($result['msg']) ?></p>
                <?php if ($result['ok']): ?>
                    <a href="index.php" class="text-sm text-green-700 underline">Abrir o app →</a>
                <?php endif; ?>
            </div>
        </div>
    </div>
    <?php
}

// ── Checagens do ambiente ─────────────────────────────────────────────────────
$checks = [];

// 1. exec() habilitado
$exec_ok = function_exists('exec') && !in_array('exec', array_map('trim', explode(',', ini_get('disable_functions'))));
$checks[] = [
    'label' => 'exec() habilitado',
    'ok'    => $exec_ok,
    'desc'  => $exec_ok
        ? 'PHP pode executar processos externos.'
        : 'exec() está desabilitado. Sem isso o yt-dlp não funciona. No Hostinger, ative em: Hospedagem → Avançado → PHP Configuration → disable_functions (remova "exec").',
];

// 2. shell_exec() habilitado
$shell_ok = function_exists('shell_exec') && !in_array('shell_exec', array_map('trim', explode(',', ini_get('disable_functions'))));
$checks[] = [
    'label' => 'shell_exec() habilitado',
    'ok'    => $shell_ok,
    'desc'  => $shell_ok ? 'PHP pode capturar saída de comandos.' : 'shell_exec() está desabilitado. Necessário para buscar a lista de vídeos.',
];

// 3. allow_url_fopen ou curl (para baixar o binário)
$fopen_ok = (bool)ini_get('allow_url_fopen');
$curl_ok  = function_exists('curl_init');
$download_ok = $fopen_ok || $curl_ok;
$checks[] = [
    'label' => 'Download de URL (allow_url_fopen ou cURL)',
    'ok'    => $download_ok,
    'desc'  => $download_ok
        ? ($fopen_ok ? 'allow_url_fopen ativado.' : '') . ($curl_ok ? ' cURL disponível.' : '')
        : 'Sem allow_url_fopen nem cURL não é possível baixar o binário automaticamente. Use SSH.',
];

// 4. ZipArchive
$zip_ok = class_exists('ZipArchive');
$checks[] = [
    'label' => 'ZipArchive (para criar ZIP)',
    'ok'    => $zip_ok,
    'desc'  => $zip_ok ? 'Extensão ZipArchive disponível.' : 'ZipArchive não encontrado. Instale a extensão php-zip.',
];

// 5. yt-dlp já instalado (sistema ou local)
$ytdlp_bin = '';
foreach ([$BIN_PATH, 'yt-dlp', '/usr/local/bin/yt-dlp', '/usr/bin/yt-dlp'] as $b) {
    $o = []; $rc = -1;
    @exec(escapeshellarg($b) . ' --version 2>/dev/null', $o, $rc);
    if ($rc === 0) { $ytdlp_bin = $b; break; }
    $o = [];
}
$ytdlp_ok      = $ytdlp_bin !== '';
$ytdlp_version = '';
if ($ytdlp_ok) {
    $ov = []; @exec(escapeshellarg($ytdlp_bin) . ' --version 2>/dev/null', $ov);
    $ytdlp_version = trim($ov[0] ?? '');
}
$checks[] = [
    'label' => 'yt-dlp encontrado',
    'ok'    => $ytdlp_ok,
    'desc'  => $ytdlp_ok
        ? "Encontrado em: {$ytdlp_bin}" . ($ytdlp_version ? " (v{$ytdlp_version})" : '')
        : 'yt-dlp não encontrado. Use o botão abaixo para instalar automaticamente.',
];

// 6. Pasta downloads com permissão de escrita
$dl_dir = __DIR__ . '/downloads';
$dl_ok  = is_dir($dl_dir) && is_writable($dl_dir);
if (!$dl_ok && is_dir($dl_dir)) @chmod($dl_dir, 0755);
$dl_ok = is_dir($dl_dir) && is_writable($dl_dir);
$checks[] = [
    'label' => 'Pasta downloads/ com escrita',
    'ok'    => $dl_ok,
    'desc'  => $dl_ok ? 'Pasta downloads/ existe e tem permissão de escrita.' : 'Sem permissão de escrita em downloads/. Execute: chmod 755 downloads/',
];

// 6. Pasta bin com permissão de escrita
$bin_writable = is_dir($BIN_DIR) ? is_writable($BIN_DIR) : is_writable(__DIR__);
$checks[] = [
    'label' => 'Pasta bin/ pode ser criada/escrita',
    'ok'    => $bin_writable,
    'desc'  => $bin_writable ? 'Pode salvar o binário yt-dlp em bin/.' : 'Sem permissão para criar/escrever em bin/. Execute: chmod 755 .',
];

$all_critical_ok = $exec_ok && $shell_ok && $zip_ok;
$ready = $ytdlp_ok && $all_critical_ok;
?>

<!-- Status geral -->
<div class="rounded-xl p-5 border <?= $ready ? 'bg-green-50 border-green-300' : ($all_critical_ok ? 'bg-yellow-50 border-yellow-300' : 'bg-red-50 border-red-300') ?>">
    <div class="flex items-center gap-3">
        <i class="fa-solid <?= $ready ? 'fa-circle-check text-green-500' : ($all_critical_ok ? 'fa-triangle-exclamation text-yellow-500' : 'fa-circle-xmark text-red-500') ?> text-3xl"></i>
        <div>
            <p class="font-bold text-lg text-gray-800">
                <?php if ($ready): ?>
                    Tudo pronto! O app está funcionando.
                <?php elseif ($all_critical_ok): ?>
                    PHP OK — só falta instalar o yt-dlp.
                <?php else: ?>
                    Problemas críticos encontrados. Veja os detalhes abaixo.
                <?php endif; ?>
            </p>
            <?php if ($ready): ?>
                <a href="index.php" class="text-sm text-green-700 underline">Abrir o app →</a>
            <?php endif; ?>
        </div>
    </div>
</div>

<!-- Checklist -->
<div class="bg-white rounded-xl shadow divide-y">
    <?php foreach ($checks as $c): ?>
    <div class="flex items-start gap-4 p-4">
        <i class="fa-solid <?= $c['ok'] ? 'fa-circle-check text-green-500' : 'fa-circle-xmark text-red-500' ?> text-lg mt-0.5 shrink-0"></i>
        <div>
            <p class="font-semibold text-gray-800 text-sm"><?= htmlspecialchars($c['label']) ?></p>
            <p class="text-xs text-gray-500 mt-0.5"><?= htmlspecialchars($c['desc']) ?></p>
        </div>
    </div>
    <?php endforeach; ?>
</div>

<!-- Instalar yt-dlp automaticamente -->
<?php if (!$ytdlp_ok && $all_critical_ok && $download_ok && $bin_writable): ?>
<div class="bg-white rounded-xl shadow p-5">
    <h2 class="font-bold text-gray-800 mb-2 flex items-center gap-2">
        <i class="fa-solid fa-download text-blue-500"></i>
        Instalar yt-dlp automaticamente
    </h2>
    <p class="text-sm text-gray-600 mb-4">
        Baixa o binário standalone direto do GitHub Releases e salva em <code class="bg-gray-100 px-1 rounded">bin/yt-dlp</code>.
        Não precisa de Python nem pip.
    </p>
    <form method="POST">
        <input type="hidden" name="action" value="install">
        <button type="submit"
                class="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2.5 rounded-lg font-semibold text-sm transition flex items-center gap-2">
            <i class="fa-solid fa-bolt"></i> Instalar agora (binário standalone)
        </button>
    </form>
</div>
<?php endif; ?>

<!-- Instruções SSH (sempre visível quando yt-dlp não está instalado) -->
<?php if (!$ytdlp_ok): ?>
<div class="bg-white rounded-xl shadow p-5 space-y-4">
    <h2 class="font-bold text-gray-800 flex items-center gap-2">
        <i class="fa-solid fa-terminal text-gray-600"></i>
        Instalar via SSH (alternativa manual)
    </h2>

    <p class="text-sm text-gray-600">
        Acesse o servidor via SSH (Hostinger → Hospedagem → SSH Access) e execute:
    </p>

    <div class="bg-gray-900 text-green-400 rounded-lg p-4 text-sm font-mono space-y-1 overflow-x-auto">
        <p><span class="text-gray-500"># Navega para a pasta do projeto</span></p>
        <p>cd <?= htmlspecialchars(__DIR__) ?></p>
        <p>&nbsp;</p>
        <p><span class="text-gray-500"># Baixa o binário standalone (não precisa de Python)</span></p>
        <p>mkdir -p bin</p>
        <p>curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o bin/yt-dlp</p>
        <p>chmod +x bin/yt-dlp</p>
        <p>&nbsp;</p>
        <p><span class="text-gray-500"># Testa</span></p>
        <p>bin/yt-dlp --version</p>
    </div>

    <p class="text-sm text-gray-600">Após executar, <a href="setup.php" class="text-blue-600 underline">recarregue esta página</a> para confirmar.</p>
</div>
<?php endif; ?>

<?php if (!$exec_ok): ?>
<!-- exec() desabilitado: instrução específica Hostinger -->
<div class="bg-orange-50 border border-orange-200 rounded-xl p-5 space-y-3">
    <h2 class="font-bold text-orange-800 flex items-center gap-2">
        <i class="fa-solid fa-triangle-exclamation"></i>
        Como habilitar exec() no Hostinger
    </h2>
    <ol class="text-sm text-orange-900 space-y-2 list-decimal list-inside">
        <li>Acesse o painel Hostinger (hPanel)</li>
        <li>Vá em <strong>Hospedagem → Gerenciar → Configurações Avançadas → PHP Configuration</strong></li>
        <li>Localize a diretiva <code class="bg-orange-100 px-1 rounded">disable_functions</code></li>
        <li>Remova <code class="bg-orange-100 px-1 rounded">exec</code> e <code class="bg-orange-100 px-1 rounded">shell_exec</code> da lista</li>
        <li>Salve e recarregue esta página</li>
    </ol>
    <p class="text-xs text-orange-700">
        ⚠️ Se não aparecer essa opção, seu plano pode ser muito restrito.
        Planos <strong>Business</strong> e <strong>Cloud</strong> do Hostinger costumam permitir exec().
    </p>
</div>
<?php endif; ?>

<!-- Botão recarregar -->
<div class="text-center">
    <a href="setup.php"
       class="inline-flex items-center gap-2 bg-gray-200 hover:bg-gray-300 text-gray-700 px-5 py-2 rounded-lg text-sm font-semibold transition">
        <i class="fa-solid fa-rotate-right"></i> Recarregar checagem
    </a>
</div>

</main>
</body>
</html>
