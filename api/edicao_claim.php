<?php
// api/edicao_claim.php
// Claim (reservar) tarefas pendentes para um worker usando MySQLi ($conn)

ini_set('display_errors', 0);
ini_set('display_startup_errors', 0);
error_reporting(E_ALL);

header('Content-Type: application/json; charset=utf-8');

// 1) Auth
require_once __DIR__ . '/_auth.php';

// 2) DB (MySQLi) - precisa expor $conn
require_once __DIR__ . '/db.php';

// 3) Validar conexão
if (!isset($conn) || !($conn instanceof mysqli)) {
    http_response_code(500);
    echo json_encode(["sucesso" => false, "mensagem" => "DB inválido: \$conn não está definido (mysqli)."], JSON_UNESCAPED_UNICODE);
    exit;
}

// 4) Parâmetros
$worker_id = $_POST['worker_id'] ?? $_GET['worker_id'] ?? 'worker';
$worker_id = preg_replace('/[^a-zA-Z0-9_\-]/', '', $worker_id);
if ($worker_id === '') $worker_id = 'worker';

$max = (int)($_POST['max'] ?? $_GET['max'] ?? 1);
if ($max < 1) $max = 1;
if ($max > 10) $max = 10;

try {
    // IMPORTANTE: sua tabela precisa ser InnoDB para FOR UPDATE funcionar
    $conn->begin_transaction();

    // 5) Seleciona pendentes com lock (FOR UPDATE)
    // LIMIT não pode ser bindado como parâmetro em alguns setups, então usamos int sanitizado ($max)
    $sqlSel = "
        SELECT id, vmos_id, legenda, bruto_arquivo
        FROM fila_edicao
        WHERE status='pendente'
        ORDER BY id ASC
        LIMIT $max
        FOR UPDATE
    ";

    $res = $conn->query($sqlSel);
    if ($res === false) {
        throw new Exception("SELECT falhou: " . $conn->error);
    }

    $rows = [];
    while ($row = $res->fetch_assoc()) {
        $rows[] = $row;
    }

    if (count($rows) === 0) {
        $conn->commit();
        echo json_encode(["sucesso" => true, "tarefas" => []], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
        exit;
    }

    // 6) Atualiza status para 'baixando' nas IDs selecionadas
    $ids = [];
    foreach ($rows as $r) {
        $ids[] = (int)$r['id'];
    }
    $idList = implode(",", $ids);

    // UPDATE com bind apenas no worker_id
    $sqlUpd = "
        UPDATE fila_edicao
        SET status='baixando', worker_id=?
        WHERE id IN ($idList) AND status='pendente'
    ";

    $stmt = $conn->prepare($sqlUpd);
    if (!$stmt) {
        throw new Exception("PREPARE falhou: " . $conn->error);
    }

    $stmt->bind_param("s", $worker_id);

    if (!$stmt->execute()) {
        throw new Exception("EXECUTE falhou: " . $stmt->error);
    }

    $stmt->close();

    // 7) Commit
    $conn->commit();

    // 8) Resposta
    echo json_encode(["sucesso" => true, "tarefas" => $rows], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
} catch (Throwable $e) {
    // rollback se possível
    try { $conn->rollback(); } catch (Throwable $e2) {}

    http_response_code(500);
    echo json_encode([
        "sucesso" => false,
        "mensagem" => "Erro no claim: " . $e->getMessage()
    ], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
}