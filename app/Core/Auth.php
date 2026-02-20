<?php

declare(strict_types=1);

namespace App\Core;

/**
 * Auth — autenticação de admin e tenant.
 */
class Auth
{
    // ----------------------------------------------------------------
    // ADMIN AUTH
    // ----------------------------------------------------------------

    public static function loginAdmin(string $email, string $password): bool
    {
        $admin = DB::fetchOne(
            'SELECT * FROM admin_users WHERE email = ? AND is_active = 1 LIMIT 1',
            [strtolower(trim($email))]
        );
        if (!$admin || !password_verify($password, $admin['password_hash'])) {
            return false;
        }
        DB::query('UPDATE admin_users SET last_login_at = NOW() WHERE id = ?', [$admin['id']]);
        Session::set('admin', [
            'id'    => $admin['id'],
            'name'  => $admin['name'],
            'email' => $admin['email'],
            'role'  => $admin['role'],
        ]);
        return true;
    }

    public static function admin(): array|null
    {
        return Session::get('admin');
    }

    public static function requireAdmin(): void
    {
        if (!self::admin()) {
            header('Location: /admin/login');
            exit;
        }
    }

    public static function logoutAdmin(): void
    {
        Session::remove('admin');
        Session::remove('tenant_user');
    }

    // ----------------------------------------------------------------
    // TENANT AUTH
    // ----------------------------------------------------------------

    public static function loginTenant(string $email, string $password): bool
    {
        $user = DB::fetchOne(
            'SELECT tu.*, t.status AS tenant_status, t.name AS tenant_name, t.credits AS tenant_credits
             FROM tenant_users tu
             JOIN tenants t ON t.id = tu.tenant_id
             WHERE tu.email = ? AND tu.is_active = 1
             LIMIT 1',
            [strtolower(trim($email))]
        );
        if (!$user || !password_verify($password, $user['password_hash'])) {
            return false;
        }
        DB::query('UPDATE tenant_users SET last_login_at = NOW() WHERE id = ?', [$user['id']]);
        Session::set('tenant_user', [
            'id'             => $user['id'],
            'tenant_id'      => $user['tenant_id'],
            'name'           => $user['name'],
            'email'          => $user['email'],
            'role'           => $user['role'],
            'tenant_name'    => $user['tenant_name'],
            'tenant_status'  => $user['tenant_status'],
            'tenant_credits' => $user['tenant_credits'],
        ]);
        return true;
    }

    public static function tenantUser(): array|null
    {
        return Session::get('tenant_user');
    }

    public static function tenantId(): int|null
    {
        $u = self::tenantUser();
        return $u ? (int)$u['tenant_id'] : null;
    }

    public static function requireTenant(): void
    {
        if (!self::tenantUser()) {
            header('Location: /app/login');
            exit;
        }
    }

    public static function logoutTenant(): void
    {
        Session::remove('tenant_user');
    }

    // ----------------------------------------------------------------
    // Créditos e limites
    // ----------------------------------------------------------------

    /**
     * Retorna o saldo atual de créditos do tenant (lê do banco, sempre fresco).
     */
    public static function tenantCredits(): int
    {
        $tid = self::tenantId();
        if (!$tid) return 0;
        return (int)DB::fetchColumn('SELECT credits FROM tenants WHERE id = ?', [$tid]);
    }

    /**
     * Verifica se o tenant tem créditos disponíveis.
     */
    public static function hasCredits(): bool
    {
        return self::tenantCredits() > 0;
    }

    /**
     * Clientes podem criar quantos agentes quiserem.
     */
    public static function canCreateAgent(): bool
    {
        return true;
    }

    /**
     * Crons disponíveis para todos os clientes.
     */
    public static function canCreateCron(): bool
    {
        return true;
    }

    /**
     * Upload de documentos disponível para todos os clientes.
     */
    public static function canUploadDoc(): bool
    {
        return true;
    }
}
