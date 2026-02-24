<?php
// api/marcar_status.php
// Atualiza status de um vídeo em fila_postagens (usado pelo Auto.js/mobile)

ini_set('display_errors', 0);
ini_set('display_startup_errors', 0);
error_reporting(E_ALL);

header('Content-Type: application/json; charset=utf-8');

require_once __DIR__ . '/_auth.php';
require_once __DIR__ . '/db.php';

if (!isset($conn) || !($conn instanceof mysqli)) {
    http_response_code(500);
    echo json_encode(["sucesso" => false, "mensagem" => "DB inválido."], JSON_UNESCAPED_UNICODE);
    exit;
}

$id_tarefa = (int)($_GET['id_tarefa'] ?? $_POST['id_tarefa'] ?? 0);
$status_novo = $_GET['status'] ?? $_POST['status'] ?? '';

if ($id_tarefa <= 0 || $status_novo === '') {
    http_response_code(400);
    echo json_encode(["sucesso" => false, "mensagem" => "Parâmetros incompletos. Envie id_tarefa e status."], JSON_UNESCAPED_UNICODE);
    exit;
}

// Sanitiza o status para evitar valores arbitrários
$status_validos = ['pendente', 'baixando', 'baixado', 'postado', 'concluido', 'erro'];
if (!in_array(strtolower($status_novo), $status_validos, true)) {
    http_response_code(400);
    echo json_encode(["sucesso" => false, "mensagem" => "Status inválido."], JSON_UNESCAPED_UNICODE);
    exit;
}
$status_novo = strtolower($status_novo);

// Se o status indica conclusão, apaga o arquivo físico para liberar espaço
$status_para_excluir = ['baixado', 'postado', 'concluido'];

if (in_array($status_novo, $status_para_excluir, true)) {
    $stmt_busca = $conn->prepare("SELECT nome_arquivo FROM fila_postagens WHERE id = ?");
    if ($stmt_busca) {
        $stmt_busca->bind_param("i", $id_tarefa);
        $stmt_busca->execute();
        $result = $stmt_busca->get_result();
        if ($result && $result->num_rows > 0) {
            $arquivo = $result->fetch_assoc()['nome_arquivo'];
            $caminho_video = dirname(__DIR__) . "/videos/" . basename($arquivo);
            if (file_exists($caminho_video)) {
                @unlink($caminho_video);
            }
        }
        $stmt_busca->close();
    }
}

// Atualiza o status no banco com prepared statement
$stmt = $conn->prepare("UPDATE fila_postagens SET status = ? WHERE id = ?");
if (!$stmt) {
    http_response_code(500);
    echo json_encode(["sucesso" => false, "mensagem" => "Erro ao preparar query: " . $conn->error], JSON_UNESCAPED_UNICODE);
    exit;
}

$stmt->bind_param("si", $status_novo, $id_tarefa);

if ($stmt->execute()) {
    echo json_encode(["sucesso" => true, "mensagem" => "Status atualizado para '$status_novo'."], JSON_UNESCAPED_UNICODE);
} else {
    http_response_code(500);
    echo json_encode(["sucesso" => false, "mensagem" => "Erro ao atualizar banco: " . $stmt->error], JSON_UNESCAPED_UNICODE);
}

$stmt->close();
$conn->close();
?>
