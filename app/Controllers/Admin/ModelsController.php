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

class ModelsController
{
    public function index(): void
    {
        Auth::requireAdmin();
        $models = DB::fetchAll('SELECT * FROM model_catalog ORDER BY sort_order, id');
        Response::view('admin/models/index', [
            'admin'  => Auth::admin(),
            'models' => $models,
            'csrf'   => CSRF::field(),
        ]);
    }

    public function create(): void
    {
        Auth::requireAdmin();
        Response::view('admin/models/form', [
            'admin' => Auth::admin(),
            'model' => null,
            'csrf'  => CSRF::field(),
        ]);
    }

    public function store(): void
    {
        Auth::requireAdmin();
        CSRF::verifyRequest();

        $data = $this->collectFormData();
        if (!$data['model_id'] || !$data['display_name']) {
            Session::flash('error', 'Model ID e nome são obrigatórios.');
            Response::redirect('/admin/models/create');
        }

        $id = DB::insert('model_catalog', $data);
        $admin = Auth::admin();
        AuditLog::admin($admin['id'], 'model.created', 'model_catalog', (int)$id, null, $data);

        Session::flash('success', 'Modelo adicionado ao catálogo.');
        Response::redirect('/admin/models');
    }

    public function edit(string $id): void
    {
        Auth::requireAdmin();
        $model = DB::fetchOne('SELECT * FROM model_catalog WHERE id = ?', [(int)$id]);
        if (!$model) Response::abort(404);
        Response::view('admin/models/form', [
            'admin' => Auth::admin(),
            'model' => $model,
            'csrf'  => CSRF::field(),
        ]);
    }

    public function update(string $id): void
    {
        Auth::requireAdmin();
        CSRF::verifyRequest();

        $modelId = (int)$id;
        $old     = DB::fetchOne('SELECT * FROM model_catalog WHERE id = ?', [$modelId]);
        if (!$old) Response::abort(404);

        $data = $this->collectFormData();
        DB::update('model_catalog', $data, ['id' => $modelId]);

        $admin = Auth::admin();
        AuditLog::admin($admin['id'], 'model.updated', 'model_catalog', $modelId, $old, $data);

        Session::flash('success', 'Modelo atualizado.');
        Response::redirect('/admin/models');
    }

    public function destroy(string $id): void
    {
        Auth::requireAdmin();
        CSRF::verifyRequest();

        $modelId = (int)$id;
        DB::update('model_catalog', ['is_active' => 0], ['id' => $modelId]);

        $admin = Auth::admin();
        AuditLog::admin($admin['id'], 'model.disabled', 'model_catalog', $modelId);

        Session::flash('success', 'Modelo desativado.');
        Response::redirect('/admin/models');
    }

    private function collectFormData(): array
    {
        return [
            'provider'            => Request::post('provider', 'openrouter'),
            'model_id'            => trim(Request::post('model_id', '')),
            'display_name'        => trim(Request::post('display_name', '')),
            'description'         => Request::post('description', ''),
            'context_length'      => (int)Request::post('context_length', 4096),
            'supports_functions'  => Request::post('supports_functions') ? 1 : 0,
            'default_temperature' => (float)Request::post('default_temperature', 0.7),
            'default_max_tokens'  => (int)Request::post('default_max_tokens', 1024),
            'is_active'           => Request::post('is_active') ? 1 : 0,
            'sort_order'          => (int)Request::post('sort_order', 0),
        ];
    }
}
