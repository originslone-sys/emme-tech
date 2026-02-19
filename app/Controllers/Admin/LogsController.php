<?php

declare(strict_types=1);

namespace App\Controllers\Admin;

use App\Core\Auth;
use App\Core\Response;
use App\Lib\Logger;

class LogsController
{
    public function index(): void
    {
        Auth::requireAdmin();

        $lines   = (int)($_GET['lines'] ?? 200);
        $lines   = min(max($lines, 50), 1000);
        $content = Logger::tail($lines);

        Response::view('admin/logs', [
            'admin'   => Auth::admin(),
            'content' => $content,
            'lines'   => $lines,
        ]);
    }
}
