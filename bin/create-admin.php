#!/usr/bin/env php
<?php
/**
 * create-admin.php — Creates the initial superadmin user.
 *
 * Usage:
 *   php bin/create-admin.php
 *   php bin/create-admin.php --email=admin@site.com --password=SenhaForte123 --name="Admin"
 */

declare(strict_types=1);

define('APP_ROOT', dirname(__DIR__));
require APP_ROOT . '/app/Config/config.php';

use App\Core\DB;

spl_autoload_register(function (string $class): void {
    $path = str_replace('\\', '/', $class);
    $file = APP_ROOT . '/app/' . substr($path, 4) . '.php';
    if (file_exists($file)) require_once $file;
});

// Parse CLI args
$opts = getopt('', ['email:', 'password:', 'name:', 'role:']);

if (!empty($opts['email'])) {
    $email    = $opts['email'];
    $password = $opts['password'] ?? '';
    $name     = $opts['name']     ?? 'Super Admin';
    $role     = $opts['role']     ?? 'superadmin';
} else {
    // Interactive
    echo "=== Criar Superadmin ===\n";
    echo "Nome [Super Admin]: ";
    $name = trim(fgets(STDIN) ?: '') ?: 'Super Admin';

    echo "E-mail [" . env('ADMIN_DEFAULT_EMAIL', 'admin@localhost') . "]: ";
    $email = trim(fgets(STDIN) ?: '') ?: env('ADMIN_DEFAULT_EMAIL', 'admin@localhost');

    echo "Senha (mín. 8 chars): ";
    // Try to disable echo on *nix
    if (PHP_OS_FAMILY !== 'Windows') {
        system('stty -echo');
    }
    $password = trim(fgets(STDIN) ?: '');
    if (PHP_OS_FAMILY !== 'Windows') {
        system('stty echo');
    }
    echo "\n";

    $role = 'superadmin';
}

if (!$email || !$password) {
    echo "ERRO: E-mail e senha são obrigatórios.\n";
    exit(1);
}

if (strlen($password) < 8) {
    echo "ERRO: Senha deve ter pelo menos 8 caracteres.\n";
    exit(1);
}

$email = strtolower(trim($email));

// Check if exists
$existing = DB::fetchOne('SELECT id FROM admin_users WHERE email = ?', [$email]);
if ($existing) {
    echo "Admin com e-mail '$email' já existe (id={$existing['id']}).\n";
    echo "Deseja atualizar a senha? (s/N): ";
    $confirm = strtolower(trim(fgets(STDIN) ?: ''));
    if ($confirm === 's' || $confirm === 'sim') {
        DB::update('admin_users', [
            'password_hash' => password_hash($password, PASSWORD_BCRYPT),
            'name'          => $name,
        ], ['id' => $existing['id']]);
        echo "✅ Senha do admin '$email' atualizada com sucesso.\n";
    } else {
        echo "Operação cancelada.\n";
    }
    exit(0);
}

$id = DB::insert('admin_users', [
    'name'          => $name,
    'email'         => $email,
    'password_hash' => password_hash($password, PASSWORD_BCRYPT),
    'role'          => $role,
    'is_active'     => 1,
]);

echo "✅ Superadmin criado com sucesso!\n";
echo "   ID:    $id\n";
echo "   Nome:  $name\n";
echo "   Email: $email\n";
echo "   Role:  $role\n";
echo "\nAcesse: " . env('APP_URL', 'http://localhost') . "/admin/login\n";
