<?php
header('Content-Type: application/json');

$job_file = __DIR__ . '/edicao_job.json';

if (!isset($_POST['nonce']) || !isset($_POST['status'])) {
  echo json_encode(["sucesso" => false, "mensagem" => "Faltam parâmetros: nonce, status"]);
  exit;
}

if (!file_exists($job_file)) {
  echo json_encode(["sucesso" => false, "mensagem" => "Job não existe."]);
  exit;
}

$job = json_decode(file_get_contents($job_file), true);
if (!$job) {
  echo json_encode(["sucesso" => false, "mensagem" => "Job inválido."]);
  exit;
}

$nonce = $_POST['nonce'];
if (!isset($job['nonce']) || $job['nonce'] !== $nonce) {
  echo json_encode(["sucesso" => false, "mensagem" => "Nonce inválido (job diferente do que você puxou)."]);
  exit;
}

$status = $_POST['status']; // running|done|error|idle
$job['status'] = $status;

$job['result_ok'] = isset($_POST['result_ok']) ? (int)$_POST['result_ok'] : ($job['result_ok'] ?? 0);
$job['result_fail'] = isset($_POST['result_fail']) ? (int)$_POST['result_fail'] : ($job['result_fail'] ?? 0);
$job['message'] = isset($_POST['message']) ? (string)$_POST['message'] : ($job['message'] ?? "");

$job['updated_at'] = date('c');

file_put_contents($job_file, json_encode($job, JSON_PRETTY_PRINT|JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES));

echo json_encode(["sucesso" => true, "job" => $job], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);