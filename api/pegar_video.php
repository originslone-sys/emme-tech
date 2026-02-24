<?php
// api/pegar_video.php
// Retorna vídeos pendentes para o Auto.js/mobile de uma conta específica

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

$vmos_id = trim($_GET['vmos_id'] ?? $_POST['vmos_id'] ?? '');

if ($vmos_id === '') {
    http_response_code(400);
    echo json_encode(["sucesso" => false, "mensagem" => "Informe o vmos_id."], JSON_UNESCAPED_UNICODE);
    exit;
}

// Busca vídeos pendentes com prepared statement
$stmt = $conn->prepare(
    "SELECT id, nome_arquivo, legenda FROM fila_postagens
     WHERE vmos_id = ? AND status = 'pendente'
     ORDER BY id ASC"
);
if (!$stmt) {
    http_response_code(500);
    echo json_encode(["sucesso" => false, "mensagem" => "Erro ao preparar query: " . $conn->error], JSON_UNESCAPED_UNICODE);
    exit;
}

$stmt->bind_param("s", $vmos_id);
$stmt->execute();
$resultado = $stmt->get_result();

if ($resultado && $resultado->num_rows > 0) {
    // URL base sempre HTTPS
    $host = $_SERVER['HTTP_HOST'] ?? 'emmetech.digital';
    $url_site = "https://" . $host;

    $videos_lista = [];
    $ids_para_atualizar = [];

    while ($video = $resultado->fetch_assoc()) {
        $id_video = (int)$video['id'];
        $nome_arquivo = basename($video['nome_arquivo']);
        $link_download = $url_site . "/videos/" . $nome_arquivo;

        $videos_lista[] = [
            "id"           => $id_video,
            "nome_arquivo" => $nome_arquivo,
            "video_url"    => $link_download,
            "legenda"      => $video['legenda'] ?? ''
        ];
        $ids_para_atualizar[] = $id_video;
    }
    $stmt->close();

    // Marca os vídeos como "baixando" para não serem entregues novamente
    if (!empty($ids_para_atualizar)) {
        $placeholders = implode(',', array_fill(0, count($ids_para_atualizar), '?'));
        $types = str_repeat('i', count($ids_para_atualizar));
        $stmt_upd = $conn->prepare("UPDATE fila_postagens SET status = 'baixando' WHERE id IN ($placeholders)");
        if ($stmt_upd) {
            $stmt_upd->bind_param($types, ...$ids_para_atualizar);
            $stmt_upd->execute();
            $stmt_upd->close();
        }
    }

    echo json_encode([
        "sucesso"    => true,
        "quantidade" => count($videos_lista),
        "videos"     => $videos_lista
    ], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
} else {
    $stmt->close();
    echo json_encode([
        "sucesso"   => false,
        "mensagem"  => "Nenhum vídeo pendente para a conta " . $vmos_id
    ], JSON_UNESCAPED_UNICODE);
}

$conn->close();
?>
