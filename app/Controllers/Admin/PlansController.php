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

class PlansController
{
    public function index(): void
    {
        Auth::requireAdmin();
        $plans = DB::fetchAll(
            'SELECT p.*,
                    (SELECT COUNT(*) FROM tenants WHERE plan_id = p.id) AS tenant_count
             FROM plans p ORDER BY p.sort_order, p.id'
        );
        Response::view('admin/plans/index', [
            'admin' => Auth::admin(),
            'plans' => $plans,
            'csrf'  => CSRF::field(),
        ]);
    }

    public function create(): void
    {
        Auth::requireAdmin();
        Response::view('admin/plans/form', [
            'admin' => Auth::admin(),
            'plan'  => null,
            'csrf'  => CSRF::field(),
        ]);
    }

    public function store(): void
    {
        Auth::requireAdmin();
        CSRF::verifyRequest();

        $data = $this->collectFormData();
        if (!$data['name'] || !$data['slug']) {
            Session::flash('error', 'Nome e slug são obrigatórios.');
            Response::redirect('/admin/plans/create');
        }

        $id = DB::insert('plans', $data);

        $admin = Auth::admin();
        AuditLog::admin($admin['id'], 'plan.created', 'plan', (int)$id, null, $data);

        Session::flash('success', 'Plano criado.');
        Response::redirect('/admin/plans');
    }

    public function edit(string $id): void
    {
        Auth::requireAdmin();
        $plan = DB::fetchOne('SELECT * FROM plans WHERE id = ?', [(int)$id]);
        if (!$plan) Response::abort(404);
        Response::view('admin/plans/form', [
            'admin' => Auth::admin(),
            'plan'  => $plan,
            'csrf'  => CSRF::field(),
        ]);
    }

    public function update(string $id): void
    {
        Auth::requireAdmin();
        CSRF::verifyRequest();

        $planId = (int)$id;
        $old    = DB::fetchOne('SELECT * FROM plans WHERE id = ?', [$planId]);
        if (!$old) Response::abort(404);

        $data = $this->collectFormData();
        DB::update('plans', $data, ['id' => $planId]);

        $admin = Auth::admin();
        AuditLog::admin($admin['id'], 'plan.updated', 'plan', $planId, $old, $data);

        Session::flash('success', 'Plano atualizado.');
        Response::redirect('/admin/plans');
    }

    public function destroy(string $id): void
    {
        Auth::requireAdmin();
        CSRF::verifyRequest();

        $planId = (int)$id;
        $count  = (int)DB::fetchColumn('SELECT COUNT(*) FROM tenants WHERE plan_id = ?', [$planId]);
        if ($count > 0) {
            Session::flash('error', "Plano possui $count tenants vinculados. Remova-os primeiro.");
            Response::redirect('/admin/plans');
        }

        DB::delete('plans', ['id' => $planId]);
        $admin = Auth::admin();
        AuditLog::admin($admin['id'], 'plan.deleted', 'plan', $planId);

        Session::flash('success', 'Plano removido.');
        Response::redirect('/admin/plans');
    }

    private function collectFormData(): array
    {
        return [
            'name'                    => Request::post('name', ''),
            'slug'                    => preg_replace('/[^a-z0-9\-]/', '', strtolower(Request::post('slug', ''))),
            'description'             => Request::post('description', ''),
            'price_monthly'           => (float)Request::post('price_monthly', 0),
            'price_yearly'            => (float)Request::post('price_yearly', 0),
            'max_agents'              => (int)Request::post('max_agents', 1),
            'max_messages_per_month'  => (int)Request::post('max_messages_per_month', 1000),
            'max_crons'               => (int)Request::post('max_crons', 0),
            'max_docs'                => (int)Request::post('max_docs', 5),
            'storage_limit_mb'        => (int)Request::post('storage_limit_mb', 50),
            'feature_crons'           => Request::post('feature_crons') ? 1 : 0,
            'feature_docs'            => Request::post('feature_docs') ? 1 : 0,
            'feature_api_access'      => Request::post('feature_api_access') ? 1 : 0,
            'feature_custom_persona'  => Request::post('feature_custom_persona') ? 1 : 0,
            'stripe_product_id'       => Request::post('stripe_product_id', ''),
            'stripe_price_monthly_id' => Request::post('stripe_price_monthly_id', ''),
            'stripe_price_yearly_id'  => Request::post('stripe_price_yearly_id', ''),
            'is_active'               => Request::post('is_active') ? 1 : 0,
            'sort_order'              => (int)Request::post('sort_order', 0),
        ];
    }
}
