<?php

declare(strict_types=1);

namespace App\Controllers\Admin;

use App\Core\Auth;
use App\Core\CSRF;
use App\Core\Request;
use App\Core\Response;
use App\Core\Session;

class LoginController
{
    public function showLogin(): void
    {
        if (Auth::admin()) {
            Response::redirect('/admin/dashboard');
        }
        Response::view('admin/login', ['csrf' => CSRF::field()]);
    }

    public function postLogin(): void
    {
        CSRF::verifyRequest();

        $email    = Request::post('email', '');
        $password = Request::post('password', '');

        if (Auth::loginAdmin($email, $password)) {
            Session::flash('success', 'Bem-vindo de volta!');
            Response::redirect('/admin/dashboard');
        }

        Session::flash('error', 'E-mail ou senha inválidos.');
        Response::redirect('/admin/login');
    }

    public function logout(): void
    {
        Auth::logoutAdmin();
        Response::redirect('/admin/login');
    }
}
