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

// ── Helpers ───────────────────────────────────────────────────────────────────

/**
 * Verifica se exec() está disponível SEM chamá-la.
 * @param string $func 'exec' | 'shell_exec' | etc.
 */
function fn_enabled(string $func): bool {
    if (!function_exists($func)) return false;
    $disabled = array_map('trim', explode(',', (string) ini_get('disable_functions')));
    return !in_array($func, $disabled, true);
}

/**
 * Chama exec() somente se ela estiver disponível.
 * Retorna false se exec() estiver desabilitada (sem lançar fatal error).
 */
function safe_exec(string $cmd, array &$output = [], int &$rc = -1): bool {
    static $ok = null;
    if ($ok === null) $ok = fn_enabled('exec');
    if (!$ok) { $output = []; $rc = -1; return false; }
    exec($cmd, $output, $rc);
    return true;
}

$BIN_DIR  = __DIR__ . '/bin';
$BIN_PATH = $BIN_DIR . '/yt-dlp';

// ── Helpers de diagnóstico ────────────────────────────────────────────────────

/** Detecta a arquitetura do servidor via uname -m */
function detect_arch(): string {
    $out = []; $rc = -1;
    safe_exec('uname -m 2>/dev/null', $out, $rc);
    return $rc === 0 ? trim($out[0] ?? '') : 'unknown';
}

/** Retorna a URL de download do binário yt-dlp para a arquitetura atual */
function ytdlp_url(string $arch): string {
    $base = 'https://github.com/yt-dlp/yt-dlp/releases/latest/download/';
    return match(true) {
        str_contains($arch, 'aarch64') || str_contains($arch, 'arm64') => $base . 'yt-dlp_linux_aarch64',
        str_contains($arch, 'armv7')                                    => $base . 'yt-dlp_linux_armv7l',
        str_contains($arch, 'i686') || str_contains($arch, 'i386')     => $base . 'yt-dlp_x86',
        default                                                          => $base . 'yt-dlp',  // x86_64
    };
}

/** Baixa URL via file_get_contents ou cURL */
function fetch_url(string $url): string|false {
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
    return $content;
}

// ── Ação: instalar binário ────────────────────────────────────────────────────
if (isset($_POST['action']) && $_POST['action'] === 'install') {
    $result = ['ok' => false, 'msg' => '', 'detail' => ''];

    if (!is_dir($BIN_DIR)) @mkdir($BIN_DIR, 0755, true);

    // Detecta arquitetura e escolhe o binário correto
    $arch    = detect_arch();
    $url     = ytdlp_url($arch);
    $content = fetch_url($url);

    if ($content === false || strlen((string)$content) < 1000) {
        $result['msg']    = 'Falha ao baixar o binário. Tente pelo SSH (instruções abaixo).';
        $result['detail'] = "URL tentada: {$url}";
    } else {
        // Verifica se é um binário ELF válido (não uma página HTML de erro)
        $magic = substr($content, 0, 4);
        if ($magic !== "\x7fELF") {
            $result['msg']    = 'O arquivo baixado não é um binário válido (recebeu HTML?).';
            $result['detail'] = "Primeiros bytes: " . bin2hex($magic) . ". Tente pelo SSH.";
        } else {
            file_put_contents($BIN_PATH, $content);
            @chmod($BIN_PATH, 0755);

            // Testa e captura o erro real (2>&1 para incluir stderr)
            $out = []; $rc = -1;
            safe_exec(escapeshellarg($BIN_PATH) . ' --version 2>&1', $out, $rc);
            if ($rc === 0) {
                $result = ['ok' => true, 'msg' => 'yt-dlp instalado com sucesso! Versão: ' . trim($out[0] ?? ''), 'detail' => "Arch: {$arch} | Binário: {$url}"];
            } else {
                $err = implode(' ', $out);
                // Detecta noexec
                $is_noexec = str_contains($err, 'Permission denied') || str_contains($err, 'cannot execute');
                $result['msg'] = $is_noexec
                    ? 'Erro de permissão ao executar: o diretório pode estar montado com noexec.'
                    : 'Binário baixado mas não executou.';
                $result['detail'] = "Arch: {$arch} | RC: {$rc}" . ($err ? " | Erro: {$err}" : " | (sem saída de erro)");
            }
        }
    }
    ?>
    <div class="rounded-xl p-5 border <?= $result['ok'] ? 'bg-green-50 border-green-300' : 'bg-red-50 border-red-300' ?>">
        <div class="flex items-start gap-3">
            <i class="fa-solid <?= $result['ok'] ? 'fa-circle-check text-green-500' : 'fa-circle-xmark text-red-500' ?> text-2xl mt-0.5 shrink-0"></i>
            <div>
                <p class="font-semibold <?= $result['ok'] ? 'text-green-800' : 'text-red-800' ?>"><?= htmlspecialchars($result['msg']) ?></p>
                <?php if (!empty($result['detail'])): ?>
                    <p class="text-xs mt-1 font-mono <?= $result['ok'] ? 'text-green-700' : 'text-red-700' ?>"><?= htmlspecialchars($result['detail']) ?></p>
                <?php endif; ?>
                <?php if ($result['ok']): ?>
                    <a href="index.php" class="text-sm text-green-700 underline mt-1 block">Abrir o app →</a>
                <?php endif; ?>
            </div>
        </div>
    </div>
    <?php
}

// ── Ação: instalar via pip3 ───────────────────────────────────────────────────
if (isset($_POST['action']) && $_POST['action'] === 'install_pip') {
    $result = ['ok' => false, 'msg' => '', 'detail' => ''];
    $out = []; $rc = -1;
    safe_exec('pip3 install --user yt-dlp 2>&1', $out, $rc);
    if ($rc === 0) {
        // Localiza onde o pip instalou
        $wo = []; safe_exec('python3 -m yt_dlp --version 2>&1', $wo, $wrc);
        if ($wrc === 0) {
            $result = ['ok' => true, 'msg' => 'yt-dlp instalado via pip3! Versão: ' . trim($wo[0] ?? ''), 'detail' => 'Use "python3 -m yt_dlp" (o api.php será atualizado).'];
        } else {
            $result['msg']    = 'pip3 instalou mas não conseguiu executar.';
            $result['detail'] = implode(' ', array_slice($out, -3));
        }
    } else {
        $result['msg']    = 'Falha no pip3 install.';
        $result['detail'] = implode(' ', array_slice($out, -5));
    }
    ?>
    <div class="rounded-xl p-5 border <?= $result['ok'] ? 'bg-green-50 border-green-300' : 'bg-red-50 border-red-300' ?>">
        <div class="flex items-start gap-3">
            <i class="fa-solid <?= $result['ok'] ? 'fa-circle-check text-green-500' : 'fa-circle-xmark text-red-500' ?> text-2xl mt-0.5 shrink-0"></i>
            <div>
                <p class="font-semibold <?= $result['ok'] ? 'text-green-800' : 'text-red-800' ?>"><?= htmlspecialchars($result['msg']) ?></p>
                <?php if (!empty($result['detail'])): ?>
                    <p class="text-xs mt-1 font-mono <?= $result['ok'] ? 'text-green-700' : 'text-red-700' ?>"><?= htmlspecialchars($result['detail']) ?></p>
                <?php endif; ?>
            </div>
        </div>
    </div>
    <?php
}

// ── Checagens do ambiente ─────────────────────────────────────────────────────
$checks = [];

// 1. exec() habilitado
$exec_ok = fn_enabled('exec');
$checks[] = [
    'label' => 'exec() habilitado',
    'ok'    => $exec_ok,
    'desc'  => $exec_ok
        ? 'PHP pode executar processos externos.'
        : 'exec() está desabilitado. Sem isso o yt-dlp não funciona. No Hostinger: hPanel → Hospedagem → Avançado → Configuração do PHP → disable_functions (remova "exec").',
];

// 2. shell_exec() habilitado
$shell_ok = fn_enabled('shell_exec');
$checks[] = [
    'label' => 'shell_exec() habilitado',
    'ok'    => $shell_ok,
    'desc'  => $shell_ok
        ? 'PHP pode capturar saída de comandos.'
        : 'shell_exec() está desabilitado. Remova "shell_exec" de disable_functions no painel Hostinger.',
];

// 3. allow_url_fopen ou cURL (para baixar o binário)
$fopen_ok    = (bool) ini_get('allow_url_fopen');
$curl_ok     = function_exists('curl_init');
$download_ok = $fopen_ok || $curl_ok;
$checks[] = [
    'label' => 'Download de URL (allow_url_fopen ou cURL)',
    'ok'    => $download_ok,
    'desc'  => $download_ok
        ? trim(($fopen_ok ? 'allow_url_fopen ativado.' : '') . ($curl_ok ? ' cURL disponível.' : ''))
        : 'Sem allow_url_fopen nem cURL não é possível baixar o binário automaticamente. Use SSH.',
];

// 4. ZipArchive
$zip_ok = class_exists('ZipArchive');
$checks[] = [
    'label' => 'ZipArchive (para criar ZIP)',
    'ok'    => $zip_ok,
    'desc'  => $zip_ok
        ? 'Extensão ZipArchive disponível.'
        : 'ZipArchive não encontrado. Ative a extensão php-zip no painel do Hostinger.',
];

// 5. yt-dlp já instalado (local ou sistema) — usa safe_exec, nunca lança fatal
$ytdlp_bin = '';
if ($exec_ok) {
    foreach ([$BIN_PATH, 'yt-dlp', '/usr/local/bin/yt-dlp', '/usr/bin/yt-dlp'] as $b) {
        $o = []; $rc = -1;
        safe_exec(escapeshellarg($b) . ' --version 2>/dev/null', $o, $rc);
        if ($rc === 0) { $ytdlp_bin = $b; break; }
    }
}
$ytdlp_ok      = $ytdlp_bin !== '';
$ytdlp_version = '';
if ($ytdlp_ok) {
    $ov = []; safe_exec(escapeshellarg($ytdlp_bin) . ' --version 2>/dev/null', $ov);
    $ytdlp_version = trim($ov[0] ?? '');
}
$checks[] = [
    'label' => 'yt-dlp encontrado',
    'ok'    => $ytdlp_ok,
    'desc'  => $ytdlp_ok
        ? "Encontrado em: {$ytdlp_bin}" . ($ytdlp_version ? " (v{$ytdlp_version})" : '')
        : ($exec_ok
            ? 'yt-dlp não encontrado. Use o botão abaixo para instalar automaticamente.'
            : 'Não foi possível verificar (exec() desabilitado).'),
];

// 6. Pasta downloads/ com permissão de escrita
$dl_dir = __DIR__ . '/downloads';
if (!is_dir($dl_dir)) @mkdir($dl_dir, 0755, true);
$dl_ok = is_dir($dl_dir) && is_writable($dl_dir);
$checks[] = [
    'label' => 'Pasta downloads/ com escrita',
    'ok'    => $dl_ok,
    'desc'  => $dl_ok
        ? 'Pasta downloads/ existe e tem permissão de escrita.'
        : 'Sem permissão de escrita em downloads/. Execute via SSH: chmod 755 downloads/',
];

// 7. Pasta bin/ pode ser criada/escrita
$bin_writable = is_dir($BIN_DIR) ? is_writable($BIN_DIR) : is_writable(__DIR__);
$checks[] = [
    'label' => 'Pasta bin/ pode ser criada/escrita',
    'ok'    => $bin_writable,
    'desc'  => $bin_writable
        ? 'Pode salvar o binário yt-dlp em bin/.'
        : 'Sem permissão para criar/escrever em bin/. Execute via SSH: chmod 755 .',
];

$all_critical_ok = $exec_ok && $shell_ok && $zip_ok;
$ready           = $ytdlp_ok && $all_critical_ok;
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

<!-- Diagnóstico do servidor -->
<?php
$arch = detect_arch();
$bin_exists = file_exists($BIN_PATH);
$bin_size   = $bin_exists ? filesize($BIN_PATH) : 0;
$bin_magic  = $bin_exists ? bin2hex(substr((string)file_get_contents($BIN_PATH, false, null, 0, 4), 0, 4)) : '';
$is_elf     = $bin_magic === '7f454c46'; // \x7fELF

// Testa se exec funciona de verdade com um comando simples
$exec_test_out = []; $exec_test_rc = -1;
safe_exec('echo ok 2>/dev/null', $exec_test_out, $exec_test_rc);
$exec_works = $exec_test_rc === 0 && trim($exec_test_out[0] ?? '') === 'ok';

// Se o binário existir mas falhar, captura o erro real
$bin_error = '';
if ($bin_exists && $is_elf && !$ytdlp_ok) {
    $eo = []; $erc = -1;
    safe_exec(escapeshellarg($BIN_PATH) . ' --version 2>&1', $eo, $erc);
    $bin_error = implode(' ', $eo);
}
?>
<div class="bg-white rounded-xl shadow p-5 space-y-3">
    <h2 class="font-bold text-gray-800 flex items-center gap-2 text-sm">
        <i class="fa-solid fa-magnifying-glass text-gray-500"></i> Diagnóstico do servidor
    </h2>
    <div class="grid grid-cols-2 gap-2 text-xs font-mono">
        <span class="text-gray-500">Arquitetura:</span>
        <span class="text-gray-800 font-semibold"><?= htmlspecialchars($arch ?: 'não detectada') ?></span>

        <span class="text-gray-500">exec() realmente funciona:</span>
        <span class="<?= $exec_works ? 'text-green-600' : 'text-red-600' ?> font-semibold"><?= $exec_works ? 'sim' : 'não (bloqueado?)' ?></span>

        <?php if ($bin_exists): ?>
        <span class="text-gray-500">bin/yt-dlp existe:</span>
        <span class="text-gray-800">sim (<?= number_format($bin_size / 1024 / 1024, 1) ?> MB)</span>

        <span class="text-gray-500">Tipo do arquivo:</span>
        <span class="<?= $is_elf ? 'text-green-600' : 'text-red-600' ?>"><?= $is_elf ? 'ELF binário válido' : 'inválido (magic: ' . $bin_magic . ')' ?></span>
        <?php endif; ?>

        <?php if ($bin_error): ?>
        <span class="text-gray-500">Erro ao executar:</span>
        <span class="text-red-600 break-all"><?= htmlspecialchars($bin_error) ?></span>
        <?php endif; ?>
    </div>

    <?php if ($bin_exists && $is_elf && !$ytdlp_ok && str_contains($bin_error, 'ermission')): ?>
    <div class="bg-orange-50 border border-orange-200 rounded p-3 text-xs text-orange-800">
        <strong>noexec detectado:</strong> O diretório está montado sem permissão de execução.
        Tente mover o binário para <code>/tmp</code> via SSH:
        <code class="block mt-1 bg-orange-100 p-1 rounded">cp bin/yt-dlp /tmp/yt-dlp && chmod +x /tmp/yt-dlp && /tmp/yt-dlp --version</code>
    </div>
    <?php elseif ($bin_exists && $is_elf && !$ytdlp_ok): ?>
    <div class="bg-blue-50 border border-blue-200 rounded p-3 text-xs text-blue-800">
        <strong>Binário ELF presente mas não executa.</strong>
        Provável causa: arquitetura incompatível. Seu servidor é <strong><?= htmlspecialchars($arch) ?></strong>
        mas o binário baixado pode ser para outra arquitetura.
        Tente instalar via pip (abaixo) ou use o SSH.
    </div>
    <?php endif; ?>

    <?php if ($exec_ok && $arch): ?>
    <!-- Tentativa via Python/pip -->
    <?php
    $py3 = []; safe_exec('python3 --version 2>&1', $py3, $pyrc);
    $pip3 = []; safe_exec('pip3 --version 2>&1', $pip3, $piprc);
    $has_py3  = $pyrc  === 0;
    $has_pip3 = $piprc === 0;
    if ($has_py3 || $has_pip3): ?>
    <div class="border-t pt-3 mt-2">
        <p class="text-xs text-gray-500 mb-1">Python detectado no servidor:</p>
        <?php if ($has_py3): ?><p class="text-xs font-mono text-gray-700">python3: <?= htmlspecialchars(trim($py3[0] ?? '')) ?></p><?php endif; ?>
        <?php if ($has_pip3): ?><p class="text-xs font-mono text-gray-700">pip3: <?= htmlspecialchars(trim($pip3[0] ?? '')) ?></p><?php endif; ?>
        <form method="POST" class="mt-2">
            <input type="hidden" name="action" value="install_pip">
            <button type="submit" class="bg-purple-600 hover:bg-purple-700 text-white px-4 py-1.5 rounded text-xs font-semibold transition">
                <i class="fa-solid fa-python mr-1"></i> Instalar via pip3 install yt-dlp
            </button>
        </form>
    </div>
    <?php endif; ?>
    <?php endif; ?>
</div>

<!-- Instalar yt-dlp automaticamente -->
<?php if (!$ytdlp_ok && $all_critical_ok && $download_ok && $bin_writable): ?>
<div class="bg-white rounded-xl shadow p-5">
    <h2 class="font-bold text-gray-800 mb-2 flex items-center gap-2">
        <i class="fa-solid fa-download text-blue-500"></i>
        Instalar yt-dlp automaticamente
    </h2>
    <p class="text-sm text-gray-600 mb-4">
        Baixa o binário standalone direto do GitHub Releases e salva em
        <code class="bg-gray-100 px-1 rounded">bin/yt-dlp</code>.
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

<!-- Instruções SSH -->
<div class="bg-white rounded-xl shadow p-5 space-y-4">
    <h2 class="font-bold text-gray-800 flex items-center gap-2">
        <i class="fa-solid fa-terminal text-gray-600"></i>
        Instalar via SSH (alternativa manual)
    </h2>
    <p class="text-sm text-gray-600">
        Acesse o servidor via SSH (hPanel → Hospedagem → SSH Access) e execute:
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
    <p class="text-sm text-gray-600">
        Após executar, <a href="setup.php" class="text-blue-600 underline">recarregue esta página</a> para confirmar.
    </p>
</div>

<!-- Como habilitar exec() no Hostinger -->
<?php if (!$exec_ok || !$shell_ok): ?>
<div class="bg-orange-50 border border-orange-200 rounded-xl p-5 space-y-3">
    <h2 class="font-bold text-orange-800 flex items-center gap-2">
        <i class="fa-solid fa-triangle-exclamation"></i>
        Como habilitar exec() / shell_exec() no Hostinger
    </h2>
    <ol class="text-sm text-orange-900 space-y-2 list-decimal list-inside">
        <li>Acesse o painel Hostinger (hPanel)</li>
        <li>Vá em <strong>Hospedagem → Gerenciar → Configurações Avançadas → Configuração do PHP</strong></li>
        <li>Localize a diretiva <code class="bg-orange-100 px-1 rounded">disable_functions</code></li>
        <li>Remova <code class="bg-orange-100 px-1 rounded">exec</code> e <code class="bg-orange-100 px-1 rounded">shell_exec</code> da lista</li>
        <li>Salve e recarregue esta página</li>
    </ol>
    <p class="text-xs text-orange-700">
        Se não aparecer essa opção, seu plano pode ser muito restrito.
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
