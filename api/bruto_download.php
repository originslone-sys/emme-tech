<?php
// api/bruto_download.php
// Faz download de um arquivo bruto salvo em /brutos

require_once __DIR__ . '/_auth.php';

$file = basename($_GET['file'] ?? '');

if ($file === '') {
    http_response_code(400);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode(["sucesso" => false, "mensagem" => "Parâmetro 'file' obrigatório."], JSON_UNESCAPED_UNICODE);
    exit;
}

$base = realpath(__DIR__ . '/../brutos');
if ($base === false) {
    http_response_code(500);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode(["sucesso" => false, "mensagem" => "Diretório brutos não encontrado."], JSON_UNESCAPED_UNICODE);
    exit;
}

$path = $base . DIRECTORY_SEPARATOR . $file;

// Garante que o arquivo está dentro de /brutos (evita path traversal residual)
if (strpos(realpath($path) ?: '', $base) !== 0) {
    http_response_code(400);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode(["sucesso" => false, "mensagem" => "Arquivo inválido."], JSON_UNESCAPED_UNICODE);
    exit;
}

if (!file_exists($path) || !is_file($path)) {
    http_response_code(404);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode(["sucesso" => false, "mensagem" => "Arquivo não encontrado."], JSON_UNESCAPED_UNICODE);
    exit;
}

$size = filesize($path);
if ($size === false) {
    http_response_code(500);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode(["sucesso" => false, "mensagem" => "Não foi possível obter tamanho do arquivo."], JSON_UNESCAPED_UNICODE);
    exit;
}

header('Content-Type: application/octet-stream');
header('Content-Disposition: attachment; filename="' . addslashes($file) . '"');
header('Content-Length: ' . $size);
header('Cache-Control: no-cache');

readfile($path);
?>
