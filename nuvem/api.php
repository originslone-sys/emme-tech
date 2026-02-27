<?php
/**
 * API - Nuvem Storage
 * Endpoints para gerenciar arquivos e pastas via IDrive E2
 */

require_once __DIR__ . '/vendor/autoload.php';

use Nuvem\Storage;

// Headers
header('Content-Type: application/json; charset=utf-8');
header('X-Content-Type-Options: nosniff');

// Carregar configuracao
$configFile = __DIR__ . '/config.php';
if (!file_exists($configFile)) {
    http_response_code(500);
    echo json_encode(['error' => 'config.php nao encontrado. Copie config.example.php para config.php']);
    exit;
}

$config = require $configFile;

// Verificar autenticacao simples via sessao
session_start();
$action = $_GET['action'] ?? '';

// Acoes que NAO precisam de Storage (resolver antes de conectar ao S3)
switch ($action) {
    case 'check-auth':
        echo json_encode(['authenticated' => !empty($_SESSION['nuvem_auth'])]);
        exit;

    case 'login':
        $_SESSION['nuvem_auth'] = true;
        echo json_encode(['success' => true]);
        exit;

    case 'logout':
        session_destroy();
        echo json_encode(['success' => true]);
        exit;
}

// Todas as outras acoes precisam de autenticacao
if (empty($_SESSION['nuvem_auth'])) {
    http_response_code(401);
    echo json_encode(['error' => 'Nao autenticado']);
    exit;
}

// Inicializar storage somente quando necessario
try {
    $storage = new Storage($config['e2']);
} catch (\Exception $e) {
    http_response_code(500);
    echo json_encode(['error' => 'Erro ao conectar com o storage: ' . $e->getMessage()]);
    exit;
}

// Roteamento de acoes que precisam do Storage
try {
    switch ($action) {
        case 'list':
            handleList($storage);
            break;
        case 'create-folder':
            handleCreateFolder($storage);
            break;
        case 'rename':
            handleRename($storage);
            break;
        case 'delete':
            handleDelete($storage);
            break;
        case 'upload':
            handleUpload($storage, $config);
            break;
        case 'download':
            handleDownload($storage);
            break;
        case 'move':
            handleMove($storage);
            break;
        case 'info':
            handleInfo($storage);
            break;
        default:
            http_response_code(404);
            echo json_encode(['error' => 'Acao nao encontrada']);
    }
} catch (\Aws\S3\Exception\S3Exception $e) {
    http_response_code(500);
    echo json_encode(['error' => 'Erro S3: ' . $e->getAwsErrorMessage()]);
} catch (\Exception $e) {
    http_response_code(500);
    echo json_encode(['error' => $e->getMessage()]);
}

// === Handlers ===

function handleList(Storage $storage): void
{
    $path = $_GET['path'] ?? '';
    $result = $storage->listObjects($path);
    echo json_encode($result);
}

function handleCreateFolder(Storage $storage): void
{
    $input = json_decode(file_get_contents('php://input'), true);
    $path = $input['path'] ?? '';

    if (empty($path)) {
        http_response_code(400);
        echo json_encode(['error' => 'Caminho da pasta e obrigatorio']);
        return;
    }

    // Validar nome da pasta
    $folderName = basename(rtrim($path, '/'));
    if (!preg_match('/^[a-zA-Z0-9_\-. \p{L}]+$/u', $folderName)) {
        http_response_code(400);
        echo json_encode(['error' => 'Nome de pasta invalido. Use apenas letras, numeros, espacos, hifens e underlines.']);
        return;
    }

    $storage->createFolder($path);
    echo json_encode(['success' => true, 'message' => 'Pasta criada com sucesso']);
}

function handleRename(Storage $storage): void
{
    $input = json_decode(file_get_contents('php://input'), true);
    $oldPath = $input['oldPath'] ?? '';
    $newPath = $input['newPath'] ?? '';

    if (empty($oldPath) || empty($newPath)) {
        http_response_code(400);
        echo json_encode(['error' => 'Caminhos antigo e novo sao obrigatorios']);
        return;
    }

    $storage->rename($oldPath, $newPath);
    echo json_encode(['success' => true, 'message' => 'Renomeado com sucesso']);
}

function handleDelete(Storage $storage): void
{
    $input = json_decode(file_get_contents('php://input'), true);
    $path = $input['path'] ?? '';

    if (empty($path)) {
        http_response_code(400);
        echo json_encode(['error' => 'Caminho e obrigatorio']);
        return;
    }

    $storage->delete($path);
    echo json_encode(['success' => true, 'message' => 'Excluido com sucesso']);
}

function handleUpload(Storage $storage, array $config): void
{
    if (empty($_FILES['file'])) {
        http_response_code(400);
        echo json_encode(['error' => 'Nenhum arquivo enviado']);
        return;
    }

    $file = $_FILES['file'];
    $targetPath = $_POST['path'] ?? '';

    if ($file['error'] !== UPLOAD_ERR_OK) {
        http_response_code(400);
        echo json_encode(['error' => 'Erro no upload: codigo ' . $file['error']]);
        return;
    }

    $maxUpload = $config['app']['max_upload'] ?? (500 * 1024 * 1024);
    if ($file['size'] > $maxUpload) {
        http_response_code(400);
        echo json_encode(['error' => 'Arquivo excede o tamanho maximo permitido']);
        return;
    }

    $fileName = basename($file['name']);
    $fullPath = rtrim($targetPath, '/') . '/' . $fileName;
    if (str_starts_with($fullPath, '/')) {
        $fullPath = ltrim($fullPath, '/');
    }

    $fileContent = fopen($file['tmp_name'], 'rb');
    $contentType = $file['type'] ?: 'application/octet-stream';

    $storage->upload($fullPath, $fileContent, $contentType);

    if (is_resource($fileContent)) {
        fclose($fileContent);
    }

    echo json_encode(['success' => true, 'message' => 'Upload realizado com sucesso', 'path' => $fullPath]);
}

function handleDownload(Storage $storage): void
{
    $path = $_GET['path'] ?? '';

    if (empty($path)) {
        http_response_code(400);
        echo json_encode(['error' => 'Caminho e obrigatorio']);
        return;
    }

    $url = $storage->getDownloadUrl($path, 3600);
    echo json_encode(['url' => $url]);
}

function handleMove(Storage $storage): void
{
    $input = json_decode(file_get_contents('php://input'), true);
    $oldPath = $input['oldPath'] ?? '';
    $newPath = $input['newPath'] ?? '';

    if (empty($oldPath) || empty($newPath)) {
        http_response_code(400);
        echo json_encode(['error' => 'Caminhos antigo e novo sao obrigatorios']);
        return;
    }

    $storage->move($oldPath, $newPath);
    echo json_encode(['success' => true, 'message' => 'Movido com sucesso']);
}

function handleInfo(Storage $storage): void
{
    $path = $_GET['path'] ?? '';

    if (empty($path)) {
        http_response_code(400);
        echo json_encode(['error' => 'Caminho e obrigatorio']);
        return;
    }

    $info = $storage->getFileInfo($path);
    echo json_encode($info);
}
