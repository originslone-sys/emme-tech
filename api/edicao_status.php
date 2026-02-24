<?php
// api/edicao_status.php
// Atualiza status de uma tarefa da fila_edicao (mysqli/$conn)

ini_set('display_errors', 0);
ini_set('display_startup_errors', 0);
error_reporting(E_ALL);

header('Content-Type: application/json; charset=utf-8');

require_once __DIR__ . '/_auth.php';
require_once __DIR__ . '/db.php';

if (!isset($conn) || !($conn instanceof mysqli)) {
    http_response_code(500);
    echo json_encode(["sucesso"=>false,"mensagem"=>"DB inválido: \$conn não está definido (mysqli)."], JSON_UNESCAPED_UNICODE);
    exit;
}

$id = (int)($_POST['id'] ?? $_GET['id'] ?? 0);
$status = $_POST['status'] ?? $_GET['status'] ?? '';
$worker_id = $_POST['worker_id'] ?? $_GET['worker_id'] ?? null;
$erro_msg = $_POST['erro_msg'] ?? $_GET['erro_msg'] ?? null;

$valid = ['pendente','baixando','editando','concluido','erro'];

if ($id <= 0 || !in_array($status, $valid, true)) {
    http_response_code(400);
    echo json_encode(["sucesso"=>false,"mensagem"=>"Parâmetros inválidos (id/status)."], JSON_UNESCAPED_UNICODE);
    exit;
}

if ($worker_id !== null) {
    $worker_id = preg_replace('/[^a-zA-Z0-9_\-]/', '', $worker_id);
    if ($worker_id === '') $worker_id = null;
}

try {
    $sql = "UPDATE fila_edicao SET status=?, worker_id=?, erro_msg=? WHERE id=?";
    $stmt = $conn->prepare($sql);
    if (!$stmt) throw new Exception("PREPARE falhou: " . $conn->error);

    // s = string, i = int; worker_id e erro_msg podem ser null
    $stmt->bind_param("sssi", $status, $worker_id, $erro_msg, $id);

    if (!$stmt->execute()) {
        throw new Exception("EXECUTE falhou: " . $stmt->error);
    }

    $stmt->close();

    echo json_encode(["sucesso"=>true], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
} catch (Throwable $e) {
    http_response_code(500);
    echo json_encode(["sucesso"=>false,"mensagem"=>"Erro ao atualizar status: ".$e->getMessage()], JSON_UNESCAPED_UNICODE);
}