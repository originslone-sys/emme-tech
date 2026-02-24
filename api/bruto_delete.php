<?php
// api/bruto_delete.php
// Deleta arquivo bruto em /brutos

header('Content-Type: application/json; charset=utf-8');

require_once __DIR__ . '/_auth.php';

$file = basename($_POST['file'] ?? $_GET['file'] ?? '');
if ($file === '') {
    http_response_code(400);
    echo json_encode(["sucesso"=>false,"mensagem"=>"file obrigatório"], JSON_UNESCAPED_UNICODE);
    exit;
}

$path = realpath(__DIR__ . '/../') . '/brutos/' . $file;
if (file_exists($path)) {
    @unlink($path);
}

echo json_encode(["sucesso"=>true], JSON_UNESCAPED_UNICODE);