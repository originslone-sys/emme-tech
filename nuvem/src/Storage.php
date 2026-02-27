<?php

namespace Nuvem;

use Aws\S3\S3Client;
use Aws\S3\Exception\S3Exception;

class Storage
{
    private S3Client $client;
    private string $bucket;

    public function __construct(array $config)
    {
        $this->bucket = $config['bucket'];

        $this->client = new S3Client([
            'version'     => $config['version'] ?? 'latest',
            'region'      => $config['region'],
            'endpoint'    => $config['endpoint'],
            'credentials' => [
                'key'    => $config['key'],
                'secret' => $config['secret'],
            ],
            'use_path_style_endpoint' => true,
        ]);
    }

    /**
     * Listar arquivos e pastas em um prefixo (caminho)
     */
    public function listObjects(string $prefix = '', string $delimiter = '/'): array
    {
        $prefix = $this->normalizePath($prefix);

        $params = [
            'Bucket'    => $this->bucket,
            'Prefix'    => $prefix,
            'Delimiter' => $delimiter,
        ];

        $result = $this->client->listObjectsV2($params);

        $folders = [];
        $files = [];

        // Pastas (CommonPrefixes)
        if (!empty($result['CommonPrefixes'])) {
            foreach ($result['CommonPrefixes'] as $cp) {
                $fullPath = $cp['Prefix'];
                $name = rtrim(str_replace($prefix, '', $fullPath), '/');
                if ($name !== '') {
                    $folders[] = [
                        'name' => $name,
                        'path' => $fullPath,
                        'type' => 'folder',
                    ];
                }
            }
        }

        // Arquivos (Contents)
        if (!empty($result['Contents'])) {
            foreach ($result['Contents'] as $obj) {
                $key = $obj['Key'];
                $name = str_replace($prefix, '', $key);

                // Ignorar o proprio prefixo (pasta placeholder)
                if ($name === '' || $name === '/') {
                    continue;
                }

                $files[] = [
                    'name'         => $name,
                    'path'         => $key,
                    'type'         => 'file',
                    'size'         => $obj['Size'],
                    'lastModified' => $obj['LastModified']->format('Y-m-d H:i:s'),
                    'extension'    => strtolower(pathinfo($name, PATHINFO_EXTENSION)),
                ];
            }
        }

        // Ordenar pastas e arquivos por nome
        usort($folders, fn($a, $b) => strcasecmp($a['name'], $b['name']));
        usort($files, fn($a, $b) => strcasecmp($a['name'], $b['name']));

        return [
            'folders' => $folders,
            'files'   => $files,
            'path'    => $prefix,
        ];
    }

    /**
     * Criar uma pasta (prefixo vazio no S3)
     */
    public function createFolder(string $path): bool
    {
        $path = $this->normalizePath($path);
        if (!str_ends_with($path, '/')) {
            $path .= '/';
        }

        $this->client->putObject([
            'Bucket' => $this->bucket,
            'Key'    => $path,
            'Body'   => '',
        ]);

        return true;
    }

    /**
     * Renomear arquivo ou pasta
     */
    public function rename(string $oldPath, string $newPath): bool
    {
        $oldPath = $this->normalizePath($oldPath);
        $newPath = $this->normalizePath($newPath);

        $isFolder = str_ends_with($oldPath, '/');

        if ($isFolder) {
            // Para pastas, copiar todos os objetos com o novo prefixo
            $objects = $this->client->listObjectsV2([
                'Bucket' => $this->bucket,
                'Prefix' => $oldPath,
            ]);

            if (!empty($objects['Contents'])) {
                foreach ($objects['Contents'] as $obj) {
                    $newKey = $newPath . substr($obj['Key'], strlen($oldPath));
                    $this->client->copyObject([
                        'Bucket'     => $this->bucket,
                        'CopySource' => $this->bucket . '/' . $obj['Key'],
                        'Key'        => $newKey,
                    ]);
                    $this->client->deleteObject([
                        'Bucket' => $this->bucket,
                        'Key'    => $obj['Key'],
                    ]);
                }
            }
        } else {
            // Para arquivos, copiar e deletar o original
            $this->client->copyObject([
                'Bucket'     => $this->bucket,
                'CopySource' => $this->bucket . '/' . $oldPath,
                'Key'        => $newPath,
            ]);
            $this->client->deleteObject([
                'Bucket' => $this->bucket,
                'Key'    => $oldPath,
            ]);
        }

        return true;
    }

    /**
     * Excluir arquivo ou pasta
     */
    public function delete(string $path): bool
    {
        $path = $this->normalizePath($path);

        $isFolder = str_ends_with($path, '/');

        if ($isFolder) {
            // Deletar todos os objetos na pasta
            $objects = $this->client->listObjectsV2([
                'Bucket' => $this->bucket,
                'Prefix' => $path,
            ]);

            if (!empty($objects['Contents'])) {
                $deleteObjects = array_map(fn($obj) => ['Key' => $obj['Key']], $objects['Contents']);
                $this->client->deleteObjects([
                    'Bucket' => $this->bucket,
                    'Delete' => ['Objects' => $deleteObjects],
                ]);
            }
        } else {
            $this->client->deleteObject([
                'Bucket' => $this->bucket,
                'Key'    => $path,
            ]);
        }

        return true;
    }

    /**
     * Fazer upload de arquivo
     */
    public function upload(string $path, $fileContent, string $contentType = ''): bool
    {
        $path = $this->normalizePath($path);

        $params = [
            'Bucket' => $this->bucket,
            'Key'    => $path,
            'Body'   => $fileContent,
        ];

        if ($contentType) {
            $params['ContentType'] = $contentType;
        }

        $this->client->putObject($params);
        return true;
    }

    /**
     * Gerar URL pre-assinada para download
     */
    public function getDownloadUrl(string $path, int $expiry = 3600): string
    {
        $path = $this->normalizePath($path);

        $cmd = $this->client->getCommand('GetObject', [
            'Bucket' => $this->bucket,
            'Key'    => $path,
        ]);

        $request = $this->client->createPresignedRequest($cmd, "+{$expiry} seconds");
        return (string) $request->getUri();
    }

    /**
     * Mover arquivo para outro caminho
     */
    public function move(string $oldPath, string $newPath): bool
    {
        return $this->rename($oldPath, $newPath);
    }

    /**
     * Obter informacoes de um arquivo
     */
    public function getFileInfo(string $path): array
    {
        $path = $this->normalizePath($path);

        $result = $this->client->headObject([
            'Bucket' => $this->bucket,
            'Key'    => $path,
        ]);

        return [
            'name'         => basename($path),
            'path'         => $path,
            'size'         => $result['ContentLength'],
            'contentType'  => $result['ContentType'],
            'lastModified' => $result['LastModified']->format('Y-m-d H:i:s'),
            'extension'    => strtolower(pathinfo($path, PATHINFO_EXTENSION)),
        ];
    }

    /**
     * Verificar se um objeto existe
     */
    public function exists(string $path): bool
    {
        $path = $this->normalizePath($path);
        return $this->client->doesObjectExist($this->bucket, $path);
    }

    /**
     * Normalizar caminho removendo barras iniciais
     */
    private function normalizePath(string $path): string
    {
        return ltrim($path, '/');
    }
}
