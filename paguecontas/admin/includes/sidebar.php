<?php
$currentPage = basename($_SERVER['PHP_SELF'], '.php');
?>
<aside class="sidebar admin-sidebar" id="sidebar">
    <div class="sidebar-header">
        <a href="index.php" class="sidebar-logo">
            <div class="logo-icon" style="width:36px;height:36px;background:var(--gradient-primary);border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:16px;">&#9889;</div>
            <span>Pague<span class="text-gradient">Contas</span></span>
        </a>
        <div style="margin-top: 8px; padding: 4px 10px; background: rgba(247, 37, 133, 0.15); border-radius: 20px; display: inline-flex; font-size: 11px; font-weight: 700; color: var(--accent); text-transform: uppercase; letter-spacing: 1px;">Admin</div>
    </div>

    <nav class="sidebar-nav">
        <div class="sidebar-label">Painel</div>
        <a href="index.php" class="sidebar-link <?= $currentPage === 'index' ? 'active' : '' ?>">
            <span class="link-icon">&#128202;</span>
            Dashboard
        </a>

        <div class="sidebar-label">Gerenciamento</div>
        <a href="usuarios.php" class="sidebar-link <?= $currentPage === 'usuarios' ? 'active' : '' ?>">
            <span class="link-icon">&#128101;</span>
            Usuários
        </a>
        <a href="recargas.php" class="sidebar-link <?= $currentPage === 'recargas' ? 'active' : '' ?>">
            <span class="link-icon">&#128178;</span>
            Recargas
            <?php
            if (isset($pendingRecharges) && $pendingRecharges > 0) {
                echo '<span class="link-badge">' . $pendingRecharges . '</span>';
            }
            ?>
        </a>
        <a href="transacoes.php" class="sidebar-link <?= $currentPage === 'transacoes' ? 'active' : '' ?>">
            <span class="link-icon">&#128179;</span>
            Transações
        </a>

        <div class="sidebar-label">Sistema</div>
        <a href="configuracoes.php" class="sidebar-link <?= $currentPage === 'configuracoes' ? 'active' : '' ?>">
            <span class="link-icon">&#9881;</span>
            Configurações
        </a>
    </nav>

    <div class="sidebar-footer">
        <div class="sidebar-user">
            <div class="user-avatar" style="background: var(--accent);">A</div>
            <div class="user-info">
                <div class="user-name"><?= sanitize($_SESSION['user_name'] ?? 'Admin') ?></div>
                <div class="user-email">Administrador</div>
            </div>
        </div>
        <a href="../logout.php" class="sidebar-link" style="margin-top: 8px; color: var(--danger);">
            <span class="link-icon">&#128682;</span>
            Sair
        </a>
    </div>
</aside>
