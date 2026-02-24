<?php
// api/edicao_list.php
// Lista tarefas da fila_edicao (mysqli/$conn)

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

$status = $_GET['status'] ?? '';
$limit = (int)($_GET['limit'] ?? 200);
if ($limit < 1) $limit = 1;
if ($limit > 500) $limit = 500;

$where = "";
$params = [];
$types = "";

if ($status !== '') {
    $valid = ['pendente','baixando','editando','concluido','erro'];
    if (!in_array($status, $valid, true)) {
        http_response_code(400);
        echo json_encode(["sucesso"=>false,"mensagem"=>"status inválido"], JSON_UNESCAPED_UNICODE);
        exit;
    }
    $where = "WHERE status=?";
    $params[] = $status;
    $types .= "s";
}

try {
    $sql = "SELECT id, vmos_id, legenda, bruto_arquivo, status, worker_id, erro_msg, created_at, updated_at
            FROM fila_edicao
            $where
            ORDER BY id DESC
            LIMIT $limit";

    $stmt = $conn->prepare($sql);
    if (!$stmt) throw new Exception("PREPARE falhou: " . $conn->error);

    if ($types !== "") {
        $stmt->bind_param($types, ...$params);
    }

    if (!$stmt->execute()) throw new Exception("EXECUTE falhou: " . $stmt->error);

    $res = $stmt->get_result();
    $rows = [];
    while ($row = $res->fetch_assoc()) {
        $rows[] = $row;
    }
    $stmt->close();

    echo json_encode(["sucesso"=>true,"tarefas"=>$rows], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
} catch (Throwable $e) {
    http_response_code(500);
    echo json_encode(["sucesso"=>false,"mensagem"=>"Erro ao listar: ".$e->getMessage()], JSON_UNESCAPED_UNICODE);
}