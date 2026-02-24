<?php
header('Content-Type: application/json');

$job_file = __DIR__ . '/edicao_job.json';

if (!file_exists($job_file)) {
  echo json_encode([
    "sucesso" => true,
    "job" => [
      "status" => "idle"
    ]
  ]);
  exit;
}

$raw = file_get_contents($job_file);
$job = json_decode($raw, true);

if (!$job) {
  echo json_encode(["sucesso" => false, "mensagem" => "Job inválido (JSON quebrado)."]);
  exit;
}

echo json_encode(["sucesso" => true, "job" => $job], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);