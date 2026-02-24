<?php
// api/marcar_status.php
header('Content-Type: application/json');
require 'conexao.php';

if (!isset($_GET['id_tarefa']) || !isset($_GET['status'])) {
    die(json_encode(["sucesso" => false, "mensagem" => "Parâmetros incompletos. Envie id_tarefa e status."]));
}

$id_tarefa = (int)$_GET['id_tarefa'];
$status_novo = $conn->real_escape_string($_GET['status']);

// ==========================================
// EXCLUSÃO DO ARQUIVO FÍSICO COM SEGURANÇA
// ==========================================
// Se o Auto.js enviar status "baixado", "postado" ou "concluido", o arquivo é deletado.
$status_para_excluir = ['baixado', 'postado', 'concluido'];

if (in_array(strtolower($status_novo), $status_para_excluir)) {
    // Primeiro, precisamos descobrir qual é o nome do arquivo amarrado a este ID
    $sql_busca = "SELECT nome_arquivo FROM fila_postagens WHERE id = $id_tarefa";
    $result = $conn->query($sql_busca);
    
    if ($result && $result->num_rows > 0) {
        $arquivo = $result->fetch_assoc()['nome_arquivo'];
        $caminho_video = dirname(__DIR__) . "/videos/" . $arquivo;
        
        // Se o arquivo existir na pasta /videos, nós o deletamos para liberar espaço!
        if (file_exists($caminho_video)) {
            unlink($caminho_video);
        }
    }
}

// Atualiza o banco de dados com o novo status
$sql = "UPDATE fila_postagens SET status='$status_novo' WHERE id=$id_tarefa";

if ($conn->query($sql) === TRUE) {
    echo json_encode(["sucesso" => true, "mensagem" => "Status atualizado ($status_novo). Servidor limpo se aplicável."]);
} else {
    echo json_encode(["sucesso" => false, "mensagem" => "Erro ao atualizar banco: " . $conn->error]);
}
$conn->close();
?>