<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="theme-color" content="#0d1117">
    <meta name="msapplication-navbutton-color" content="#0d1117">
    <title>Nuvem - Armazenamento em Nuvem</title>
    <link rel="stylesheet" href="assets/css/style.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <link rel="manifest" href="data:application/json,{}">
</head>
<body>
    <!-- Tela de Login (oculta - uso pessoal) -->
    <div id="login-screen" class="login-screen" style="display:none">
        <div class="login-window">
            <div class="login-body">
                <div class="login-icon"><i class="fas fa-spinner fa-spin"></i></div>
                <h2>Carregando...</h2>
                <form id="login-form"><input type="hidden" id="login-password"><div id="login-error" class="login-error" style="display:none"></div></form>
            </div>
        </div>
    </div>

    <!-- Aplicacao Principal -->
    <div id="app" class="app">
        <!-- Desktop / Area de Trabalho -->
        <div class="desktop">
            <!-- Janela Principal -->
            <div class="window" id="main-window">
                <!-- Barra de Titulo -->
                <div class="window-titlebar" id="window-titlebar">
                    <div class="titlebar-left">
                        <i class="fas fa-cloud"></i>
                        <span id="window-title">Nuvem - Meus Arquivos</span>
                    </div>
                    <div class="titlebar-buttons">
                        <span class="btn-minimize" id="btn-minimize-window">&#9472;</span>
                        <span class="btn-maximize" id="btn-maximize-window">&#9723;</span>
                        <span class="btn-close" id="btn-close-app">&#10005;</span>
                    </div>
                </div>

                <!-- Barra de Ferramentas -->
                <div class="toolbar">
                    <!-- Mobile menu toggle -->
                    <button class="mobile-menu-btn" id="btn-mobile-menu" title="Menu">
                        <i class="fas fa-bars"></i>
                    </button>

                    <div class="toolbar-left">
                        <button class="tool-btn" id="btn-back" title="Voltar" disabled>
                            <i class="fas fa-arrow-left"></i>
                        </button>
                        <button class="tool-btn" id="btn-forward" title="Avancar" disabled>
                            <i class="fas fa-arrow-right"></i>
                        </button>
                        <button class="tool-btn" id="btn-up" title="Subir um nivel">
                            <i class="fas fa-arrow-up"></i>
                        </button>
                        <button class="tool-btn" id="btn-refresh" title="Atualizar">
                            <i class="fas fa-rotate-right"></i>
                        </button>
                    </div>

                    <!-- Barra de Caminho -->
                    <div class="path-bar">
                        <i class="fas fa-folder-open"></i>
                        <div id="breadcrumb" class="breadcrumb">
                            <span class="crumb" data-path="">Raiz</span>
                        </div>
                    </div>

                    <div class="toolbar-right">
                        <div class="search-box">
                            <i class="fas fa-search"></i>
                            <input type="text" id="search-input" placeholder="Buscar arquivos...">
                        </div>
                    </div>
                </div>

                <!-- Area de Acoes -->
                <div class="action-bar">
                    <button class="action-btn" id="btn-new-folder">
                        <i class="fas fa-folder-plus"></i> <span>Nova Pasta</span>
                    </button>
                    <button class="action-btn" id="btn-upload">
                        <i class="fas fa-cloud-arrow-up"></i> <span>Upload</span>
                    </button>
                    <div class="action-separator"></div>
                    <button class="action-btn" id="btn-view-grid" title="Grade">
                        <i class="fas fa-th-large"></i>
                    </button>
                    <button class="action-btn active" id="btn-view-list" title="Lista">
                        <i class="fas fa-list"></i>
                    </button>
                    <div class="action-separator"></div>
                    <button class="action-btn" id="btn-select-all" title="Selecionar todos">
                        <i class="fas fa-check-double"></i> <span>Selecionar</span>
                    </button>
                    <button class="action-btn danger" id="btn-delete-selected" title="Excluir selecionados" style="display:none">
                        <i class="fas fa-trash"></i> <span>Excluir</span>
                    </button>
                    <button class="action-btn" id="btn-download-selected" title="Baixar selecionados" style="display:none">
                        <i class="fas fa-download"></i> <span>Baixar</span>
                    </button>
                </div>

                <!-- Conteudo Principal -->
                <div class="window-content">
                    <!-- Sidebar overlay (mobile) -->
                    <div class="sidebar-overlay" id="sidebar-overlay"></div>

                    <!-- Painel Lateral -->
                    <div class="sidebar" id="sidebar">
                        <button class="sidebar-close-btn" id="btn-sidebar-close">
                            <i class="fas fa-times"></i> Fechar Menu
                        </button>
                        <div class="sidebar-section">
                            <h3><i class="fas fa-star"></i> Acesso Rapido</h3>
                            <ul>
                                <li class="sidebar-item active" data-path="">
                                    <i class="fas fa-home"></i> Raiz
                                </li>
                            </ul>
                        </div>
                        <div class="sidebar-section">
                            <h3><i class="fas fa-hdd"></i> Storage</h3>
                            <div class="storage-info">
                                <div class="storage-bar">
                                    <div class="storage-used" id="storage-used-bar" style="width:0%"></div>
                                </div>
                                <span class="storage-text" id="storage-text">Calculando...</span>
                            </div>
                        </div>
                    </div>

                    <!-- Area de Arquivos -->
                    <div class="file-area" id="file-area">
                        <!-- Header da lista -->
                        <div class="file-list-header" id="file-list-header">
                            <div class="col-check"><input type="checkbox" id="check-all"></div>
                            <div class="col-icon"></div>
                            <div class="col-name" data-sort="name">Nome <i class="fas fa-sort"></i></div>
                            <div class="col-size" data-sort="size">Tamanho <i class="fas fa-sort"></i></div>
                            <div class="col-date" data-sort="date">Modificado <i class="fas fa-sort"></i></div>
                            <div class="col-actions">Acoes</div>
                        </div>

                        <!-- Carregando -->
                        <div class="loading" id="loading">
                            <i class="fas fa-spinner fa-spin"></i>
                            <span>Carregando arquivos...</span>
                        </div>

                        <!-- Lista de Arquivos -->
                        <div class="file-list" id="file-list"></div>
                    </div>
                </div>

                <!-- Barra de Status -->
                <div class="statusbar">
                    <span id="status-items">0 itens</span>
                    <span id="status-selected"></span>
                    <span id="status-path">Raiz</span>
                </div>
            </div>
        </div>

        <!-- Barra de Tarefas (Windows-style) -->
        <div class="taskbar">
            <div class="taskbar-left">
                <button class="start-btn" id="btn-start">
                    <i class="fas fa-cloud"></i> <span>Nuvem</span>
                </button>
            </div>
            <div class="taskbar-center">
                <div class="taskbar-item active" id="taskbar-window">
                    <i class="fas fa-folder"></i> <span>Meus Arquivos</span>
                </div>
            </div>
            <div class="taskbar-right">
                <span class="taskbar-clock" id="taskbar-clock"></span>
                <button class="taskbar-btn" id="btn-logout" title="Sair">
                    <i class="fas fa-power-off"></i>
                </button>
            </div>
        </div>
    </div>

    <!-- Upload Area (Drag & Drop Overlay) -->
    <div class="drop-overlay" id="drop-overlay" style="display:none">
        <div class="drop-content">
            <i class="fas fa-cloud-arrow-up"></i>
            <h2>Solte os arquivos aqui</h2>
            <p>Os arquivos serao enviados para a pasta atual</p>
        </div>
    </div>

    <!-- Menu de Contexto (desktop) -->
    <div class="context-menu" id="context-menu" style="display:none">
        <div class="context-item" data-action="open"><i class="fas fa-folder-open"></i> Abrir</div>
        <div class="context-item" data-action="download"><i class="fas fa-download"></i> Baixar</div>
        <div class="context-separator"></div>
        <div class="context-item" data-action="rename"><i class="fas fa-pen"></i> Renomear</div>
        <div class="context-item" data-action="move"><i class="fas fa-arrows-alt"></i> Mover para...</div>
        <div class="context-separator"></div>
        <div class="context-item" data-action="info"><i class="fas fa-info-circle"></i> Propriedades</div>
        <div class="context-separator"></div>
        <div class="context-item danger" data-action="delete"><i class="fas fa-trash"></i> Excluir</div>
    </div>

    <!-- Menu de Contexto da Area Vazia (desktop) -->
    <div class="context-menu" id="area-context-menu" style="display:none">
        <div class="context-item" data-action="new-folder"><i class="fas fa-folder-plus"></i> Nova Pasta</div>
        <div class="context-item" data-action="upload"><i class="fas fa-cloud-arrow-up"></i> Upload</div>
        <div class="context-separator"></div>
        <div class="context-item" data-action="refresh"><i class="fas fa-rotate-right"></i> Atualizar</div>
        <div class="context-separator"></div>
        <div class="context-item" data-action="select-all"><i class="fas fa-check-double"></i> Selecionar Tudo</div>
    </div>

    <!-- Bottom Sheet (mobile context menu) -->
    <div class="bottom-sheet-overlay" id="bottom-sheet-overlay"></div>
    <div class="bottom-sheet" id="bottom-sheet">
        <div class="bottom-sheet-handle"></div>
        <div id="bottom-sheet-content"></div>
    </div>

    <!-- Modal de Dialogo -->
    <div class="modal-overlay" id="modal-overlay" style="display:none">
        <div class="modal-window" id="modal-window">
            <div class="modal-titlebar">
                <span id="modal-title">Dialogo</span>
                <span class="btn-close" id="modal-close">&#10005;</span>
            </div>
            <div class="modal-body" id="modal-body"></div>
            <div class="modal-footer" id="modal-footer"></div>
        </div>
    </div>

    <!-- Upload Progress (multi-file queue) -->
    <div class="upload-progress-container" id="upload-progress" style="display:none">
        <div class="upload-progress-window">
            <div class="upload-progress-titlebar">
                <span><i class="fas fa-upload"></i> <span id="upload-title">Enviando arquivos</span></span>
                <div class="upload-titlebar-actions">
                    <span class="upload-toggle" id="upload-toggle" title="Minimizar"><i class="fas fa-chevron-down"></i></span>
                    <span class="btn-close" id="upload-cancel" title="Fechar">&#10005;</span>
                </div>
            </div>
            <div class="upload-summary" id="upload-summary">
                <div class="upload-summary-bar-container">
                    <div class="upload-summary-bar" id="upload-summary-bar"></div>
                </div>
                <span class="upload-summary-text" id="upload-summary-text">0 de 0 arquivos</span>
            </div>
            <div class="upload-file-list" id="upload-file-list">
                <!-- Items inserted by JS -->
            </div>
        </div>
    </div>

    <div class="upload-progress-container" id="download-progress" style="display:none">
        <div class="upload-progress-window">
            <div class="upload-progress-titlebar">
                <span><i class="fas fa-download"></i> <span id="download-title">Baixando arquivos</span></span>
                <div class="upload-titlebar-actions">
                    <span class="upload-toggle" id="download-toggle" title="Minimizar"><i class="fas fa-chevron-down"></i></span>
                    <span class="btn-close" id="download-cancel" title="Fechar">&#10005;</span>
                </div>
            </div>
            <div class="upload-summary" id="download-summary">
                <div class="upload-summary-bar-container">
                    <div class="upload-summary-bar" id="download-summary-bar"></div>
                </div>
                <span class="upload-summary-text" id="download-summary-text">0 de 0 arquivos</span>
            </div>
            <div class="upload-file-list" id="download-file-list">
                <!-- Items inserted by JS -->
            </div>
        </div>
    </div>

    <!-- Input de arquivo oculto -->
    <input type="file" id="file-input" style="display:none" multiple>

    <script src="assets/js/app.js"></script>
</body>
</html>
