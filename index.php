<?php
/**
 * Front Controller — routes all HTTP requests to the appropriate controller.
 */

declare(strict_types=1);

define('APP_ROOT', __DIR__);
require APP_ROOT . '/app/Config/config.php';

// ----------------------------------------------------------------
// Autoloader (PSR-4 style, no Composer)
// ----------------------------------------------------------------
spl_autoload_register(function (string $class): void {
    $file = APP_ROOT . '/' . str_replace(['App\\', '\\'], ['app/', '/'], $class) . '.php';
    if (file_exists($file)) {
        require_once $file;
    }
});

use App\Core\App;
use App\Core\Session;

// Start session for all requests
Session::start();

$router = new App();

// ----------------------------------------------------------------
// PUBLIC — Webhook endpoints (no auth)
// ----------------------------------------------------------------
$router->get( '/webhook/whatsapp', [\App\Controllers\Webhook\WhatsAppController::class, 'verify']);
$router->post('/webhook/whatsapp', [\App\Controllers\Webhook\WhatsAppController::class, 'receive']);
$router->post('/webhook/stripe',   [\App\Controllers\Webhook\StripeController::class,   'receive']);

// ----------------------------------------------------------------
// ADMIN — Authentication
// ----------------------------------------------------------------
$router->get( '/admin/login',  [\App\Controllers\Admin\LoginController::class, 'showLogin']);
$router->post('/admin/login',  [\App\Controllers\Admin\LoginController::class, 'postLogin']);
$router->get( '/admin/logout', [\App\Controllers\Admin\LoginController::class, 'logout']);

// ----------------------------------------------------------------
// ADMIN — Protected pages
// ----------------------------------------------------------------
$router->get('/admin',           fn() => \App\Core\Response::redirect('/admin/dashboard'));
$router->get('/admin/dashboard', [\App\Controllers\Admin\DashboardController::class, 'index']);

// Tenants CRUD
$router->get( '/admin/tenants',            [\App\Controllers\Admin\TenantsController::class, 'index']);
$router->get( '/admin/tenants/create',     [\App\Controllers\Admin\TenantsController::class, 'create']);
$router->post('/admin/tenants',            [\App\Controllers\Admin\TenantsController::class, 'store']);
$router->get( '/admin/tenants/:id/edit',   [\App\Controllers\Admin\TenantsController::class, 'edit']);
$router->post('/admin/tenants/:id/update', [\App\Controllers\Admin\TenantsController::class, 'update']);
$router->post('/admin/tenants/:id/delete', [\App\Controllers\Admin\TenantsController::class, 'destroy']);

// Plans CRUD
$router->get( '/admin/plans',            [\App\Controllers\Admin\PlansController::class, 'index']);
$router->get( '/admin/plans/create',     [\App\Controllers\Admin\PlansController::class, 'create']);
$router->post('/admin/plans',            [\App\Controllers\Admin\PlansController::class, 'store']);
$router->get( '/admin/plans/:id/edit',   [\App\Controllers\Admin\PlansController::class, 'edit']);
$router->post('/admin/plans/:id/update', [\App\Controllers\Admin\PlansController::class, 'update']);
$router->post('/admin/plans/:id/delete', [\App\Controllers\Admin\PlansController::class, 'destroy']);

// Models CRUD
$router->get( '/admin/models',            [\App\Controllers\Admin\ModelsController::class, 'index']);
$router->get( '/admin/models/create',     [\App\Controllers\Admin\ModelsController::class, 'create']);
$router->post('/admin/models',            [\App\Controllers\Admin\ModelsController::class, 'store']);
$router->get( '/admin/models/:id/edit',   [\App\Controllers\Admin\ModelsController::class, 'edit']);
$router->post('/admin/models/:id/update', [\App\Controllers\Admin\ModelsController::class, 'update']);
$router->post('/admin/models/:id/delete', [\App\Controllers\Admin\ModelsController::class, 'destroy']);

// Audit & Logs
$router->get('/admin/audit', [\App\Controllers\Admin\AuditController::class, 'index']);
$router->get('/admin/logs',  [\App\Controllers\Admin\LogsController::class,  'index']);

// ----------------------------------------------------------------
// APP (Tenant) — Authentication
// ----------------------------------------------------------------
$router->get( '/app/login',    [\App\Controllers\App\LoginController::class, 'showLogin']);
$router->post('/app/login',    [\App\Controllers\App\LoginController::class, 'postLogin']);
$router->get( '/app/register', [\App\Controllers\App\LoginController::class, 'showRegister']);
$router->post('/app/register', [\App\Controllers\App\LoginController::class, 'postRegister']);
$router->get( '/app/logout',   [\App\Controllers\App\LoginController::class, 'logout']);

// ----------------------------------------------------------------
// APP (Tenant) — Protected pages
// ----------------------------------------------------------------
$router->get('/app',           fn() => \App\Core\Response::redirect('/app/dashboard'));
$router->get('/app/dashboard', [\App\Controllers\App\DashboardController::class, 'index']);

// Agents CRUD
$router->get( '/app/agents',            [\App\Controllers\App\AgentsController::class, 'index']);
$router->get( '/app/agents/create',     [\App\Controllers\App\AgentsController::class, 'create']);
$router->post('/app/agents',            [\App\Controllers\App\AgentsController::class, 'store']);
$router->get( '/app/agents/:id/edit',   [\App\Controllers\App\AgentsController::class, 'edit']);
$router->post('/app/agents/:id/update', [\App\Controllers\App\AgentsController::class, 'update']);
$router->post('/app/agents/:id/delete', [\App\Controllers\App\AgentsController::class, 'destroy']);

// Personas CRUD
$router->get( '/app/personas',            [\App\Controllers\App\PersonasController::class, 'index']);
$router->get( '/app/personas/create',     [\App\Controllers\App\PersonasController::class, 'create']);
$router->post('/app/personas',            [\App\Controllers\App\PersonasController::class, 'store']);
$router->get( '/app/personas/:id/edit',   [\App\Controllers\App\PersonasController::class, 'edit']);
$router->post('/app/personas/:id/update', [\App\Controllers\App\PersonasController::class, 'update']);
$router->post('/app/personas/:id/delete', [\App\Controllers\App\PersonasController::class, 'destroy']);

// Docs
$router->get( '/app/docs',                   [\App\Controllers\App\DocsController::class, 'index']);
$router->post('/app/docs/upload',             [\App\Controllers\App\DocsController::class, 'upload']);
$router->post('/app/docs/:id/reprocess',      [\App\Controllers\App\DocsController::class, 'reprocess']);
$router->post('/app/docs/:id/delete',         [\App\Controllers\App\DocsController::class, 'destroy']);

// Crons CRUD
$router->get( '/app/crons',            [\App\Controllers\App\CronsController::class, 'index']);
$router->get( '/app/crons/create',     [\App\Controllers\App\CronsController::class, 'create']);
$router->post('/app/crons',            [\App\Controllers\App\CronsController::class, 'store']);
$router->get( '/app/crons/:id/edit',   [\App\Controllers\App\CronsController::class, 'edit']);
$router->post('/app/crons/:id/update', [\App\Controllers\App\CronsController::class, 'update']);
$router->post('/app/crons/:id/delete', [\App\Controllers\App\CronsController::class, 'destroy']);

// Threads
$router->get('/app/threads', [\App\Controllers\App\ThreadsController::class, 'index']);
$router->get('/app/thread',  [\App\Controllers\App\ThreadsController::class, 'view']);

// Billing
$router->get( '/app/billing',          [\App\Controllers\App\BillingController::class, 'index']);
$router->post('/app/billing/checkout', [\App\Controllers\App\BillingController::class, 'checkout']);
$router->post('/app/billing/portal',   [\App\Controllers\App\BillingController::class, 'portal']);

// Settings
$router->get( '/app/settings',                     [\App\Controllers\App\SettingsController::class, 'index']);
$router->post('/app/settings/profile',             [\App\Controllers\App\SettingsController::class, 'updateProfile']);
$router->post('/app/settings/password',            [\App\Controllers\App\SettingsController::class, 'updatePassword']);
$router->post('/app/settings/openrouter-token',    [\App\Controllers\App\SettingsController::class, 'updateOpenRouterToken']);

// ----------------------------------------------------------------
// Landing page (homepage)
// ----------------------------------------------------------------
$router->get('/', [\App\Controllers\LandingController::class, 'index']);

// ----------------------------------------------------------------
// Run!
// ----------------------------------------------------------------
try {
    $router->run();
} catch (\Throwable $e) {
    if (APP_DEBUG) {
        echo '<pre style="background:#1a1a1a;color:#ff6b6b;padding:20px">';
        echo htmlspecialchars($e::class . ': ' . $e->getMessage() . "\n" . $e->getTraceAsString());
        echo '</pre>';
    } else {
        http_response_code(500);
        echo '<h1>Erro interno do servidor</h1>';
    }
    \App\Lib\Logger::error('Unhandled exception', [
        'class'   => $e::class,
        'message' => $e->getMessage(),
        'file'    => $e->getFile() . ':' . $e->getLine(),
    ]);
}
