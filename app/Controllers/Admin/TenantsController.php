<?php

declare(strict_types=1);

namespace App\Controllers\Admin;

use App\Core\Auth;
use App\Core\CSRF;
use App\Core\DB;
use App\Core\Request;
use App\Core\Response;
use App\Core\Session;
use App\Lib\AuditLog;

class TenantsController
{
    public function index(): void
    {
        Auth::requireAdmin();

        $search  = Request::get('q', '');
        $status  = Request::get('status', '');
        $params  = [];
        $where   = ['1=1'];

        if ($search) {
            $where[] = '(t.name LIKE ? OR t.email LIKE ?)';
            $params[] = "%$search%";
            $params[] = "%$search%";
        }
        if ($status) {
            $where[] = 't.status = ?';
            $params[] = $status;
        }

        $tenants = DB::fetchAll(
            'SELECT t.*, p.name AS plan_name,
                    (SELECT COUNT(*) FROM agents WHERE tenant_id = t.id) AS agent_count
             FROM tenants t
             LEFT JOIN plans p ON p.id = t.plan_id
             WHERE ' . implode(' AND ', $where) . '
             ORDER BY t.created_at DESC',
            $params
        );

        $plans = DB::fetchAll('SELECT id, name FROM plans WHERE is_active = 1 ORDER BY sort_order');

        Response::view('admin/tenants/index', [
            'admin'   => Auth::admin(),
            'tenants' => $tenants,
            'plans'   => $plans,
            'search'  => $search,
            'status'  => $status,
            'csrf'    => CSRF::field(),
        ]);
    }

    public function create(): void
    {
        Auth::requireAdmin();
        $plans = DB::fetchAll('SELECT id, name FROM plans WHERE is_active = 1 ORDER BY sort_order');
        Response::view('admin/tenants/form', [
            'admin'  => Auth::admin(),
            'plans'  => $plans,
            'tenant' => null,
            'csrf'   => CSRF::field(),
        ]);
    }

    public function store(): void
    {
        Auth::requireAdmin();
        CSRF::verifyRequest();

        $name     = Request::post('name', '');
        $email    = Request::post('email', '');
        $password = Request::post('password', '');
        $planId   = Request::post('plan_id') ?: null;
        $status   = Request::post('status', 'trial');
        $tz       = Request::post('timezone', 'America/Sao_Paulo');

        if (!$name || !$email || !$password) {
            Session::flash('error', 'Preencha nome, e-mail e senha.');
            Response::redirect('/admin/tenants/create');
        }

        $slug = $this->makeSlug($name);

        DB::beginTransaction();
        try {
            $tenantId = DB::insert('tenants', [
                'name'          => $name,
                'slug'          => $slug,
                'email'         => strtolower($email),
                'plan_id'       => $planId,
                'status'        => $status,
                'timezone'      => $tz,
                'trial_ends_at' => date('Y-m-d H:i:s', strtotime('+14 days')),
            ]);

            DB::insert('tenant_users', [
                'tenant_id'     => $tenantId,
                'name'          => $name,
                'email'         => strtolower($email),
                'password_hash' => password_hash($password, PASSWORD_BCRYPT),
                'role'          => 'owner',
            ]);

            DB::commit();
        } catch (\Throwable $e) {
            DB::rollBack();
            Session::flash('error', 'Erro ao criar tenant: ' . $e->getMessage());
            Response::redirect('/admin/tenants/create');
        }

        $admin = Auth::admin();
        AuditLog::admin($admin['id'], 'tenant.created', 'tenant', (int)$tenantId);

        Session::flash('success', 'Tenant criado com sucesso.');
        Response::redirect('/admin/tenants');
    }

    public function edit(string $id): void
    {
        Auth::requireAdmin();
        $tenant = DB::fetchOne('SELECT * FROM tenants WHERE id = ?', [(int)$id]);
        if (!$tenant) Response::abort(404);

        $plans = DB::fetchAll('SELECT id, name FROM plans WHERE is_active = 1 ORDER BY sort_order');
        Response::view('admin/tenants/form', [
            'admin'  => Auth::admin(),
            'plans'  => $plans,
            'tenant' => $tenant,
            'csrf'   => CSRF::field(),
        ]);
    }

    public function update(string $id): void
    {
        Auth::requireAdmin();
        CSRF::verifyRequest();

        $tenantId = (int)$id;
        $old = DB::fetchOne('SELECT * FROM tenants WHERE id = ?', [$tenantId]);
        if (!$old) Response::abort(404);

        $data = [
            'name'     => Request::post('name', $old['name']),
            'email'    => strtolower(Request::post('email', $old['email'])),
            'plan_id'  => Request::post('plan_id') ?: null,
            'status'   => Request::post('status', $old['status']),
            'timezone' => Request::post('timezone', $old['timezone']),
            'notes'    => Request::post('notes', ''),
        ];

        DB::update('tenants', $data, ['id' => $tenantId]);

        $admin = Auth::admin();
        AuditLog::admin($admin['id'], 'tenant.updated', 'tenant', $tenantId, $old, $data);

        // Reset password if provided
        $newPass = Request::post('password', '');
        if ($newPass) {
            DB::query(
                'UPDATE tenant_users SET password_hash = ? WHERE tenant_id = ? AND role = ?',
                [password_hash($newPass, PASSWORD_BCRYPT), $tenantId, 'owner']
            );
        }

        Session::flash('success', 'Tenant atualizado.');
        Response::redirect('/admin/tenants');
    }

    public function destroy(string $id): void
    {
        Auth::requireAdmin();
        CSRF::verifyRequest();

        $tenantId = (int)$id;
        DB::delete('tenants', ['id' => $tenantId]);

        $admin = Auth::admin();
        AuditLog::admin($admin['id'], 'tenant.deleted', 'tenant', $tenantId);

        Session::flash('success', 'Tenant removido.');
        Response::redirect('/admin/tenants');
    }

    private function makeSlug(string $name): string
    {
        $slug = strtolower(trim($name));
        $slug = preg_replace('/[^a-z0-9]+/', '-', iconv('UTF-8', 'ASCII//TRANSLIT', $slug) ?: $slug);
        $slug = trim($slug, '-');
        // Ensure uniqueness
        $base  = $slug;
        $count = 1;
        while (DB::fetchColumn('SELECT COUNT(*) FROM tenants WHERE slug = ?', [$slug]) > 0) {
            $slug = "$base-$count";
            $count++;
        }
        return $slug;
    }
}
