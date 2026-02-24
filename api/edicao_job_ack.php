<?php
// api/edicao_job_ack.php
// Atualiza status do job após execução do worker local

header('Content-Type: application/json; charset=utf-8');

require_once __DIR__ . '/_auth.php';

$job_file = __DIR__ . '/edicao_job.json';

$nonce  = $_POST['nonce']  ?? '';
$status = $_POST['status'] ?? '';

if ($nonce === '' || $status === '') {
    http_response_code(400);
    echo json_encode(["sucesso" => false, "mensagem" => "Faltam parâmetros: nonce, status"], JSON_UNESCAPED_UNICODE);
    exit;
}

// Valida status permitidos
$status_validos = ['running', 'done', 'error', 'idle'];
if (!in_array($status, $status_validos, true)) {
    http_response_code(400);
    echo json_encode(["sucesso" => false, "mensagem" => "Status inválido. Use: running|done|error|idle"], JSON_UNESCAPED_UNICODE);
    exit;
}

if (!file_exists($job_file)) {
    http_response_code(404);
    echo json_encode(["sucesso" => false, "mensagem" => "Job não existe."], JSON_UNESCAPED_UNICODE);
    exit;
}

$raw = file_get_contents($job_file);
$job = json_decode($raw, true);

if (!is_array($job) || json_last_error() !== JSON_ERROR_NONE) {
    http_response_code(500);
    echo json_encode(["sucesso" => false, "mensagem" => "Job inválido (JSON corrompido)."], JSON_UNESCAPED_UNICODE);
    exit;
}

if (!isset($job['nonce']) || $job['nonce'] !== $nonce) {
    http_response_code(409);
    echo json_encode(["sucesso" => false, "mensagem" => "Nonce inválido (job diferente do que você puxou)."], JSON_UNESCAPED_UNICODE);
    exit;
}

$job['status']      = $status;
$job['result_ok']   = isset($_POST['result_ok'])   ? (int)$_POST['result_ok']   : ($job['result_ok']   ?? 0);
$job['result_fail'] = isset($_POST['result_fail']) ? (int)$_POST['result_fail'] : ($job['result_fail'] ?? 0);
$job['message']     = isset($_POST['message'])     ? (string)$_POST['message']  : ($job['message']     ?? '');
$job['updated_at']  = date('c');

if (file_put_contents($job_file, json_encode($job, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES)) === false) {
    http_response_code(500);
    echo json_encode(["sucesso" => false, "mensagem" => "Falha ao salvar job."], JSON_UNESCAPED_UNICODE);
    exit;
}

echo json_encode(["sucesso" => true, "job" => $job], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
?>
