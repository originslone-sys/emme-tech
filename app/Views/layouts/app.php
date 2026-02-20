<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title><?= htmlspecialchars($pageTitle ?? 'Dashboard') ?> — EMME Tech</title>
<link rel="stylesheet" href="/assets/css/app.css">
</head>
<body class="layout-app">

<nav class="sidebar">
    <div class="sidebar-brand">
        <span class="brand-text"><span class="brand-emme">EMME</span> Tech</span>
    </div>
    <ul class="sidebar-nav">
        <li class="<?= str_starts_with($_SERVER['REQUEST_URI'], '/app/dashboard') ? 'active' : '' ?>">
            <a href="/app/dashboard">🏠 Visão Geral</a>
        </li>
        <li class="<?= str_starts_with($_SERVER['REQUEST_URI'], '/app/agents') ? 'active' : '' ?>">
            <a href="/app/agents">🤖 Agentes</a>
        </li>
        <li class="<?= str_starts_with($_SERVER['REQUEST_URI'], '/app/personas') ? 'active' : '' ?>">
            <a href="/app/personas">🎭 Personas</a>
        </li>
        <li class="<?= str_starts_with($_SERVER['REQUEST_URI'], '/app/docs') ? 'active' : '' ?>">
            <a href="/app/docs">📚 Documentos / Memória</a>
        </li>
        <li class="<?= str_starts_with($_SERVER['REQUEST_URI'], '/app/crons') ? 'active' : '' ?>">
            <a href="/app/crons">⏰ Automações</a>
        </li>
        <li class="<?= str_starts_with($_SERVER['REQUEST_URI'], '/app/threads') ? 'active' : '' ?>">
            <a href="/app/threads">💬 Conversas</a>
        </li>
        <li class="<?= str_starts_with($_SERVER['REQUEST_URI'], '/app/billing') ? 'active' : '' ?>">
            <a href="/app/billing">💳 Assinatura</a>
        </li>
        <li class="<?= str_starts_with($_SERVER['REQUEST_URI'], '/app/settings') ? 'active' : '' ?>">
            <a href="/app/settings">⚙️ Configurações</a>
        </li>
    </ul>
    <div class="sidebar-footer">
        <span><?= htmlspecialchars($user['name'] ?? '') ?></span>
        <a href="/app/logout" class="btn-logout">Sair</a>
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
