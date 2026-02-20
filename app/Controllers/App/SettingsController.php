<?php

declare(strict_types=1);

namespace App\Controllers\App;

use App\Core\Auth;
use App\Core\CSRF;
use App\Core\DB;
use App\Core\Request;
use App\Core\Response;
use App\Core\Session;
use App\Lib\AuditLog;

class SettingsController
{
    public function index(): void
    {
        Auth::requireTenant();
        $tid    = Auth::tenantId();
        $tenant = DB::fetchOne('SELECT * FROM tenants WHERE id = ?', [$tid]);

        Response::view('app/settings', [
            'user'   => Auth::tenantUser(),
            'tenant' => $tenant,
            'csrf'   => CSRF::field(),
        ]);
    }

    public function updateProfile(): void
    {
        Auth::requireTenant();
        CSRF::verifyRequest();

        $tid  = Auth::tenantId();
        $user = Auth::tenantUser();
        $old  = DB::fetchOne('SELECT * FROM tenants WHERE id = ?', [$tid]);

        $data = [
            'name'           => trim(Request::post('name', $old['name'])),
            'business_name'  => trim(Request::post('business_name', '')),
            'business_phone' => trim(Request::post('business_phone', '')),
            'timezone'       => Request::post('timezone', 'America/Sao_Paulo'),
        ];

        DB::update('tenants', $data, ['id' => $tid]);
        AuditLog::tenant($user['id'], $tid, 'settings.profile_updated', 'tenant', $tid);

        Session::flash('success', 'Perfil atualizado.');
        Response::redirect('/app/settings');
    }

    public function updatePassword(): void
    {
        Auth::requireTenant();
        CSRF::verifyRequest();

        $userId  = Auth::tenantUser()['id'];
        $current = Request::post('current_password', '');
        $new     = Request::post('new_password', '');
        $confirm = Request::post('confirm_password', '');

        $userRow = DB::fetchOne('SELECT * FROM tenant_users WHERE id = ?', [$userId]);
        if (!password_verify($current, $userRow['password_hash'])) {
            Session::flash('error', 'Senha atual incorreta.');
            Response::redirect('/app/settings');
        }

        if ($new !== $confirm || strlen($new) < 8) {
            Session::flash('error', 'Nova senha inválida (mínimo 8 caracteres e deve confirmar).');
            Response::redirect('/app/settings');
        }

        DB::update('tenant_users', ['password_hash' => password_hash($new, PASSWORD_BCRYPT)], ['id' => $userId]);

        $tid = Auth::tenantId();
        AuditLog::tenant($userId, $tid, 'settings.password_changed');

        Session::flash('success', 'Senha alterada com sucesso.');
        Response::redirect('/app/settings');
    }
}
