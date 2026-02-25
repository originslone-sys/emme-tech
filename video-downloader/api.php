<?php
declare(strict_types=1);

$DOWNLOADS_DIR = __DIR__ . '/downloads';
if (!is_dir($DOWNLOADS_DIR)) @mkdir($DOWNLOADS_DIR, 0755, true);

// ── Helpers ──────────────────────────────────────────────────────────────────
function json_out(array $data, int $code = 200): never {
    http_response_code($code);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($data, JSON_UNESCAPED_UNICODE);
    exit;
}

/**
 * Retorna o comando completo (já escapado) para invocar o yt-dlp.
 * Ordem: local direto → /tmp (bypassa mmap restriction do /home) →
 *        python3+local → PATH → módulo Python.
 */
function find_ytdlp(): string {
    $local   = __DIR__ . '/bin/yt-dlp';
    $tmp_bin = '/tmp/ytdlp_' . substr(md5(__DIR__), 0, 8);

    // Auto-copia ELF para /tmp se necessário (tmpfs não tem restrição de mmap)
    if (file_exists($local) && is_file($local)) {
        if (!file_exists($tmp_bin) || filesize($tmp_bin) !== filesize($local)) {
            @copy($local, $tmp_bin);
            @chmod($tmp_bin, 0755);
        }
    }

    $py_paths = [
        'python3', '/usr/bin/python3', '/usr/local/bin/python3',
        '/usr/bin/python3.12', '/usr/bin/python3.11', '/usr/bin/python3.10', '/usr/bin/python3.9',
    ];

    $candidates = [
        [escapeshellarg($local),   escapeshellarg($local)],
        [escapeshellarg($tmp_bin), escapeshellarg($tmp_bin)],
    ];
    foreach ($py_paths as $py) {
        $candidates[] = [escapeshellarg($py) . ' ' . escapeshellarg($local),
                         escapeshellarg($py) . ' ' . escapeshellarg($local)];
    }
    $candidates[] = ['yt-dlp',                                'yt-dlp'];
    $candidates[] = [escapeshellarg('/usr/local/bin/yt-dlp'), escapeshellarg('/usr/local/bin/yt-dlp')];
    $candidates[] = [escapeshellarg('/usr/bin/yt-dlp'),       escapeshellarg('/usr/bin/yt-dlp')];
    foreach ($py_paths as $py) {
        $candidates[] = [escapeshellarg($py) . ' -m yt_dlp', escapeshellarg($py) . ' -m yt_dlp'];
    }

    foreach ($candidates as [$test, $cmd]) {
        $out = []; $rc = -1;
        exec($test . ' --version 2>/dev/null', $out, $rc);
        if ($rc === 0) return $cmd;
    }
    return '';
}

function safe_url(string $url): bool {
    if (!filter_var($url, FILTER_VALIDATE_URL)) return false;
    $host = parse_url($url, PHP_URL_HOST);
    if (!$host) return false;
    // Block local/private network access
    if (preg_match('/^(localhost|127\.|192\.168\.|10\.|172\.(1[6-9]|2\d|3[01])\.)/', $host)) return false;
    return true;
}

/**
 * Obtém URL de stream via Cobalt API — fallback para servidores sem yt-dlp.
 * Configuração opcional em bin/cobalt.json: {"url":"https://...","key":"..."}
 */
function cobalt_get_stream_url(string $video_url, string $quality = '720'): array {
    $cfg_file = __DIR__ . '/bin/cobalt.json';
    $cfg      = file_exists($cfg_file) ? (json_decode(file_get_contents($cfg_file), true) ?? []) : [];
    $api_base = rtrim($cfg['url'] ?? 'https://api.cobalt.tools', '/');
    $api_key  = $cfg['key'] ?? '';

    $headers = ['Accept: application/json', 'Content-Type: application/json'];
    if ($api_key !== '') $headers[] = 'Authorization: Api-Key ' . $api_key;

    $ch = curl_init($api_base . '/');
    curl_setopt_array($ch, [
        CURLOPT_POST           => true,
        CURLOPT_HTTPHEADER     => $headers,
        CURLOPT_POSTFIELDS     => json_encode([
            'url'               => $video_url,
            'videoQuality'      => $quality,
            'youtubeVideoCodec' => 'h264',
            'filenameStyle'     => 'basic',
            'downloadMode'      => 'auto',
        ]),
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT        => 30,
        CURLOPT_SSL_VERIFYPEER => true,
    ]);
    $resp = curl_exec($ch);
    $http = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $cerr = curl_error($ch);
    curl_close($ch);

    if ($cerr)         return ['ok' => false, 'error' => 'cURL: ' . $cerr];
    if ($http === 401) return ['ok' => false, 'error' => 'cobalt_auth_required'];
    if ($http !== 200) return ['ok' => false, 'error' => "Cobalt HTTP {$http}: " . substr($resp ?? '', 0, 150)];

    $data   = json_decode($resp, true);
    if (!$data) return ['ok' => false, 'error' => 'Resposta inválida da Cobalt API'];

    $status = $data['status'] ?? '';
    if ($status === 'error') return ['ok' => false, 'error' => $data['error']['code'] ?? 'cobalt_error'];
    if (in_array($status, ['tunnel', 'redirect'], true) && !empty($data['url'])) {
        return ['ok' => true, 'url' => $data['url'], 'status' => $status, 'filename' => $data['filename'] ?? null];
    }
    if ($status === 'picker') {
        $items = $data['picker'] ?? [];
        if (!empty($items[0]['url'])) {
            return ['ok' => true, 'url' => $items[0]['url'], 'status' => 'picker', 'filename' => $items[0]['filename'] ?? null];
        }
    }
    return ['ok' => false, 'error' => "Cobalt: status inesperado '{$status}'"];
}

/**
 * Baixa uma URL remota diretamente para o disco via cURL (streaming — não carrega em memória).
 */
function curl_save_to_file(string $url, string $dest, int $timeout = 300): array {
    $fp = @fopen($dest, 'wb');
    if (!$fp) return ['ok' => false, 'error' => 'Não foi possível criar arquivo de destino'];

    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_FILE           => $fp,
        CURLOPT_FOLLOWLOCATION => true,
        CURLOPT_MAXREDIRS      => 5,
        CURLOPT_TIMEOUT        => $timeout,
        CURLOPT_SSL_VERIFYPEER => true,
        CURLOPT_USERAGENT      => 'Mozilla/5.0 (compatible; VideoDownloader/1.0)',
    ]);
    curl_exec($ch);
    $http = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $size = (int) curl_getinfo($ch, CURLINFO_SIZE_DOWNLOAD);
    $cerr = curl_error($ch);
    curl_close($ch);
    fclose($fp);

    if ($cerr || $http < 200 || $http >= 300 || $size < 1000) {
        @unlink($dest);
        return ['ok' => false, 'error' => $cerr ?: "HTTP {$http}, {$size} bytes recebidos"];
    }
    return ['ok' => true, 'size' => $size];
}

$action = $_GET['action'] ?? $_POST['action'] ?? '';

// ── check: verifica yt-dlp ────────────────────────────────────────────────────
if ($action === 'check') {
    $bin = find_ytdlp();
    if ($bin === '') {
        json_out(['ok' => false, 'error' => 'yt-dlp não encontrado.', 'cobalt_mode' => true]);
    }
    exec($bin . ' --version 2>/dev/null', $ver);
    json_out(['ok' => true, 'path' => $bin, 'version' => trim($ver[0] ?? ''), 'cobalt_mode' => false]);
}

// ── fetch_videos: lista vídeos de um perfil ───────────────────────────────────
if ($action === 'fetch_videos') {
    $url   = trim($_POST['url'] ?? '');
    $start = max(1, (int)($_POST['start'] ?? 1));
    $count = min(100, max(1, (int)($_POST['count'] ?? 100)));

    if (!safe_url($url)) json_out(['ok' => false, 'error' => 'URL inválida ou não permitida.']);

    $bin = find_ytdlp();
    if ($bin === '') json_out(['ok' => false, 'error' => 'A navegação de perfis requer yt-dlp, indisponível neste servidor. Use o modo de URL direta abaixo para baixar vídeos individuais via Cobalt API.']);

    $end = $start + $count - 1;
    $cmd = $bin
         . ' --flat-playlist --dump-single-json'
         . ' --no-warnings --ignore-errors'
         . ' --playlist-start ' . (int)$start
         . ' --playlist-end '   . (int)$end
         . ' ' . escapeshellarg($url)
         . ' 2>/dev/null';

    $raw = shell_exec($cmd);
    if (!$raw) json_out(['ok' => false, 'error' => 'Nenhum resultado. Verifique se a URL é de um perfil público e suportado (TikTok, Instagram, Facebook).']);

    $data = json_decode($raw, true);
    if (!$data) json_out(['ok' => false, 'error' => 'Resposta inválida do yt-dlp. A URL pode não ser um perfil/playlist suportado.']);

    $entries = $data['entries'] ?? [];
    // Filtra entradas nulas (vídeos privados/removidos)
    $entries = array_values(array_filter($entries, fn($e) => !empty($e)));

    $videos = array_map(function (array $e): array {
        $thumb = $e['thumbnail'] ?? '';
        if (!$thumb && !empty($e['thumbnails'])) {
            // Pega thumbnail de maior resolução
            $thumbs = $e['thumbnails'];
            usort($thumbs, fn($a, $b) => (int)($b['width'] ?? 0) - (int)($a['width'] ?? 0));
            $thumb = $thumbs[0]['url'] ?? '';
        }
        return [
            'id'       => $e['id'] ?? '',
            'title'    => $e['title'] ?? $e['id'] ?? 'Sem título',
            'url'      => $e['webpage_url'] ?? $e['url'] ?? '',
            'thumb'    => $thumb,
            'duration' => (int)($e['duration'] ?? 0),
            'views'    => (int)($e['view_count'] ?? 0),
            'date'     => $e['upload_date'] ?? '',
        ];
    }, $entries);

    json_out([
        'ok'       => true,
        'videos'   => $videos,
        'fetched'  => count($videos),
        'start'    => $start,
        'has_more' => count($videos) >= $count,
        'profile'  => $data['title'] ?? $data['uploader'] ?? '',
        'platform' => strtolower($data['extractor'] ?? $data['extractor_key'] ?? ''),
    ]);
}

// ── download: baixa vídeos e emite progresso via SSE ─────────────────────────
if ($action === 'download') {
    $raw_urls = isset($_POST['urls']) && is_array($_POST['urls']) ? $_POST['urls'] : [];

    $urls = array_values(array_filter(array_map('trim', $raw_urls), 'safe_url'));
    if (empty($urls)) json_out(['ok' => false, 'error' => 'Nenhuma URL válida recebida.']);

    $bin         = find_ytdlp();
    $cobalt_mode = ($bin === ''); // usa Cobalt API quando yt-dlp não está disponível

    // Cria diretório do job
    $job_id  = date('Ymd_His') . '_' . bin2hex(random_bytes(4));
    $job_dir = $DOWNLOADS_DIR . '/' . $job_id;
    @mkdir($job_dir, 0755, true);

    // SSE headers
    header('Content-Type: text/event-stream; charset=utf-8');
    header('Cache-Control: no-cache');
    header('X-Accel-Buffering: no');
    set_time_limit(0);
    if (ob_get_level()) ob_end_flush();

    $emit = function (array $payload) {
        echo 'data: ' . json_encode($payload, JSON_UNESCAPED_UNICODE) . "\n\n";
        flush();
    };

    $total  = count($urls);
    $done   = 0;
    $failed = 0;

    $emit(['type' => 'start', 'total' => $total, 'job' => $job_id,
           'mode' => $cobalt_mode ? 'cobalt' : 'ytdlp']);

    foreach ($urls as $i => $url) {
        $n = $i + 1;
        $emit(['type' => 'progress', 'done' => $done, 'total' => $total, 'n' => $n,
               'msg' => "Baixando vídeo {$n} de {$total}..."]);

        if ($cobalt_mode) {
            // ── Cobalt API ────────────────────────────────────────────────────
            $cobalt = cobalt_get_stream_url($url);
            if (!$cobalt['ok']) {
                $failed++;
                $err_msg = ($cobalt['error'] === 'cobalt_auth_required')
                    ? 'Cobalt API requer chave de API. Configure em Setup → Cobalt API.'
                    : 'Cobalt: ' . $cobalt['error'];
                $emit(['type' => 'error', 'done' => $done, 'total' => $total, 'n' => $n,
                       'msg' => "Falha no vídeo {$n}: {$err_msg}"]);
                continue;
            }

            $raw_name = $cobalt['filename'] ?? ('video_' . $n . '.mp4');
            $fname    = preg_replace('/[^\w.\-]/', '_', $raw_name);
            if (!preg_match('/\.(mp4|webm|mov|mkv)$/i', $fname)) $fname .= '.mp4';
            $dest = $job_dir . '/' . $fname;

            $dl = curl_save_to_file($cobalt['url'], $dest);
            if ($dl['ok']) {
                $done++;
                $emit(['type' => 'done_one', 'done' => $done, 'total' => $total, 'n' => $n]);
            } else {
                $failed++;
                $emit(['type' => 'error', 'done' => $done, 'total' => $total, 'n' => $n,
                       'msg' => "Falha no download do vídeo {$n}: " . $dl['error']]);
            }
        } else {
            // ── yt-dlp ────────────────────────────────────────────────────────
            $out_tpl = $job_dir . '/%(title).80B.%(ext)s';
            $cmd = $bin
                 . ' --no-playlist --no-warnings --ignore-errors'
                 . ' --merge-output-format mp4'
                 . ' -o ' . escapeshellarg($out_tpl)
                 . ' ' . escapeshellarg($url)
                 . ' 2>&1';

            $output = [];
            exec($cmd, $output, $rc);

            if ($rc === 0) {
                $done++;
                $emit(['type' => 'done_one', 'done' => $done, 'total' => $total, 'n' => $n]);
            } else {
                $failed++;
                $err_line = '';
                foreach (array_reverse($output) as $line) {
                    if (str_contains($line, 'ERROR')) { $err_line = $line; break; }
                }
                $emit(['type' => 'error', 'done' => $done, 'total' => $total, 'n' => $n,
                       'msg' => "Falha no vídeo {$n}" . ($err_line ? ": " . substr($err_line, 0, 120) : '.')]);
            }
        }
    }

    if ($done > 0) {
        $emit(['type' => 'zipping', 'done' => $done, 'total' => $total]);

        $zip_path = $DOWNLOADS_DIR . '/' . $job_id . '.zip';
        $zip = new ZipArchive();
        $zip->open($zip_path, ZipArchive::CREATE | ZipArchive::OVERWRITE);
        foreach (glob($job_dir . '/*') as $file) {
            if (is_file($file)) $zip->addFile($file, basename($file));
        }
        $zip->close();

        foreach (glob($job_dir . '/*') as $file) @unlink($file);
        @rmdir($job_dir);

        $emit(['type' => 'complete', 'done' => $done, 'total' => $total,
               'failed' => $failed, 'job' => $job_id,
               'size_mb' => round(filesize($zip_path) / 1048576, 1)]);
    } else {
        $emit(['type' => 'failed', 'msg' => 'Nenhum vídeo foi baixado com sucesso.']);
    }

    exit;
}

// ── zip: serve o ZIP pronto ───────────────────────────────────────────────────
if ($action === 'zip') {
    $job_id = preg_replace('/[^a-zA-Z0-9_]/', '', $_GET['job'] ?? '');
    if (!$job_id) { http_response_code(400); exit; }

    $zip_path = $DOWNLOADS_DIR . '/' . $job_id . '.zip';
    if (!file_exists($zip_path)) { http_response_code(404); echo 'ZIP não encontrado ou já baixado.'; exit; }

    header('Content-Type: application/zip');
    header('Content-Disposition: attachment; filename="videos_' . $job_id . '.zip"');
    header('Content-Length: ' . filesize($zip_path));
    header('Cache-Control: no-cache, no-store');
    readfile($zip_path);
    @unlink($zip_path);
    exit;
}

json_out(['ok' => false, 'error' => 'Ação desconhecida.'], 400);
