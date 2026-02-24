<?php
$API_KEY = 'a4aLYTawyy4HEUGQIoHCSjDOtSrxh4SA';

$k = $_POST['api_key'] ?? $_GET['api_key'] ?? '';
if ($k !== $API_KEY) {
  http_response_code(403);
  header('Content-Type: application/json');
  echo json_encode(["sucesso"=>false,"mensagem"=>"api_key inválida"], JSON_UNESCAPED_UNICODE);
  exit;
}