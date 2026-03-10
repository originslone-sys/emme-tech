<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PagueContas - Pague suas contas e ganhe cashback!</title>
    <meta name="description" content="PagueContas: pague boletos, contas de energia, água e muito mais. Ganhe 5% de cashback em cada pagamento!">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="assets/css/style.css">
</head>
<body>

    <!-- Navigation -->
    <nav class="navbar" id="navbar">
        <div class="nav-container">
            <a href="index.php" class="nav-logo">
                <div class="logo-icon">&#9889;</div>
                <span>Pague<span class="text-gradient">Contas</span></span>
            </a>

            <div class="nav-links" id="navLinks">
                <a href="#features">Recursos</a>
                <a href="#how-it-works">Como Funciona</a>
                <a href="#cashback">Cashback</a>
                <a href="#faq">FAQ</a>
            </div>

            <div class="nav-actions">
                <a href="login.php" class="btn btn-secondary btn-sm">Entrar</a>
                <a href="register.php" class="btn btn-primary btn-sm">Criar Conta</a>
            </div>

            <div class="nav-toggle" id="navToggle" onclick="document.getElementById('navLinks').classList.toggle('active')">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    </nav>

    <!-- Hero Section -->
    <section class="hero">
        <div class="hero-container">
            <div class="hero-content">
                <div class="hero-badge">
                    <span class="badge-dot"></span>
                    Plataforma 100% Digital
                </div>
                <h1>Pague suas contas e ganhe <span class="text-gradient">5% de cashback</span></h1>
                <p>Boletos, energia, água, gás, telefone e muito mais. Cada pagamento retorna dinheiro para sua carteira digital. Simples, rápido e seguro.</p>

                <div class="hero-buttons">
                    <a href="register.php" class="btn btn-primary btn-lg">Começar Agora &#10132;</a>
                    <a href="#how-it-works" class="btn btn-secondary btn-lg">Como Funciona</a>
                </div>

                <div class="hero-stats">
                    <div class="hero-stat">
                        <div class="stat-value" data-count="15000" data-suffix="+" data-prefix="">15.000+</div>
                        <div class="stat-label">Clientes Ativos</div>
                    </div>
                    <div class="hero-stat">
                        <div class="stat-value" data-count="2500000" data-prefix="R$ " data-suffix="">R$ 2.500.000</div>
                        <div class="stat-label">Cashback Distribuído</div>
                    </div>
                    <div class="hero-stat">
                        <div class="stat-value" data-count="500000" data-suffix="+" data-prefix="">500.000+</div>
                        <div class="stat-label">Contas Pagas</div>
                    </div>
                </div>
            </div>

            <div class="hero-visual">
                <!-- Floating Cards -->
                <div class="float-card cashback">
                    <div class="cashback-icon">&#128176;</div>
                    <div>
                        <div class="cashback-text">Cashback recebido</div>
                        <div class="cashback-value">+ R$ 12,50</div>
                    </div>
                </div>

                <div class="float-card security">
                    <div class="security-icon">&#128274;</div>
                    <div class="security-text">Pagamento Seguro</div>
                </div>

                <!-- Phone Mockup -->
                <div class="hero-phone">
                    <div class="phone-notch"></div>
                    <div class="phone-header">
                        <div class="greeting">Olá, bem-vindo!</div>
                        <div class="user-name">João Silva</div>
                    </div>
                    <div class="phone-balance">
                        <div class="balance-label">Saldo Disponível</div>
                        <div class="balance-value">R$ 1.250,00</div>
                        <div class="cashback-info">&#127775; Cashback: R$ 62,50</div>
                    </div>
                    <div class="phone-actions">
                        <div class="phone-action">
                            <div class="action-icon">&#128179;</div>
                            <div class="action-label">Pagar</div>
                        </div>
                        <div class="phone-action">
                            <div class="action-icon">&#128178;</div>
                            <div class="action-label">Recarga</div>
                        </div>
                        <div class="phone-action">
                            <div class="action-icon">&#128200;</div>
                            <div class="action-label">Extrato</div>
                        </div>
                        <div class="phone-action">
                            <div class="action-icon">&#128176;</div>
                            <div class="action-label">Cashback</div>
                        </div>
                    </div>
                    <div class="phone-transaction">
                        <div class="tx-icon deposit">&#128178;</div>
                        <div class="tx-info">
                            <div class="tx-title">Recarga PIX</div>
                            <div class="tx-date">Hoje, 14:30</div>
                        </div>
                        <div class="tx-amount positive">+ R$ 500,00</div>
                    </div>
                    <div class="phone-transaction">
                        <div class="tx-icon payment">&#128161;</div>
                        <div class="tx-info">
                            <div class="tx-title">Conta de Energia</div>
                            <div class="tx-date">Hoje, 15:02</div>
                        </div>
                        <div class="tx-amount negative">- R$ 250,00</div>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <!-- Features Section -->
    <section class="section" id="features">
        <div class="container">
            <div class="section-header">
                <span class="section-label">&#9889; Recursos</span>
                <h2>Tudo que você precisa em <span class="text-gradient">um só lugar</span></h2>
                <p>Uma plataforma completa para gerenciar seus pagamentos com facilidade e ainda ganhar dinheiro de volta.</p>
            </div>

            <div class="features-grid">
                <div class="feature-card">
                    <div class="feature-icon purple">&#128179;</div>
                    <h3>Pague Boletos</h3>
                    <p>Pague qualquer boleto bancário com código de barras diretamente pela plataforma.</p>
                </div>
                <div class="feature-card">
                    <div class="feature-icon green">&#128161;</div>
                    <h3>Contas de Energia</h3>
                    <p>Pague suas contas de luz de forma rápida e receba cashback automaticamente.</p>
                </div>
                <div class="feature-card">
                    <div class="feature-icon blue">&#128167;</div>
                    <h3>Contas de Água</h3>
                    <p>Mantenha suas contas de água em dia com pagamento instantâneo.</p>
                </div>
                <div class="feature-card">
                    <div class="feature-icon pink">&#128176;</div>
                    <h3>5% de Cashback</h3>
                    <p>Cada conta paga retorna 5% do valor para sua carteira digital.</p>
                </div>
                <div class="feature-card">
                    <div class="feature-icon yellow">&#128178;</div>
                    <h3>Recarga Rápida</h3>
                    <p>Recarregue seu saldo via PIX, cartão de crédito ou transferência bancária.</p>
                </div>
                <div class="feature-card">
                    <div class="feature-icon purple">&#128202;</div>
                    <h3>Extrato Completo</h3>
                    <p>Acompanhe todas suas movimentações, entradas, saídas e cashback em tempo real.</p>
                </div>
            </div>
        </div>
    </section>

    <!-- How It Works -->
    <section class="section" id="how-it-works" style="background: var(--dark-card); border-top: 1px solid var(--dark-border); border-bottom: 1px solid var(--dark-border);">
        <div class="container">
            <div class="section-header">
                <span class="section-label">&#128640; Como Funciona</span>
                <h2>Comece em <span class="text-gradient">4 passos simples</span></h2>
                <p>É fácil, rápido e seguro. Crie sua conta e comece a economizar com cashback.</p>
            </div>

            <div class="steps-grid">
                <div class="step-card">
                    <div class="step-number">1</div>
                    <h3>Crie sua Conta</h3>
                    <p>Cadastre-se gratuitamente com seu e-mail e senha em menos de 1 minuto.</p>
                </div>
                <div class="step-card">
                    <div class="step-number">2</div>
                    <h3>Recarregue</h3>
                    <p>Adicione saldo à sua conta via PIX, cartão ou transferência.</p>
                </div>
                <div class="step-card">
                    <div class="step-number">3</div>
                    <h3>Pague Contas</h3>
                    <p>Digite o código de barras da conta e confirme o pagamento.</p>
                </div>
                <div class="step-card">
                    <div class="step-number">4</div>
                    <h3>Receba Cashback</h3>
                    <p>Ganhe 5% de volta automaticamente em cada pagamento realizado.</p>
                </div>
            </div>
        </div>
    </section>

    <!-- Cashback Section -->
    <section class="section cashback-section" id="cashback">
        <div class="container">
            <div class="cashback-grid">
                <div class="cashback-content">
                    <span class="section-label">&#128176; Cashback</span>
                    <h2>Ganhe <span class="text-gradient">5% de volta</span> em cada pagamento</h2>
                    <p>Nosso sistema de cashback é automático. Cada conta paga retorna 5% do valor diretamente para sua carteira digital, sem burocracia.</p>

                    <div class="cashback-features">
                        <div class="cashback-feature">
                            <div class="check-icon">&#10003;</div>
                            <span>Cashback creditado automaticamente</span>
                        </div>
                        <div class="cashback-feature">
                            <div class="check-icon">&#10003;</div>
                            <span>Use o saldo de cashback para pagar outras contas</span>
                        </div>
                        <div class="cashback-feature">
                            <div class="check-icon">&#10003;</div>
                            <span>Sem limite de cashback por mês</span>
                        </div>
                        <div class="cashback-feature">
                            <div class="check-icon">&#10003;</div>
                            <span>Acompanhe seus ganhos em tempo real</span>
                        </div>
                    </div>

                    <a href="register.php" class="btn btn-success btn-lg">Quero Ganhar Cashback &#10132;</a>
                </div>

                <div class="cashback-visual">
                    <div class="cashback-big-number">5%</div>
                    <div class="cashback-card-demo">
                        <div class="demo-icon">&#127881;</div>
                        <div class="demo-label">Conta de R$ 250,00</div>
                        <div class="demo-value">+ R$ 12,50</div>
                        <div class="demo-desc">de cashback creditado na sua conta</div>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <!-- FAQ Section -->
    <section class="section" id="faq">
        <div class="container">
            <div class="section-header">
                <span class="section-label">&#10068; FAQ</span>
                <h2>Perguntas <span class="text-gradient">Frequentes</span></h2>
                <p>Tire suas dúvidas sobre a plataforma PagueContas.</p>
            </div>

            <div style="max-width: 720px; margin: 0 auto;">
                <div class="feature-card" style="margin-bottom: 16px; padding: 24px 28px; cursor: pointer;" onclick="this.querySelector('.faq-answer').style.display = this.querySelector('.faq-answer').style.display === 'block' ? 'none' : 'block'">
                    <h3 style="font-size: 17px; display: flex; justify-content: space-between; align-items: center;">
                        Como funciona o cashback?
                        <span style="font-size: 20px; color: var(--primary-light);">+</span>
                    </h3>
                    <div class="faq-answer" style="display: none; margin-top: 12px;">
                        <p>A cada conta paga pela plataforma, 5% do valor é creditado automaticamente na sua carteira de cashback. Você pode usar esse saldo para pagar outras contas.</p>
                    </div>
                </div>
                <div class="feature-card" style="margin-bottom: 16px; padding: 24px 28px; cursor: pointer;" onclick="this.querySelector('.faq-answer').style.display = this.querySelector('.faq-answer').style.display === 'block' ? 'none' : 'block'">
                    <h3 style="font-size: 17px; display: flex; justify-content: space-between; align-items: center;">
                        Quais contas posso pagar?
                        <span style="font-size: 20px; color: var(--primary-light);">+</span>
                    </h3>
                    <div class="faq-answer" style="display: none; margin-top: 12px;">
                        <p>Você pode pagar boletos bancários, contas de energia, água, gás, telefone, internet e qualquer conta que possua código de barras digitável.</p>
                    </div>
                </div>
                <div class="feature-card" style="margin-bottom: 16px; padding: 24px 28px; cursor: pointer;" onclick="this.querySelector('.faq-answer').style.display = this.querySelector('.faq-answer').style.display === 'block' ? 'none' : 'block'">
                    <h3 style="font-size: 17px; display: flex; justify-content: space-between; align-items: center;">
                        Como recarregar meu saldo?
                        <span style="font-size: 20px; color: var(--primary-light);">+</span>
                    </h3>
                    <div class="faq-answer" style="display: none; margin-top: 12px;">
                        <p>Você pode recarregar via PIX (instantâneo), cartão de crédito ou transferência bancária. O saldo é creditado após confirmação do pagamento.</p>
                    </div>
                </div>
                <div class="feature-card" style="margin-bottom: 16px; padding: 24px 28px; cursor: pointer;" onclick="this.querySelector('.faq-answer').style.display = this.querySelector('.faq-answer').style.display === 'block' ? 'none' : 'block'">
                    <h3 style="font-size: 17px; display: flex; justify-content: space-between; align-items: center;">
                        É seguro usar a plataforma?
                        <span style="font-size: 20px; color: var(--primary-light);">+</span>
                    </h3>
                    <div class="faq-answer" style="display: none; margin-top: 12px;">
                        <p>Sim! Utilizamos criptografia de ponta a ponta, autenticação segura e todos os seus dados são protegidos seguindo as melhores práticas de segurança.</p>
                    </div>
                </div>
                <div class="feature-card" style="margin-bottom: 16px; padding: 24px 28px; cursor: pointer;" onclick="this.querySelector('.faq-answer').style.display = this.querySelector('.faq-answer').style.display === 'block' ? 'none' : 'block'">
                    <h3 style="font-size: 17px; display: flex; justify-content: space-between; align-items: center;">
                        Existe limite de cashback?
                        <span style="font-size: 20px; color: var(--primary-light);">+</span>
                    </h3>
                    <div class="faq-answer" style="display: none; margin-top: 12px;">
                        <p>Não! Não há limite de cashback. Quanto mais contas você pagar, mais cashback acumula. Simples assim.</p>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <!-- CTA Section -->
    <section class="section cta-section">
        <div class="container">
            <div class="cta-box">
                <h2>Comece a <span class="text-gradient">economizar</span> hoje</h2>
                <p>Crie sua conta gratuita e ganhe cashback em cada conta paga.</p>
                <a href="register.php" class="btn btn-primary btn-lg">Criar Conta Grátis &#10132;</a>
            </div>
        </div>
    </section>

    <!-- Footer -->
    <footer class="footer">
        <div class="container">
            <div class="footer-grid">
                <div class="footer-brand">
                    <div class="footer-logo">
                        <div class="logo-icon" style="width:36px;height:36px;background:var(--gradient-primary);border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:16px;">&#9889;</div>
                        <span>Pague<span class="text-gradient">Contas</span></span>
                    </div>
                    <p>A melhor plataforma para pagamento de contas com cashback. Pague suas contas e receba dinheiro de volta.</p>
                </div>
                <div class="footer-col">
                    <h4>Plataforma</h4>
                    <ul>
                        <li><a href="#features">Recursos</a></li>
                        <li><a href="#how-it-works">Como Funciona</a></li>
                        <li><a href="#cashback">Cashback</a></li>
                        <li><a href="#faq">FAQ</a></li>
                    </ul>
                </div>
                <div class="footer-col">
                    <h4>Conta</h4>
                    <ul>
                        <li><a href="register.php">Criar Conta</a></li>
                        <li><a href="login.php">Fazer Login</a></li>
                    </ul>
                </div>
                <div class="footer-col">
                    <h4>Suporte</h4>
                    <ul>
                        <li><a href="#">Central de Ajuda</a></li>
                        <li><a href="#">Contato</a></li>
                        <li><a href="#">Termos de Uso</a></li>
                        <li><a href="#">Privacidade</a></li>
                    </ul>
                </div>
            </div>
            <div class="footer-bottom">
                <p>&copy; 2026 PagueContas. Todos os direitos reservados.</p>
                <p>Feito com &#128156; no Brasil</p>
            </div>
        </div>
    </footer>

    <script src="assets/js/main.js"></script>
</body>
</html>
