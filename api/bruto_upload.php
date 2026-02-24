<?php
// api/bruto_upload.php
// Recebe um vídeo bruto (upload) e cria tarefa na fila_edicao (mysqli/$conn)

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

$vmos_id = $_POST['vmos_id'] ?? '';
$vmos_id = preg_replace('/[^a-zA-Z0-9_]/', '', $vmos_id);

$legenda = $_POST['legenda'] ?? '';

if ($vmos_id === '' || trim($legenda) === '' || !isset($_FILES['arquivo_mp4'])) {
    http_response_code(400);
    echo json_encode(["sucesso"=>false,"mensagem"=>"Faltam campos: vmos_id, legenda, arquivo_mp4"], JSON_UNESCAPED_UNICODE);
    exit;
}

$dir = realpath(__DIR__ . '/../') . '/brutos';
if (!is_dir($dir)) {
    if (!mkdir($dir, 0777, true)) {
        http_response_code(500);
        echo json_encode(["sucesso"=>false,"mensagem"=>"Falha ao criar pasta brutos"], JSON_UNESCAPED_UNICODE);
        exit;
    }
}

$orig = $_FILES['arquivo_mp4']['name'] ?? 'video.mp4';
$ext = strtolower(pathinfo($orig, PATHINFO_EXTENSION));
if ($ext === '') $ext = 'mp4';

// Gera nome único (inclui vmos_id)
$nome = $vmos_id . "_raw_" . time() . "_" . bin2hex(random_bytes(4)) . "." . $ext;
$dest = $dir . "/" . $nome;

if (!is_uploaded_file($_FILES['arquivo_mp4']['tmp_name'])) {
    http_response_code(400);
    echo json_encode(["sucesso"=>false,"mensagem"=>"Upload inválido (tmp_name)"], JSON_UNESCAPED_UNICODE);
    exit;
}

if (!move_uploaded_file($_FILES['arquivo_mp4']['tmp_name'], $dest)) {
    http_response_code(500);
    echo json_encode(["sucesso"=>false,"mensagem"=>"Falha ao salvar bruto em brutos/"], JSON_UNESCAPED_UNICODE);
    exit;
}

try {
    $sql = "INSERT INTO fila_edicao (vmos_id, legenda, bruto_arquivo, status) VALUES (?, ?, ?, 'pendente')";
    $stmt = $conn->prepare($sql);
    if (!$stmt) throw new Exception("PREPARE falhou: " . $conn->error);

    $stmt->bind_param("sss", $vmos_id, $legenda, $nome);

    if (!$stmt->execute()) {
        throw new Exception("EXECUTE falhou: " . $stmt->error);
    }

    $id = $stmt->insert_id;
    $stmt->close();

    echo json_encode([
        "sucesso" => true,
        "mensagem" => "Bruto recebido e tarefa criada",
        "tarefa_id" => $id,
        "bruto" => $nome
    ], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
} catch (Throwable $e) {
    http_response_code(500);
    echo json_encode(["sucesso"=>false,"mensagem"=>"Erro ao inserir tarefa: ".$e->getMessage()], JSON_UNESCAPED_UNICODE);
}