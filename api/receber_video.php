<?php
// /public_html/api/receber_video.php
declare(strict_types=1);

header('Content-Type: application/json; charset=utf-8');

function jfail(int $code, string $msg, array $extra = []): void {
    http_response_code($code);
    echo json_encode(array_merge([
        "sucesso" => false,
        "mensagem" => $msg,
    ], $extra), JSON_UNESCAPED_UNICODE);
    exit;
}

// --- Auth (recomendado) ---
$authFile = __DIR__ . '/_auth.php';
if (file_exists($authFile)) {
    require_once $authFile;
    if (function_exists('require_api_key')) {
        require_api_key();
    }
}

// --- DB (MySQLi) ---
$dbFile = __DIR__ . '/db.php';
if (!file_exists($dbFile)) {
    // fallback legado, se ainda existir
    $legacy = __DIR__ . '/conexao.php';
    if (file_exists($legacy)) {
        require_once $legacy;
    } else {
        jfail(500, "Arquivo de conexão não encontrado (db.php/conexao.php).");
    }
} else {
    require_once $dbFile;
}

if (!isset($conn) || !($conn instanceof mysqli)) {
    jfail(500, "Conexão MySQL inválida: variável $conn não definida (mysqli).");
}
if ($conn->connect_errno) {
    jfail(500, "Falha MySQL: " . $conn->connect_error);
}

// --- Inputs ---
$vmos_id = $_POST['vmos_id'] ?? '';
if (!is_string($vmos_id) || trim($vmos_id) === '') {
    jfail(400, "vmos_id é obrigatório.");
}
$vmos_id = trim($vmos_id);

// legenda é opcional (mantida por compatibilidade com schema)
$legenda = $_POST['legenda'] ?? '';
if (!is_string($legenda)) $legenda = '';
$legenda = trim($legenda);

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
    jfail(400, "Erro no upload: " . (string)($f['error'] ?? 'desconhecido'));
}

$tmp = $f['tmp_name'] ?? '';
if (!is_string($tmp) || $tmp === '' || !is_uploaded_file($tmp)) {
    jfail(400, "Arquivo temporário inválido.");
}

// --- Nome final: vmos_id_time_rand.mp4 ---
try {
    $rand = bin2hex(random_bytes(4));
} catch (Throwable $e) {
    $rand = bin2hex(openssl_random_pseudo_bytes(4) ?: "abcd");
}
$nome_final = $vmos_id . "_" . time() . "_" . $rand . ".mp4";

// --- Pasta /videos (um nível acima de /api) ---
$diretorio_salvar = dirname(__DIR__) . "/videos/";
if (!file_exists($diretorio_salvar)) {
    if (!mkdir($diretorio_salvar, 0755, true)) {
        jfail(500, "Falha ao criar a pasta /videos.");
    }
}

$caminho_completo = $diretorio_salvar . $nome_final;

// move uploaded file
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

echo json_encode([
    "sucesso" => true,
    "mensagem" => "Upload recebido e agendado com sucesso.",
    "arquivo" => $nome_final,
    "campo_arquivo" => $fileField
], JSON_UNESCAPED_UNICODE);

$stmt->close();
$conn->close();
?>
