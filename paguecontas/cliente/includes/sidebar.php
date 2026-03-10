<?php
$currentPage = basename($_SERVER['PHP_SELF'], '.php');
?>
<aside class="sidebar" id="sidebar">
    <div class="sidebar-header">
        <a href="index.php" class="sidebar-logo">
            <div class="logo-icon" style="width:36px;height:36px;background:var(--gradient-primary);border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:16px;">&#9889;</div>
            <span>Pague<span class="text-gradient">Contas</span></span>
        </a>
    </div>

    <nav class="sidebar-nav">
        <div class="sidebar-label">Principal</div>
        <a href="index.php" class="sidebar-link <?= $currentPage === 'index' ? 'active' : '' ?>">
            <span class="link-icon">&#127968;</span>
            Dashboard
        </a>
        <a href="pagar.php" class="sidebar-link <?= $currentPage === 'pagar' ? 'active' : '' ?>">
            <span class="link-icon">&#128179;</span>
            Pagar Conta
        </a>
        <a href="recarga.php" class="sidebar-link <?= $currentPage === 'recarga' ? 'active' : '' ?>">
            <span class="link-icon">&#128178;</span>
            Recarregar Saldo
        </a>

        <div class="sidebar-label">Financeiro</div>
        <a href="extrato.php" class="sidebar-link <?= $currentPage === 'extrato' ? 'active' : '' ?>">
            <span class="link-icon">&#128202;</span>
            Extrato
        </a>
        <a href="cashback.php" class="sidebar-link <?= $currentPage === 'cashback' ? 'active' : '' ?>">
            <span class="link-icon">&#128176;</span>
            Meu Cashback
        </a>

        <div class="sidebar-label">Conta</div>
        <a href="perfil.php" class="sidebar-link <?= $currentPage === 'perfil' ? 'active' : '' ?>">
            <span class="link-icon">&#128100;</span>
            Meu Perfil
        </a>
        <a href="notificacoes.php" class="sidebar-link <?= $currentPage === 'notificacoes' ? 'active' : '' ?>">
            <span class="link-icon">&#128276;</span>
            Notificações
            <?php
            if (isset($unreadNotifications) && $unreadNotifications > 0) {
                echo '<span class="link-badge">' . $unreadNotifications . '</span>';
            }
            ?>
        </a>
    </nav>

    <div class="sidebar-footer">
        <div class="sidebar-user">
            <div class="user-avatar">
                <?= strtoupper(substr($user['name'] ?? 'U', 0, 1)) ?>
            </div>
            <div class="user-info">
                <div class="user-name"><?= sanitize($user['name'] ?? 'Usuário') ?></div>
                <div class="user-email"><?= sanitize($user['email'] ?? '') ?></div>
            </div>
        </div>
        <a href="../logout.php" class="sidebar-link" style="margin-top: 8px; color: var(--danger);">
            <span class="link-icon">&#128682;</span>
            Sair
        </a>
    </div>
</aside>
