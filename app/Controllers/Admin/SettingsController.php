<?php

declare(strict_types=1);

namespace App\Controllers\Admin;

use App\Core\Auth;
use App\Core\CSRF;
use App\Core\Request;
use App\Core\Response;
use App\Core\Session;
use App\Lib\AuditLog;
use App\Lib\GlobalSettings;

class SettingsController
{
    public function index(): void
    {
        Auth::requireAdmin();

        $settings = GlobalSettings::all();

        Response::view('admin/settings', [
            'admin'    => Auth::admin(),
            'settings' => $settings,
            'csrf'     => CSRF::field(),
        ]);
    }

    public function update(): void
    {
        Auth::requireAdmin();
        CSRF::verifyRequest();

        $keys = [
            'openrouter_api_key',
            'openrouter_api_url',
            'mp_access_token',
            'mp_public_key',
            'mp_webhook_secret',
            'evo_api_url',
            'evo_api_key',
        ];

        $sensitive = ['openrouter_api_key', 'mp_access_token', 'mp_public_key', 'mp_webhook_secret', 'evo_api_key'];

        foreach ($keys as $key) {
            $value = trim(Request::post($key, ''));
            // Não sobrescreve tokens sensíveis se o campo vier vazio
            if (in_array($key, $sensitive, true) && $value === '') {
                continue;
            }
            GlobalSettings::set($key, $value);
        }

        GlobalSettings::clearCache();

        $admin = Auth::admin();
        AuditLog::admin($admin['id'], 'settings.updated', 'global_settings');

        Session::flash('success', 'Configurações globais salvas com sucesso.');
        Response::redirect('/admin/settings');
    }
}
