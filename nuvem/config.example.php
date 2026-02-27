<?php
/**
 * Configuracao do IDrive E2 S3-compatible Storage
 *
 * Copie este arquivo para config.php e preencha suas credenciais.
 * Obtenha suas credenciais em: https://www.idrive.com/s3-storage-e2/
 */

return [
    'e2' => [
        'endpoint'   => 'https://YOUR_ENDPOINT.e2.cloudstorage.com', // Ex: https://k3s5.fra.idrivee2-45.com
        'region'     => 'us-east-1', // Regiao padrao para IDrive E2
        'key'        => 'YOUR_ACCESS_KEY_ID',
        'secret'     => 'YOUR_SECRET_ACCESS_KEY',
        'bucket'     => 'YOUR_BUCKET_NAME',
        'version'    => 'latest',
    ],

    'app' => [
        'name'       => 'Nuvem - Armazenamento',
        'max_upload' => 500 * 1024 * 1024, // 500MB max upload
        'password'   => 'CHANGE_THIS_PASSWORD', // Senha de acesso ao painel
    ],
];
