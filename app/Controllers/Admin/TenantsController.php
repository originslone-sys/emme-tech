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

        $search = Request::get('q', '');
        $status = Request::get('status', '');
        $params = [];
        $where  = ['1=1'];

        if ($search) {
            $where[]  = '(t.name LIKE ? OR t.email LIKE ?)';
            $params[] = "%$search%";
            $params[] = "%$search%";
        }
        if ($status) {
            $where[]  = 't.status = ?';
            $params[] = $status;
        }

        $tenants = DB::fetchAll(
            'SELECT t.*,
                    (SELECT COUNT(*) FROM agents WHERE tenant_id = t.id) AS agent_count,
                    (SELECT COUNT(*) FROM messages WHERE tenant_id = t.id AND direction = \'outbound\') AS msg_count
             FROM tenants t
             WHERE ' . implode(' AND ', $where) . '
             ORDER BY t.created_at DESC',
            $params
        );

        Response::view('admin/tenants/index', [
            'admin'   => Auth::admin(),
            'tenants' => $tenants,
            'search'  => $search,
            'status'  => $status,
            'csrf'    => CSRF::field(),
        ]);
    }

    public function create(): void
    {
        Auth::requireAdmin();
        Response::view('admin/tenants/form', [
            'admin'  => Auth::admin(),
            'tenant' => null,
            'csrf'   => CSRF::field(),
        ]);
    }

    public function store(): void
    {
        Auth::requireAdmin();
        CSRF::verifyRequest();

        $name     = trim(Request::post('name', ''));
        $email    = strtolower(trim(Request::post('email', '')));
        $password = Request::post('password', '');
        $status   = Request::post('status', 'trial');
        $tz       = Request::post('timezone', 'America/Sao_Paulo');
        $credits  = (int)Request::post('credits', 50);

        if (!$name || !$email || !$password) {
            Session::flash('error', 'Preencha nome, e-mail e senha.');
            Response::redirect('/admin/tenants/create');
        }

        $slug = $this->makeSlug($name);

        DB::beginTransaction();
        try {
            $tenantId = DB::insert('tenants', [
                'name'     => $name,
                'slug'     => $slug,
                'email'    => $email,
                'status'   => $status,
                'timezone' => $tz,
                'credits'  => $credits,
            ]);

            DB::insert('tenant_users', [
                'tenant_id'     => $tenantId,
                'name'          => $name,
                'email'         => $email,
                'password_hash' => password_hash($password, PASSWORD_BCRYPT),
                'role'          => 'owner',
            ]);

            if ($credits > 0) {
                DB::insert('credit_transactions', [
                    'tenant_id'   => $tenantId,
                    'amount'      => $credits,
                    'type'        => 'bonus',
                    'description' => 'Créditos iniciais pelo admin',
                ]);
            }

            DB::commit();
        } catch (\Throwable $e) {
            DB::rollBack();
            Session::flash('error', 'Erro ao criar cliente: ' . $e->getMessage());
            Response::redirect('/admin/tenants/create');
        }

        $admin = Auth::admin();
        AuditLog::admin($admin['id'], 'tenant.created', 'tenant', (int)$tenantId);

        Session::flash('success', 'Cliente criado com sucesso.');
        Response::redirect('/admin/tenants');
    }

    public function edit(string $id): void
    {
        Auth::requireAdmin();
        $tenant = DB::fetchOne('SELECT * FROM tenants WHERE id = ?', [(int)$id]);
        if (!$tenant) Response::abort(404);

        $recentTransactions = DB::fetchAll(
            'SELECT * FROM credit_transactions WHERE tenant_id = ? ORDER BY created_at DESC LIMIT 20',
            [(int)$id]
        );

        $packages = DB::fetchAll('SELECT id, name, credits FROM credit_packages WHERE is_active = 1 ORDER BY sort_order');

        Response::view('admin/tenants/form', [
            'admin'              => Auth::admin(),
            'tenant'             => $tenant,
            'recentTransactions' => $recentTransactions,
            'packages'           => $packages,
            'csrf'               => CSRF::field(),
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
            'name'           => trim(Request::post('name', $old['name'])),
            'email'          => strtolower(trim(Request::post('email', $old['email']))),
            'status'         => Request::post('status', $old['status']),
            'timezone'       => Request::post('timezone', $old['timezone']),
            'business_name'  => trim(Request::post('business_name', '')),
            'business_phone' => trim(Request::post('business_phone', '')),
            'notes'          => Request::post('notes', ''),
        ];

        DB::update('tenants', $data, ['id' => $tenantId]);

        $admin = Auth::admin();
        AuditLog::admin($admin['id'], 'tenant.updated', 'tenant', $tenantId, $old, $data);

        // Redefinir senha se fornecida
        $newPass = Request::post('password', '');
        if ($newPass) {
            DB::query(
                'UPDATE tenant_users SET password_hash = ? WHERE tenant_id = ? AND role = ?',
                [password_hash($newPass, PASSWORD_BCRYPT), $tenantId, 'owner']
            );
        }

        Session::flash('success', 'Cliente atualizado.');
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

        Session::flash('success', 'Cliente removido.');
        Response::redirect('/admin/tenants');
    }

    /**
     * Ativar/inativar cliente rapidamente.
     * POST /admin/tenants/:id/toggle
     */
    public function toggle(string $id): void
    {
        Auth::requireAdmin();
        CSRF::verifyRequest();

        $tenantId = (int)$id;
        $tenant   = DB::fetchOne('SELECT id, status FROM tenants WHERE id = ?', [$tenantId]);
        if (!$tenant) Response::abort(404);

        $newStatus = $tenant['status'] === 'active' ? 'inactive' : 'active';
        DB::update('tenants', ['status' => $newStatus], ['id' => $tenantId]);

        $admin = Auth::admin();
        AuditLog::admin($admin['id'], "tenant.{$newStatus}", 'tenant', $tenantId);

        Session::flash('success', 'Status do cliente atualizado.');
        Response::redirect('/admin/tenants');
    }

    private function makeSlug(string $name): string
    {
        $slug  = strtolower(trim($name));
        $slug  = preg_replace('/[^a-z0-9]+/', '-', iconv('UTF-8', 'ASCII//TRANSLIT', $slug) ?: $slug);
        $slug  = trim($slug, '-');
        $base  = $slug;
        $count = 1;
        while (DB::fetchColumn('SELECT COUNT(*) FROM tenants WHERE slug = ?', [$slug]) > 0) {
            $slug = "$base-$count";
            $count++;
        }
        return $slug;
    }
}
