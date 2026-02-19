<?php

declare(strict_types=1);

namespace App\Core;

/**
 * Auth — admin and tenant authentication.
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
            'id'   => $admin['id'],
            'name' => $admin['name'],
            'email'=> $admin['email'],
            'role' => $admin['role'],
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
        Session::remove('tenant');
    }

    // ----------------------------------------------------------------
    // TENANT AUTH
    // ----------------------------------------------------------------

    public static function loginTenant(string $email, string $password): bool
    {
        $user = DB::fetchOne(
            'SELECT tu.*, t.status AS tenant_status, t.name AS tenant_name
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
            'id'          => $user['id'],
            'tenant_id'   => $user['tenant_id'],
            'name'        => $user['name'],
            'email'       => $user['email'],
            'role'        => $user['role'],
            'tenant_name' => $user['tenant_name'],
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
    // Tenant plan / limits helpers
    // ----------------------------------------------------------------

    public static function tenantPlan(): array|null
    {
        $tid = self::tenantId();
        if (!$tid) return null;
        return DB::fetchOne(
            'SELECT p.* FROM plans p
             JOIN tenants t ON t.plan_id = p.id
             WHERE t.id = ?',
            [$tid]
        ) ?: null;
    }

    public static function canCreateAgent(): bool
    {
        $plan = self::tenantPlan();
        if (!$plan) return false;
        $tid   = self::tenantId();
        $count = (int)DB::fetchColumn('SELECT COUNT(*) FROM agents WHERE tenant_id = ?', [$tid]);
        return $count < (int)$plan['max_agents'];
    }

    public static function canCreateCron(): bool
    {
        $plan = self::tenantPlan();
        if (!$plan || !$plan['feature_crons']) return false;
        $tid   = self::tenantId();
        $count = (int)DB::fetchColumn('SELECT COUNT(*) FROM cron_jobs WHERE tenant_id = ?', [$tid]);
        return $count < (int)$plan['max_crons'];
    }

    public static function canUploadDoc(): bool
    {
        $plan = self::tenantPlan();
        if (!$plan || !$plan['feature_docs']) return false;
        $tid   = self::tenantId();
        $count = (int)DB::fetchColumn('SELECT COUNT(*) FROM kb_docs WHERE tenant_id = ?', [$tid]);
        return $count < (int)$plan['max_docs'];
    }
}
