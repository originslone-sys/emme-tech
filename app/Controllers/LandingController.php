<?php

declare(strict_types=1);

namespace App\Controllers;

use App\Core\DB;
use App\Core\Response;

class LandingController
{
    public function index(): void
    {
        try {
            $packages = DB::fetchAll(
                'SELECT * FROM credit_packages WHERE is_active = 1 ORDER BY sort_order, price ASC'
            );
        } catch (\Throwable) {
            $packages = [];
        }

        Response::view('landing', ['packages' => $packages]);
    }
}
