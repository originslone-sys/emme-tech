<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title><?= htmlspecialchars($pageTitle ?? 'Admin') ?> — EMME Tech Admin</title>
<link rel="stylesheet" href="/assets/css/app.css">
</head>
<body class="layout-admin">

<nav class="sidebar">
    <div class="sidebar-brand">
        <span class="brand-text"><span class="brand-emme">EMME</span> Tech Admin</span>
    </div>
    <ul class="sidebar-nav">
        <li class="<?= str_starts_with($_SERVER['REQUEST_URI'], '/admin/dashboard') ? 'active' : '' ?>">
            <a href="/admin/dashboard">📊 Dashboard</a>
        </li>
        <li class="<?= str_starts_with($_SERVER['REQUEST_URI'], '/admin/tenants') ? 'active' : '' ?>">
            <a href="/admin/tenants">🏢 Tenants</a>
        </li>
        <li class="<?= str_starts_with($_SERVER['REQUEST_URI'], '/admin/plans') ? 'active' : '' ?>">
            <a href="/admin/plans">💳 Planos</a>
        </li>
        <li class="<?= str_starts_with($_SERVER['REQUEST_URI'], '/admin/models') ? 'active' : '' ?>">
            <a href="/admin/models">🧠 Modelos de IA</a>
        </li>
        <li class="<?= str_starts_with($_SERVER['REQUEST_URI'], '/admin/audit') ? 'active' : '' ?>">
            <a href="/admin/audit">📋 Auditoria</a>
        </li>
        <li class="<?= str_starts_with($_SERVER['REQUEST_URI'], '/admin/logs') ? 'active' : '' ?>">
            <a href="/admin/logs">📄 Logs</a>
        </li>
    </ul>
    <div class="sidebar-footer">
        <span><?= htmlspecialchars($admin['name'] ?? '') ?></span>
        <a href="/admin/logout" class="btn-logout">Sair</a>
    </div>
</nav>

<div class="main-content">
    <header class="topbar">
        <h1><?= htmlspecialchars($pageTitle ?? 'Dashboard') ?></h1>
        <?php if ($flash = \App\Core\Session::flash('success')): ?>
            <div class="alert alert-success"><?= htmlspecialchars($flash) ?></div>
        <?php endif; ?>
        <?php if ($flash = \App\Core\Session::flash('error')): ?>
            <div class="alert alert-error"><?= htmlspecialchars($flash) ?></div>
        <?php endif; ?>
    </header>
    <div class="content-body">
        <?php /* The individual view is rendered here */ ?>
