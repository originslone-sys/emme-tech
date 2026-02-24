<?php
// api/edicao_job_get.php
// Retorna o job atual para o worker local

header('Content-Type: application/json; charset=utf-8');

require_once __DIR__ . '/_auth.php';

$job_file = __DIR__ . '/edicao_job.json';

if (!file_exists($job_file)) {
    echo json_encode([
        "sucesso" => true,
        "job"     => ["status" => "idle"]
    ], JSON_UNESCAPED_UNICODE);
    exit;
}

$raw = file_get_contents($job_file);
$job = json_decode($raw, true);

if (!is_array($job) || json_last_error() !== JSON_ERROR_NONE) {
    http_response_code(500);
    echo json_encode(["sucesso" => false, "mensagem" => "Job inválido (JSON corrompido)."], JSON_UNESCAPED_UNICODE);
    exit;
}

echo json_encode(["sucesso" => true, "job" => $job], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
?>
