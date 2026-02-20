<?php

declare(strict_types=1);

namespace App\Controllers\App;

use App\Core\Auth;
use App\Core\CSRF;
use App\Core\DB;
use App\Core\Request;
use App\Core\Response;
use App\Core\Session;

class LoginController
{
    public function showLogin(): void
    {
        if (Auth::tenantUser()) {
            Response::redirect('/app/dashboard');
        }
        Response::view('app/login', ['csrf' => CSRF::field(), 'mode' => 'login']);
    }

    public function postLogin(): void
    {
        CSRF::verifyRequest();

        $email    = Request::post('email', '');
        $password = Request::post('password', '');

        if (Auth::loginTenant($email, $password)) {
            Response::redirect('/app/dashboard');
        }

        Session::flash('error', 'E-mail ou senha inválidos.');
        Response::redirect('/app/login');
    }

    public function showRegister(): void
    {
        if (Auth::tenantUser()) {
            Response::redirect('/app/dashboard');
        }
        Response::view('app/login', [
            'csrf' => CSRF::field(),
            'mode' => 'register',
        ]);
    }

    public function postRegister(): void
    {
        CSRF::verifyRequest();

        $name     = trim(Request::post('name', ''));
        $email    = strtolower(trim(Request::post('email', '')));
        $password = Request::post('password', '');
        $confirm  = Request::post('password_confirm', '');

        if (!$name || !$email || !$password) {
            Session::flash('error', 'Preencha todos os campos.');
            Response::redirect('/app/register');
        }

        if ($password !== $confirm) {
            Session::flash('error', 'As senhas não coincidem.');
            Response::redirect('/app/register');
        }

        if (strlen($password) < 8) {
            Session::flash('error', 'A senha deve ter pelo menos 8 caracteres.');
            Response::redirect('/app/register');
        }

        $exists = DB::fetchColumn('SELECT id FROM tenant_users WHERE email = ?', [$email]);
        if ($exists) {
            Session::flash('error', 'Este e-mail já está em uso.');
            Response::redirect('/app/register');
        }

        DB::beginTransaction();
        try {
            $slug = $this->makeSlug($name);

            // Novos clientes recebem 50 créditos grátis para testar
            $freeCredits = 50;

            $tenantId = DB::insert('tenants', [
                'name'    => $name,
                'slug'    => $slug,
                'email'   => $email,
                'status'  => 'trial',
                'credits' => $freeCredits,
            ]);

            DB::insert('tenant_users', [
                'tenant_id'     => $tenantId,
                'name'          => $name,
                'email'         => $email,
                'password_hash' => password_hash($password, PASSWORD_BCRYPT),
                'role'          => 'owner',
            ]);

            // Registra a transação de bônus
            DB::insert('credit_transactions', [
                'tenant_id'   => $tenantId,
                'amount'      => $freeCredits,
                'type'        => 'bonus',
                'description' => 'Bônus de boas-vindas — 50 créditos grátis',
            ]);

            DB::commit();
        } catch (\Throwable $e) {
            DB::rollBack();
            Session::flash('error', 'Erro ao criar conta: ' . $e->getMessage());
            Response::redirect('/app/register');
        }

        Auth::loginTenant($email, $password);
        Response::redirect('/app/dashboard');
    }

    public function logout(): void
    {
        Auth::logoutTenant();
        Response::redirect('/app/login');
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
