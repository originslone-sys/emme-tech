<?php
/**
 * Debug - Verificar ambiente do servidor
 * REMOVA ESTE ARQUIVO APOS RESOLVER OS PROBLEMAS
 */
header('Content-Type: text/html; charset=utf-8');
echo '<h2>Diagnostico Nuvem</h2>';
echo '<pre>';

// PHP Version
echo "PHP Version: " . PHP_VERSION . "\n";
echo "PHP SAPI: " . php_sapi_name() . "\n\n";

// Verificar arquivos essenciais
$files = [
    'config.php',
    'vendor/autoload.php',
    'src/Storage.php',
    '.htaccess',
    '.user.ini',
];

echo "=== Arquivos ===\n";
foreach ($files as $f) {
    $path = __DIR__ . '/' . $f;
    echo $f . ': ' . (file_exists($path) ? 'OK' : 'NAO ENCONTRADO') . "\n";
}

// Verificar extensoes necessarias
echo "\n=== Extensoes PHP ===\n";
$extensions = ['json', 'curl', 'xml', 'mbstring', 'openssl', 'fileinfo'];
foreach ($extensions as $ext) {
    echo $ext . ': ' . (extension_loaded($ext) ? 'OK' : 'NAO INSTALADA') . "\n";
}

// Verificar funcoes PHP 8.0+
echo "\n=== Funcoes PHP 8.0+ ===\n";
echo "str_starts_with: " . (function_exists('str_starts_with') ? 'OK' : 'NAO DISPONIVEL (requer PHP 8.0+)') . "\n";
echo "str_ends_with: " . (function_exists('str_ends_with') ? 'OK' : 'NAO DISPONIVEL (requer PHP 8.0+)') . "\n";

// Verificar mod_rewrite
echo "\n=== Servidor ===\n";
echo "SERVER_SOFTWARE: " . ($_SERVER['SERVER_SOFTWARE'] ?? 'desconhecido') . "\n";
echo "DOCUMENT_ROOT: " . ($_SERVER['DOCUMENT_ROOT'] ?? 'desconhecido') . "\n";
echo "mod_rewrite: " . (function_exists('apache_get_modules') && in_array('mod_rewrite', apache_get_modules()) ? 'OK' : 'nao detectavel (normal em LiteSpeed/FPM)') . "\n";

// Testar autoload
echo "\n=== Teste Autoload ===\n";
$autoloadPath = __DIR__ . '/vendor/autoload.php';
if (file_exists($autoloadPath)) {
    try {
        require_once $autoloadPath;
        echo "Autoload: OK\n";

        if (class_exists('Aws\S3\S3Client')) {
            echo "AWS SDK: OK\n";
        } else {
            echo "AWS SDK: NAO ENCONTRADO (execute: composer install)\n";
        }

        if (class_exists('Nuvem\Storage')) {
            echo "Nuvem\\Storage: OK\n";
        } else {
            echo "Nuvem\\Storage: NAO ENCONTRADO\n";
        }
    } catch (\Throwable $e) {
        echo "Autoload ERRO: " . $e->getMessage() . "\n";
    }
} else {
    echo "Autoload: vendor/autoload.php NAO EXISTE\n";
    echo "Solucao: Execute 'composer install' no diretorio do projeto\n";
}

// Testar config
echo "\n=== Teste Config ===\n";
$configPath = __DIR__ . '/config.php';
if (file_exists($configPath)) {
    try {
        $config = require $configPath;
        echo "Config: OK\n";
        echo "Bucket: " . ($config['e2']['bucket'] ?? 'nao definido') . "\n";
        echo "Endpoint: " . ($config['e2']['endpoint'] ?? 'nao definido') . "\n";
    } catch (\Throwable $e) {
        echo "Config ERRO: " . $e->getMessage() . "\n";
    }
} else {
    echo "Config: config.php NAO EXISTE\n";
}

echo "\n=== Teste Rewrite ===\n";
echo "Acesse: " . (isset($_SERVER['HTTPS']) ? 'https' : 'http') . "://" . ($_SERVER['HTTP_HOST'] ?? 'seudominio') . dirname($_SERVER['SCRIPT_NAME']) . "/api/check-auth\n";
echo "Se retornar JSON, o rewrite esta funcionando.\n";

echo '</pre>';
