<?php
// api/bruto_delete.php
// Deleta arquivo bruto em /brutos

header('Content-Type: application/json; charset=utf-8');

require_once __DIR__ . '/_auth.php';

$file = basename($_POST['file'] ?? $_GET['file'] ?? '');
if ($file === '') {
    http_response_code(400);
    echo json_encode(["sucesso" => false, "mensagem" => "Parâmetro 'file' obrigatório."], JSON_UNESCAPED_UNICODE);
    exit;
}

$base = realpath(__DIR__ . '/../brutos');
if ($base === false) {
    // Pasta não existe, nada a deletar
    echo json_encode(["sucesso" => true, "deletado" => false, "mensagem" => "Diretório brutos não existe."], JSON_UNESCAPED_UNICODE);
    exit;
}

$path = $base . DIRECTORY_SEPARATOR . $file;

// Garante que o arquivo está dentro de /brutos (evita path traversal residual)
$realPath = realpath($path);
if ($realPath === false || strpos($realPath, $base) !== 0) {
    http_response_code(400);
    echo json_encode(["sucesso" => false, "mensagem" => "Arquivo inválido."], JSON_UNESCAPED_UNICODE);
    exit;
}

if (!file_exists($realPath)) {
    // Arquivo já foi deletado — operação idempotente
    echo json_encode(["sucesso" => true, "deletado" => false, "mensagem" => "Arquivo não encontrado (já removido)."], JSON_UNESCAPED_UNICODE);
    exit;
}

if (@unlink($realPath)) {
    echo json_encode(["sucesso" => true, "deletado" => true], JSON_UNESCAPED_UNICODE);
} else {
    http_response_code(500);
    echo json_encode(["sucesso" => false, "mensagem" => "Falha ao deletar arquivo. Verifique permissões."], JSON_UNESCAPED_UNICODE);
}
?>
