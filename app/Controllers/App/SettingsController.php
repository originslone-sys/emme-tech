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
use App\Lib\Crypto;

class SettingsController
{
    public function index(): void
    {
        Auth::requireTenant();
        $tid    = Auth::tenantId();
        $tenant = DB::fetchOne('SELECT * FROM tenants WHERE id = ?', [$tid]);
        $token  = DB::fetchOne('SELECT * FROM openrouter_tokens WHERE tenant_id = ? AND is_default = 1', [$tid]);

        $tokenPreview = '';
        if ($token) {
            $decrypted = Crypto::tryDecrypt($token['token_encrypted']);
            if ($decrypted) {
                $tokenPreview = substr($decrypted, 0, 12) . '...' . substr($decrypted, -6);
            }
        }

        Response::view('app/settings', [
            'user'         => Auth::tenantUser(),
            'tenant'       => $tenant,
            'tokenPreview' => $tokenPreview,
            'hasToken'     => (bool)$token,
            'csrf'         => CSRF::field(),
        ]);
    }

    public function updateProfile(): void
    {
        Auth::requireTenant();
        CSRF::verifyRequest();

        $tid    = Auth::tenantId();
        $user   = Auth::tenantUser();
        $old    = DB::fetchOne('SELECT * FROM tenants WHERE id = ?', [$tid]);

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

    public function updateOpenRouterToken(): void
    {
        Auth::requireTenant();
        CSRF::verifyRequest();

        $tid    = Auth::tenantId();
        $user   = Auth::tenantUser();
        $token  = trim(Request::post('openrouter_token', ''));

        if (!$token) {
            Session::flash('error', 'Token não pode ser vazio.');
            Response::redirect('/app/settings');
        }

        if (!str_starts_with($token, 'sk-or-')) {
            Session::flash('error', 'Token OpenRouter inválido. Deve começar com sk-or-');
            Response::redirect('/app/settings');
        }

        $encrypted = Crypto::encrypt($token);

        // Upsert default token
        $existing = DB::fetchOne('SELECT id FROM openrouter_tokens WHERE tenant_id = ? AND is_default = 1', [$tid]);
        if ($existing) {
            DB::update('openrouter_tokens', [
                'token_encrypted' => $encrypted,
                'updated_at'      => date('Y-m-d H:i:s'),
            ], ['id' => $existing['id']]);
        } else {
            DB::insert('openrouter_tokens', [
                'tenant_id'       => $tid,
                'token_encrypted' => $encrypted,
                'label'           => 'Padrão',
                'is_default'      => 1,
            ]);
        }

        AuditLog::tenant($user['id'], $tid, 'settings.openrouter_token_updated');
        Session::flash('success', 'Token OpenRouter atualizado com sucesso.');
        Response::redirect('/app/settings');
    }
}
