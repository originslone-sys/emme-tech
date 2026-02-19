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
            $plans = DB::fetchAll(
                'SELECT * FROM plans WHERE is_active = 1 ORDER BY sort_order, price_monthly ASC'
            );
        } catch (\Throwable) {
            $plans = [];
        }

        Response::view('landing', ['plans' => $plans]);
    }
}
