<?php
// api/receber_video.php
// Recebe vídeo editado do worker e registra em fila_postagens
declare(strict_types=1);

ini_set('display_errors', 0);
ini_set('display_startup_errors', 0);
error_reporting(E_ALL);

header('Content-Type: application/json; charset=utf-8');

function jfail(int $code, string $msg): void {
    http_response_code($code);
    echo json_encode(["sucesso" => false, "mensagem" => $msg], JSON_UNESCAPED_UNICODE);
    exit;
}

require_once __DIR__ . '/_auth.php';
require_once __DIR__ . '/db.php';

if (!isset($conn) || !($conn instanceof mysqli)) {
    jfail(500, "Conexão MySQL inválida.");
}
if ($conn->connect_errno) {
    jfail(500, "Falha MySQL: " . $conn->connect_error);
}

// --- Inputs ---
$vmos_id = trim($_POST['vmos_id'] ?? '');
if ($vmos_id === '') {
    jfail(400, "vmos_id é obrigatório.");
}

// legenda é opcional (mantida por compatibilidade com schema)
$legenda = trim($_POST['legenda'] ?? '');

// --- Arquivo: aceita múltiplos nomes (compatibilidade) ---
$fileField = null;
foreach (['arquivo_mp4', 'arquivo', 'video'] as $k) {
    if (isset($_FILES[$k]) && is_array($_FILES[$k]) && ($_FILES[$k]['error'] ?? UPLOAD_ERR_NO_FILE) !== UPLOAD_ERR_NO_FILE) {
        $fileField = $k;
        break;
    }
}
if ($fileField === null) {
    jfail(400, "Arquivo não enviado. Use multipart com campo arquivo_mp4 (ou arquivo/video).");
}

$f = $_FILES[$fileField];
if (($f['error'] ?? UPLOAD_ERR_OK) !== UPLOAD_ERR_OK) {
    jfail(400, "Erro no upload: código " . (string)($f['error'] ?? 'desconhecido'));
}

$tmp = $f['tmp_name'] ?? '';
if (!is_string($tmp) || $tmp === '' || !is_uploaded_file($tmp)) {
    jfail(400, "Arquivo temporário inválido.");
}

// --- Nome final: vmos_id_time_rand.mp4 ---
$nome_final = $vmos_id . "_" . time() . "_" . bin2hex(random_bytes(4)) . ".mp4";

// --- Pasta /videos (um nível acima de /api) ---
$diretorio_salvar = dirname(__DIR__) . "/videos/";
if (!is_dir($diretorio_salvar)) {
    if (!mkdir($diretorio_salvar, 0755, true)) {
        jfail(500, "Falha ao criar a pasta /videos.");
    }
}

$caminho_completo = $diretorio_salvar . $nome_final;

if (!move_uploaded_file($tmp, $caminho_completo)) {
    jfail(500, "Erro ao mover o arquivo para /videos. Verifique permissões.");
}

// --- Insert DB (prepared) ---
$stmt = $conn->prepare("INSERT INTO fila_postagens (vmos_id, nome_arquivo, legenda, status) VALUES (?, ?, ?, 'pendente')");
if (!$stmt) {
    @unlink($caminho_completo);
    jfail(500, "Erro prepare DB: " . $conn->error);
}
$stmt->bind_param("sss", $vmos_id, $nome_final, $legenda);

if (!$stmt->execute()) {
    @unlink($caminho_completo);
    jfail(500, "Erro no banco de dados: " . $stmt->error);
}

$stmt->close();
$conn->close();

echo json_encode([
    "sucesso"       => true,
    "mensagem"      => "Upload recebido e agendado com sucesso.",
    "arquivo"       => $nome_final,
    "campo_arquivo" => $fileField
], JSON_UNESCAPED_UNICODE);
?>
