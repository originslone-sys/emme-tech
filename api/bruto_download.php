<?php
// api/bruto_download.php
// Faz download de um bruto salvo em /brutos

require_once __DIR__ . '/_auth.php';

$file = basename($_GET['file'] ?? '');
if ($file === '') {
    http_response_code(400);
    echo "file obrigatório";
    exit;
}

$path = realpath(__DIR__ . '/../') . '/brutos/' . $file;
if (!file_exists($path)) {
    http_response_code(404);
    echo "não encontrado";
    exit;
}

// Headers para download
header('Content-Type: application/octet-stream');
header('Content-Disposition: attachment; filename="'.$file.'"');
header('Content-Length: ' . filesize($path));
readfile($path);