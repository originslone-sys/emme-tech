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

class CreditsController
{
    // ----------------------------------------------------------------
    // Pacotes de créditos
    // ----------------------------------------------------------------

    public function index(): void
    {
        Auth::requireAdmin();

        $packages = DB::fetchAll('SELECT * FROM credit_packages ORDER BY sort_order, id');

        Response::view('admin/credits/index', [
            'admin'    => Auth::admin(),
            'packages' => $packages,
            'csrf'     => CSRF::field(),
        ]);
    }

    public function create(): void
    {
        Auth::requireAdmin();
        Response::view('admin/credits/form', [
            'admin'   => Auth::admin(),
            'package' => null,
            'csrf'    => CSRF::field(),
        ]);
    }

    public function store(): void
    {
        Auth::requireAdmin();
        CSRF::verifyRequest();

        $data = $this->collectFormData();
        if (!$data['name'] || $data['credits'] <= 0) {
            Session::flash('error', 'Nome e créditos são obrigatórios.');
            Response::redirect('/admin/credits/create');
        }

        $id    = DB::insert('credit_packages', $data);
        $admin = Auth::admin();
        AuditLog::admin($admin['id'], 'credit_package.created', 'credit_package', (int)$id);

        Session::flash('success', 'Pacote de créditos criado.');
        Response::redirect('/admin/credits');
    }

    public function edit(string $id): void
    {
        Auth::requireAdmin();
        $package = DB::fetchOne('SELECT * FROM credit_packages WHERE id = ?', [(int)$id]);
        if (!$package) Response::abort(404);

        Response::view('admin/credits/form', [
            'admin'   => Auth::admin(),
            'package' => $package,
            'csrf'    => CSRF::field(),
        ]);
    }

    public function update(string $id): void
    {
        Auth::requireAdmin();
        CSRF::verifyRequest();

        $pkgId = (int)$id;
        $pkg   = DB::fetchOne('SELECT id FROM credit_packages WHERE id = ?', [$pkgId]);
        if (!$pkg) Response::abort(404);

        $data = $this->collectFormData();
        DB::update('credit_packages', $data, ['id' => $pkgId]);

        $admin = Auth::admin();
        AuditLog::admin($admin['id'], 'credit_package.updated', 'credit_package', $pkgId);

        Session::flash('success', 'Pacote atualizado.');
        Response::redirect('/admin/credits');
    }

    public function destroy(string $id): void
    {
        Auth::requireAdmin();
        CSRF::verifyRequest();

        $pkgId = (int)$id;
        DB::delete('credit_packages', ['id' => $pkgId]);

        $admin = Auth::admin();
        AuditLog::admin($admin['id'], 'credit_package.deleted', 'credit_package', $pkgId);

        Session::flash('success', 'Pacote removido.');
        Response::redirect('/admin/credits');
    }

    // ----------------------------------------------------------------
    // Adicionar créditos manualmente a um tenant
    // POST /admin/tenants/:id/add-credits
    // ----------------------------------------------------------------

    public function addCreditsToTenant(string $id): void
    {
        Auth::requireAdmin();
        CSRF::verifyRequest();

        $tenantId = (int)$id;
        $tenant   = DB::fetchOne('SELECT id, credits FROM tenants WHERE id = ?', [$tenantId]);
        if (!$tenant) Response::abort(404);

        $amount = (int)Request::post('amount', 0);
        $note   = trim(Request::post('note', 'Créditos adicionados manualmente'));

        if ($amount === 0) {
            Session::flash('error', 'Informe uma quantidade válida de créditos.');
            Response::redirect("/admin/tenants/{$tenantId}/edit");
        }

        DB::beginTransaction();
        try {
            DB::query('UPDATE tenants SET credits = credits + ? WHERE id = ?', [$amount, $tenantId]);
            DB::insert('credit_transactions', [
                'tenant_id'   => $tenantId,
                'amount'      => $amount,
                'type'        => 'manual',
                'description' => $note,
            ]);
            DB::commit();
        } catch (\Throwable $e) {
            DB::rollBack();
            Session::flash('error', 'Erro ao adicionar créditos: ' . $e->getMessage());
            Response::redirect("/admin/tenants/{$tenantId}/edit");
        }

        $admin = Auth::admin();
        AuditLog::admin($admin['id'], 'tenant.credits_added', 'tenant', $tenantId, null, ['amount' => $amount]);

        Session::flash('success', "Créditos adicionados ao cliente.");
        Response::redirect("/admin/tenants/{$tenantId}/edit");
    }

    private function collectFormData(): array
    {
        return [
            'name'        => trim(Request::post('name', '')),
            'credits'     => (int)Request::post('credits', 0),
            'price_brl'   => (float)Request::post('price_brl', 0),
            'description' => trim(Request::post('description', '')),
            'is_active'   => Request::post('is_active') ? 1 : 0,
            'sort_order'  => (int)Request::post('sort_order', 0),
        ];
    }
}
