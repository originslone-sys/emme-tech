<?php
// api/pegar_video.php
header('Content-Type: application/json');
require 'conexao.php';

if (!isset($_GET['vmos_id'])) {
    die(json_encode(["sucesso" => false, "mensagem" => "Informe o vmos_id."]));
}

$vmos_id = $conn->real_escape_string($_GET['vmos_id']);

// Busca TODOS os vídeos pendentes para esta conta específica
$sql = "SELECT id, nome_arquivo, legenda FROM fila_postagens 
        WHERE vmos_id = '$vmos_id' AND status = 'pendente' 
        ORDER BY id ASC";

$resultado = $conn->query($sql);

if ($resultado && $resultado->num_rows > 0) {
    $videos_lista = [];
    $ids_para_atualizar = [];
    
    // Descobre a URL base do seu site de forma dinâmica
    $url_site = (isset($_SERVER['HTTPS']) && $_SERVER['HTTPS'] === 'on' ? "https" : "http") . "://$_SERVER[HTTP_HOST]";

    // Constroi a lista de vídeos para mandar pro celular
    while($video = $resultado->fetch_assoc()) {
        $id_video = $video['id'];
        $link_download = $url_site . "/videos/" . $video['nome_arquivo'];
        
        $videos_lista[] = [
            "id" => $id_video,
            "nome_arquivo" => $video['nome_arquivo'],
            "video_url" => $link_download,
            "legenda" => $video['legenda']
        ];
        $ids_para_atualizar[] = $id_video;
    }
    
    // Trava todos os vídeos que foram enviados para não serem pegos novamente
    $ids_str = implode(",", $ids_para_atualizar);
    $sql_update = "UPDATE fila_postagens SET status = 'baixando' WHERE id IN ($ids_str)";
    $conn->query($sql_update);
    
    // Retorna a lista completa para o Auto.js processar
    echo json_encode([
        "sucesso" => true,
        "quantidade" => count($videos_lista),
        "videos" => $videos_lista
    ], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    
} else {
    echo json_encode(["sucesso" => false, "mensagem" => "Nenhum vídeo pendente para a conta " . $vmos_id]);
}

$conn->close();
?>