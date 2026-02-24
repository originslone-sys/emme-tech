<?php
// api/edicao_claim.php
// Claim (reservar) tarefas pendentes para um worker usando MySQLi ($conn)

ini_set('display_errors', 0);
ini_set('display_startup_errors', 0);
error_reporting(E_ALL);

header('Content-Type: application/json; charset=utf-8');

require_once __DIR__ . '/_auth.php';
require_once __DIR__ . '/db.php';

if (!isset($conn) || !($conn instanceof mysqli)) {
    http_response_code(500);
    echo json_encode(["sucesso" => false, "mensagem" => "DB inválido: \$conn não está definido (mysqli)."], JSON_UNESCAPED_UNICODE);
    exit;
}

$worker_id = $_POST['worker_id'] ?? $_GET['worker_id'] ?? 'worker';
$worker_id = preg_replace('/[^a-zA-Z0-9_\-]/', '', $worker_id);
if ($worker_id === '') $worker_id = 'worker';

$max = (int)($_POST['max'] ?? $_GET['max'] ?? 1);
if ($max < 1)  $max = 1;
if ($max > 10) $max = 10;

try {
    // InnoDB necessário para FOR UPDATE funcionar
    $conn->begin_transaction();

    // Seleciona pendentes com lock exclusivo para evitar que outro worker pegue a mesma tarefa
    $sqlSel = "
        SELECT id, vmos_id, legenda, bruto_arquivo
        FROM fila_edicao
        WHERE status = 'pendente'
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
        $conn->close();
        echo json_encode(["sucesso" => true, "tarefas" => []], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
        exit;
    }

    // Monta lista de IDs (já tipados como int acima)
    $ids    = array_map(fn($r) => (int)$r['id'], $rows);
    $idList = implode(",", $ids);

    // Atualiza status para 'baixando' somente nas IDs que ainda estão 'pendente'
    // (double-check de status garante idempotência mesmo com lock)
    $sqlUpd = "
        UPDATE fila_edicao
        SET status = 'baixando', worker_id = ?, updated_at = NOW()
        WHERE id IN ($idList) AND status = 'pendente'
    ";

    $stmt = $conn->prepare($sqlUpd);
    if (!$stmt) {
        throw new Exception("PREPARE falhou: " . $conn->error);
    }

    $stmt->bind_param("s", $worker_id);

    if (!$stmt->execute()) {
        throw new Exception("EXECUTE falhou: " . $stmt->error);
    }

    $affected = $stmt->affected_rows;
    $stmt->close();

    $conn->commit();

    // Se o UPDATE afetou menos rows do que o SELECT retornou, outra transação
    // ganhou a corrida em alguma tarefa (improvável com FOR UPDATE, mas defensivo).
    // Retornamos apenas as tarefas efetivamente assumidas.
    if ($affected < count($rows)) {
        // Consulta os IDs que realmente ficaram com este worker após o UPDATE
        $sqlCheck = "SELECT id, vmos_id, legenda, bruto_arquivo
                     FROM fila_edicao
                     WHERE id IN ($idList) AND worker_id = ? AND status = 'baixando'";
        $stmtChk = $conn->prepare($sqlCheck);
        if ($stmtChk) {
            $stmtChk->bind_param("s", $worker_id);
            $stmtChk->execute();
            $resChk = $stmtChk->get_result();
            $rows = [];
            while ($r = $resChk->fetch_assoc()) {
                $rows[] = $r;
            }
            $stmtChk->close();
        }
    }

    $conn->close();

    echo json_encode(["sucesso" => true, "tarefas" => $rows], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);

} catch (Throwable $e) {
    try { $conn->rollback(); } catch (Throwable $ignored) {}
    try { $conn->close();    } catch (Throwable $ignored) {}

    http_response_code(500);
    echo json_encode([
        "sucesso"  => false,
        "mensagem" => "Erro no claim: " . $e->getMessage()
    ], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
}
?>
