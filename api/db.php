<?php
// api/conexao.php
$host = "localhost";
$usuario = "u280542940_uno_user";
$senha = "Antonio@230190";
$banco = "u280542940_uno_db";

$conn = new mysqli($host, $usuario, $senha, $banco);

if ($conn->connect_error) {
    die(json_encode(["erro" => "Falha na conexão com o banco de dados: " . $conn->connect_error]));
}
?>