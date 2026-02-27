/**
 * NUVEM - Cloud Storage Application
 * Frontend JavaScript - Windows-style File Manager
 */

(function () {
    'use strict';

    // === Estado da Aplicacao ===
    const state = {
        currentPath: '',
        history: [],
        historyIndex: -1,
        files: [],
        folders: [],
        selectedItems: new Set(),
        viewMode: 'list', // 'list' ou 'grid'
        sortBy: 'name',
        sortDir: 'asc',
        contextTarget: null,
        isAuthenticated: false,
    };

    // === API Helper ===
    const api = {
        async request(action, options = {}) {
            const url = `api/${action}`;
            try {
                const response = await fetch(url, {
                    credentials: 'same-origin',
                    ...options,
                });
                const data = await response.json();
                if (!response.ok) {
                    throw new Error(data.error || 'Erro desconhecido');
                }
                return data;
            } catch (err) {
                if (err.message.includes('Nao autenticado')) {
                    showLogin();
                }
                throw err;
            }
        },

        async list(path = '') {
            return this.request(`list&path=${encodeURIComponent(path)}`);
        },

        async createFolder(path) {
            return this.request('create-folder', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path }),
            });
        },

        async rename(oldPath, newPath) {
            return this.request('rename', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ oldPath, newPath }),
            });
        },

        async deleteItem(path) {
            return this.request('delete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path }),
            });
        },

        async upload(file, path) {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('path', path);
            return this.request('upload', {
                method: 'POST',
                body: formData,
            });
        },

        async download(path) {
            return this.request(`download&path=${encodeURIComponent(path)}`);
        },

        async move(oldPath, newPath) {
            return this.request('move', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ oldPath, newPath }),
            });
        },

        async getInfo(path) {
            return this.request(`info&path=${encodeURIComponent(path)}`);
        },

        async login(password) {
            return this.request('login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ password }),
            });
        },

        async checkAuth() {
            return this.request('check-auth');
        },

        async logout() {
            return this.request('logout');
        },
    };

    // === Elementos DOM ===
    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => document.querySelectorAll(sel);

    // === Inicializacao ===
    async function init() {
        setupClock();
        setupEventListeners();
        setupDragDrop();

        try {
            const auth = await api.checkAuth();
            if (auth.authenticated) {
                showApp();
                await navigateTo('');
            } else {
                // Auto-login (uso pessoal, sem senha)
                await api.login('');
                showApp();
                await navigateTo('');
            }
        } catch {
            // Fallback: tentar login direto
            try {
                await api.login('');
                showApp();
                await navigateTo('');
            } catch {
                showLogin();
            }
        }
    }

    // === Autenticacao ===
    function showLogin() {
        state.isAuthenticated = false;
        $('#login-screen').style.display = 'flex';
        $('#app').style.display = 'none';
        $('#login-password').focus();
    }

    function showApp() {
        state.isAuthenticated = true;
        $('#login-screen').style.display = 'none';
        $('#app').style.display = 'flex';
    }

    // === Navegacao ===
    async function navigateTo(path, addToHistory = true) {
        state.currentPath = path;
        state.selectedItems.clear();
        updateSelectionUI();
        showLoading(true);

        try {
            const data = await api.list(path);
            state.folders = data.folders || [];
            state.files = data.files || [];

            if (addToHistory) {
                // Remover entradas futuras se voltamos no historico
                if (state.historyIndex < state.history.length - 1) {
                    state.history = state.history.slice(0, state.historyIndex + 1);
                }
                state.history.push(path);
                state.historyIndex = state.history.length - 1;
            }

            renderFiles();
            updateBreadcrumb();
            updateNavButtons();
            updateStatus();
            updateWindowTitle();
        } catch (err) {
            toast('Erro ao carregar arquivos: ' + err.message, 'error');
        } finally {
            showLoading(false);
        }
    }

    function goBack() {
        if (state.historyIndex > 0) {
            state.historyIndex--;
            navigateTo(state.history[state.historyIndex], false);
        }
    }

    function goForward() {
        if (state.historyIndex < state.history.length - 1) {
            state.historyIndex++;
            navigateTo(state.history[state.historyIndex], false);
        }
    }

    function goUp() {
        if (state.currentPath) {
            const parts = state.currentPath.replace(/\/$/, '').split('/');
            parts.pop();
            const parentPath = parts.length > 0 ? parts.join('/') + '/' : '';
            navigateTo(parentPath);
        }
    }

    // === Renderizacao ===
    function renderFiles() {
        const fileList = $('#file-list');
        const searchTerm = ($('#search-input').value || '').toLowerCase();

        let folders = [...state.folders];
        let files = [...state.files];

        // Filtrar por busca
        if (searchTerm) {
            folders = folders.filter((f) => f.name.toLowerCase().includes(searchTerm));
            files = files.filter((f) => f.name.toLowerCase().includes(searchTerm));
        }

        // Ordenar
        const sortFn = getSortFunction();
        folders.sort(sortFn);
        files.sort(sortFn);

        if (folders.length === 0 && files.length === 0) {
            fileList.innerHTML = '';
            const emptyEl = document.createElement('div');
            emptyEl.className = 'empty-state';
            emptyEl.innerHTML = `
                <i class="fas fa-folder-open"></i>
                <h3>Pasta vazia</h3>
                <p>Arraste arquivos aqui ou clique em "Upload"</p>
            `;
            fileList.appendChild(emptyEl);
            return;
        }

        fileList.innerHTML = '';

        // Renderizar pastas
        folders.forEach((folder) => {
            fileList.appendChild(createFileItem(folder));
        });

        // Renderizar arquivos
        files.forEach((file) => {
            fileList.appendChild(createFileItem(file));
        });

        // Aplicar modo de visualizacao
        if (state.viewMode === 'grid') {
            fileList.classList.add('grid-view');
            $('#file-list-header').style.display = 'none';
        } else {
            fileList.classList.remove('grid-view');
            $('#file-list-header').style.display = 'flex';
        }
    }

    function createFileItem(item) {
        const div = document.createElement('div');
        div.className = 'file-item';
        div.dataset.path = item.path;
        div.dataset.type = item.type;
        div.dataset.name = item.name;

        if (state.selectedItems.has(item.path)) {
            div.classList.add('selected');
        }

        const isFolder = item.type === 'folder';
        const icon = isFolder ? getFolderIcon() : getFileIcon(item.extension || '');
        const size = isFolder ? '--' : formatSize(item.size);
        const date = isFolder ? '' : (item.lastModified || '');

        div.innerHTML = `
            <div class="col-check"><input type="checkbox" ${state.selectedItems.has(item.path) ? 'checked' : ''}></div>
            <div class="col-icon">${icon}</div>
            <div class="col-name">${escapeHtml(item.name)}</div>
            <div class="col-size">${size}</div>
            <div class="col-date">${date}</div>
            <div class="col-actions">
                ${!isFolder ? '<button class="download-btn" title="Baixar"><i class="fas fa-download"></i></button>' : ''}
                <button class="rename-btn" title="Renomear"><i class="fas fa-pen"></i></button>
                <button class="delete-btn" title="Excluir"><i class="fas fa-trash"></i></button>
            </div>
        `;

        // Eventos
        div.addEventListener('dblclick', (e) => {
            e.preventDefault();
            if (isFolder) {
                navigateTo(item.path);
            } else {
                downloadFile(item.path);
            }
        });

        div.addEventListener('click', (e) => {
            if (e.target.closest('.col-actions') || e.target.tagName === 'INPUT') return;

            if (e.ctrlKey || e.metaKey) {
                toggleSelection(item.path);
            } else {
                state.selectedItems.clear();
                state.selectedItems.add(item.path);
                updateSelectionUI();
            }
        });

        div.addEventListener('contextmenu', (e) => {
            e.preventDefault();
            state.contextTarget = item;
            if (!state.selectedItems.has(item.path)) {
                state.selectedItems.clear();
                state.selectedItems.add(item.path);
                updateSelectionUI();
            }
            showContextMenu(e.clientX, e.clientY, 'item');
        });

        // Checkbox
        const checkbox = div.querySelector('input[type="checkbox"]');
        checkbox.addEventListener('change', () => {
            toggleSelection(item.path);
        });

        // Botoes de acao
        const downloadBtn = div.querySelector('.download-btn');
        if (downloadBtn) {
            downloadBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                downloadFile(item.path);
            });
        }

        const renameBtn = div.querySelector('.rename-btn');
        renameBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            showRenameDialog(item);
        });

        const deleteBtn = div.querySelector('.delete-btn');
        deleteBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            showDeleteConfirm(item);
        });

        return div;
    }

    // === Selecao ===
    function toggleSelection(path) {
        if (state.selectedItems.has(path)) {
            state.selectedItems.delete(path);
        } else {
            state.selectedItems.add(path);
        }
        updateSelectionUI();
    }

    function selectAll() {
        state.selectedItems.clear();
        state.folders.forEach((f) => state.selectedItems.add(f.path));
        state.files.forEach((f) => state.selectedItems.add(f.path));
        updateSelectionUI();
    }

    function updateSelectionUI() {
        const items = $$('.file-item');
        items.forEach((item) => {
            const path = item.dataset.path;
            const isSelected = state.selectedItems.has(path);
            item.classList.toggle('selected', isSelected);
            const cb = item.querySelector('input[type="checkbox"]');
            if (cb) cb.checked = isSelected;
        });

        const count = state.selectedItems.size;
        const deleteBtn = $('#btn-delete-selected');
        deleteBtn.style.display = count > 0 ? 'flex' : 'none';

        const checkAll = $('#check-all');
        const totalItems = state.folders.length + state.files.length;
        checkAll.checked = totalItems > 0 && count === totalItems;
        checkAll.indeterminate = count > 0 && count < totalItems;

        $('#status-selected').textContent = count > 0 ? `${count} selecionado(s)` : '';
    }

    // === Acoes de Arquivo ===
    async function downloadFile(path) {
        try {
            const data = await api.download(path);
            if (data.url) {
                window.open(data.url, '_blank');
            }
        } catch (err) {
            toast('Erro ao baixar arquivo: ' + err.message, 'error');
        }
    }

    async function uploadFiles(files) {
        if (!files || files.length === 0) return;

        const progressContainer = $('#upload-progress');

        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            $('#upload-file-name').textContent = `${file.name} (${i + 1}/${files.length})`;
            $('#upload-bar').style.width = '0%';
            $('#upload-percent').textContent = '0%';
            progressContainer.style.display = 'block';

            try {
                // Simular progresso (fetch nao tem progresso nativo de upload)
                let progress = 0;
                const progressInterval = setInterval(() => {
                    progress = Math.min(progress + Math.random() * 15, 90);
                    $('#upload-bar').style.width = progress + '%';
                    $('#upload-percent').textContent = Math.round(progress) + '%';
                }, 200);

                await api.upload(file, state.currentPath);

                clearInterval(progressInterval);
                $('#upload-bar').style.width = '100%';
                $('#upload-percent').textContent = '100%';

                toast(`"${file.name}" enviado com sucesso`, 'success');
            } catch (err) {
                toast(`Erro ao enviar "${file.name}": ${err.message}`, 'error');
            }
        }

        setTimeout(() => {
            progressContainer.style.display = 'none';
        }, 1000);

        await navigateTo(state.currentPath);
    }

    // === Dialogos ===
    function showModal(title, bodyHtml, footerHtml) {
        $('#modal-title').textContent = title;
        $('#modal-body').innerHTML = bodyHtml;
        $('#modal-footer').innerHTML = footerHtml;
        $('#modal-overlay').style.display = 'flex';
    }

    function closeModal() {
        $('#modal-overlay').style.display = 'none';
    }

    function showNewFolderDialog() {
        showModal(
            'Nova Pasta',
            `<label>Nome da pasta:</label>
             <input type="text" id="new-folder-name" placeholder="Nova Pasta" autofocus>`,
            `<button class="btn btn-secondary" onclick="document.querySelector('#modal-overlay').style.display='none'">Cancelar</button>
             <button class="btn btn-primary" id="btn-confirm-new-folder">Criar</button>`
        );

        setTimeout(() => {
            const input = $('#new-folder-name');
            input.focus();
            input.select();

            const confirmBtn = $('#btn-confirm-new-folder');
            confirmBtn.addEventListener('click', async () => {
                const name = input.value.trim();
                if (!name) {
                    toast('Digite um nome para a pasta', 'error');
                    return;
                }
                try {
                    const fullPath = state.currentPath + name + '/';
                    await api.createFolder(fullPath);
                    toast(`Pasta "${name}" criada com sucesso`, 'success');
                    closeModal();
                    await navigateTo(state.currentPath);
                } catch (err) {
                    toast('Erro ao criar pasta: ' + err.message, 'error');
                }
            });

            input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') confirmBtn.click();
                if (e.key === 'Escape') closeModal();
            });
        }, 50);
    }

    function showRenameDialog(item) {
        const isFolder = item.type === 'folder';
        const currentName = item.name;

        showModal(
            'Renomear',
            `<label>Novo nome:</label>
             <input type="text" id="rename-input" value="${escapeHtml(currentName)}" autofocus>`,
            `<button class="btn btn-secondary" onclick="document.querySelector('#modal-overlay').style.display='none'">Cancelar</button>
             <button class="btn btn-primary" id="btn-confirm-rename">Renomear</button>`
        );

        setTimeout(() => {
            const input = $('#rename-input');
            input.focus();
            // Selecionar nome sem extensao para arquivos
            if (!isFolder && currentName.includes('.')) {
                input.setSelectionRange(0, currentName.lastIndexOf('.'));
            } else {
                input.select();
            }

            const confirmBtn = $('#btn-confirm-rename');
            confirmBtn.addEventListener('click', async () => {
                const newName = input.value.trim();
                if (!newName || newName === currentName) {
                    closeModal();
                    return;
                }

                try {
                    let oldPath = item.path;
                    let newPath;

                    if (isFolder) {
                        const parentPath = oldPath.replace(/[^/]+\/$/, '');
                        newPath = parentPath + newName + '/';
                    } else {
                        const parentPath = oldPath.substring(0, oldPath.lastIndexOf('/') + 1);
                        newPath = parentPath + newName;
                    }

                    await api.rename(oldPath, newPath);
                    toast(`Renomeado para "${newName}"`, 'success');
                    closeModal();
                    await navigateTo(state.currentPath);
                } catch (err) {
                    toast('Erro ao renomear: ' + err.message, 'error');
                }
            });

            input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') confirmBtn.click();
                if (e.key === 'Escape') closeModal();
            });
        }, 50);
    }

    function showDeleteConfirm(item) {
        const name = item.name;
        const isFolder = item.type === 'folder';

        showModal(
            'Confirmar Exclusao',
            `<p style="margin-bottom:8px">Tem certeza que deseja excluir ${isFolder ? 'a pasta' : 'o arquivo'}:</p>
             <p style="font-weight:600; color:var(--win-text)">"${escapeHtml(name)}"?</p>
             ${isFolder ? '<p style="margin-top:8px; color:var(--warning); font-size:12px"><i class="fas fa-exclamation-triangle"></i> Todos os arquivos dentro da pasta serao excluidos.</p>' : ''}`,
            `<button class="btn btn-secondary" onclick="document.querySelector('#modal-overlay').style.display='none'">Cancelar</button>
             <button class="btn btn-danger" id="btn-confirm-delete">Excluir</button>`
        );

        setTimeout(() => {
            $('#btn-confirm-delete').addEventListener('click', async () => {
                try {
                    await api.deleteItem(item.path);
                    toast(`"${name}" excluido com sucesso`, 'success');
                    closeModal();
                    await navigateTo(state.currentPath);
                } catch (err) {
                    toast('Erro ao excluir: ' + err.message, 'error');
                }
            });
        }, 50);
    }

    function showDeleteSelectedConfirm() {
        const count = state.selectedItems.size;
        if (count === 0) return;

        showModal(
            'Confirmar Exclusao',
            `<p>Tem certeza que deseja excluir <strong>${count}</strong> item(ns) selecionado(s)?</p>
             <p style="margin-top:8px; color:var(--warning); font-size:12px"><i class="fas fa-exclamation-triangle"></i> Esta acao nao pode ser desfeita.</p>`,
            `<button class="btn btn-secondary" onclick="document.querySelector('#modal-overlay').style.display='none'">Cancelar</button>
             <button class="btn btn-danger" id="btn-confirm-delete-selected">Excluir Todos</button>`
        );

        setTimeout(() => {
            $('#btn-confirm-delete-selected').addEventListener('click', async () => {
                try {
                    const paths = Array.from(state.selectedItems);
                    for (const path of paths) {
                        await api.deleteItem(path);
                    }
                    toast(`${count} item(ns) excluido(s) com sucesso`, 'success');
                    closeModal();
                    state.selectedItems.clear();
                    await navigateTo(state.currentPath);
                } catch (err) {
                    toast('Erro ao excluir itens: ' + err.message, 'error');
                }
            });
        }, 50);
    }

    function showMoveDialog(item) {
        showModal(
            'Mover para...',
            `<label>Selecione a pasta de destino:</label>
             <div class="folder-tree" id="move-folder-tree">
                <div class="folder-tree-item" data-path="">
                    <i class="fas fa-home"></i> Raiz
                </div>
             </div>
             <p style="margin-top:8px; font-size:12px; color:var(--win-text-secondary)">Clique em uma pasta para seleciona-la como destino.</p>`,
            `<button class="btn btn-secondary" onclick="document.querySelector('#modal-overlay').style.display='none'">Cancelar</button>
             <button class="btn btn-primary" id="btn-confirm-move" disabled>Mover</button>`
        );

        // Carregar pastas disponiveis
        setTimeout(async () => {
            const tree = $('#move-folder-tree');
            let selectedMovePath = null;

            try {
                const data = await api.list('');
                data.folders.forEach((folder) => {
                    const el = document.createElement('div');
                    el.className = 'folder-tree-item';
                    el.dataset.path = folder.path;
                    el.innerHTML = `<i class="fas fa-folder"></i> ${escapeHtml(folder.name)}`;
                    tree.appendChild(el);
                });
            } catch { /* ignore */ }

            tree.addEventListener('click', (e) => {
                const treeItem = e.target.closest('.folder-tree-item');
                if (!treeItem) return;

                tree.querySelectorAll('.folder-tree-item').forEach((el) => el.classList.remove('selected'));
                treeItem.classList.add('selected');
                selectedMovePath = treeItem.dataset.path;
                $('#btn-confirm-move').disabled = false;
            });

            $('#btn-confirm-move').addEventListener('click', async () => {
                if (selectedMovePath === null) return;
                try {
                    const fileName = item.name;
                    const newPath = selectedMovePath + fileName;
                    await api.move(item.path, newPath);
                    toast(`"${fileName}" movido com sucesso`, 'success');
                    closeModal();
                    await navigateTo(state.currentPath);
                } catch (err) {
                    toast('Erro ao mover: ' + err.message, 'error');
                }
            });
        }, 50);
    }

    function showInfoDialog(item) {
        if (item.type === 'folder') {
            showModal(
                'Propriedades',
                `<dl class="info-grid">
                    <dt>Nome:</dt><dd>${escapeHtml(item.name)}</dd>
                    <dt>Tipo:</dt><dd>Pasta</dd>
                    <dt>Caminho:</dt><dd>${escapeHtml(item.path)}</dd>
                </dl>`,
                `<button class="btn btn-primary" onclick="document.querySelector('#modal-overlay').style.display='none'">OK</button>`
            );
            return;
        }

        // Para arquivos, buscar informacoes adicionais
        api.getInfo(item.path).then((info) => {
            showModal(
                'Propriedades',
                `<dl class="info-grid">
                    <dt>Nome:</dt><dd>${escapeHtml(info.name)}</dd>
                    <dt>Tipo:</dt><dd>${info.contentType || info.extension}</dd>
                    <dt>Tamanho:</dt><dd>${formatSize(info.size)}</dd>
                    <dt>Modificado:</dt><dd>${info.lastModified}</dd>
                    <dt>Caminho:</dt><dd>${escapeHtml(info.path)}</dd>
                </dl>`,
                `<button class="btn btn-primary" onclick="document.querySelector('#modal-overlay').style.display='none'">OK</button>`
            );
        }).catch((err) => {
            toast('Erro ao carregar propriedades: ' + err.message, 'error');
        });
    }

    // === UI Updates ===
    function updateBreadcrumb() {
        const bc = $('#breadcrumb');
        bc.innerHTML = '';

        const rootCrumb = document.createElement('span');
        rootCrumb.className = 'crumb';
        rootCrumb.dataset.path = '';
        rootCrumb.textContent = 'Raiz';
        rootCrumb.addEventListener('click', () => navigateTo(''));
        bc.appendChild(rootCrumb);

        if (state.currentPath) {
            const parts = state.currentPath.replace(/\/$/, '').split('/');
            let accumulated = '';

            parts.forEach((part) => {
                accumulated += part + '/';

                const sep = document.createElement('span');
                sep.className = 'crumb-separator';
                sep.textContent = '>';
                bc.appendChild(sep);

                const crumb = document.createElement('span');
                crumb.className = 'crumb';
                crumb.dataset.path = accumulated;
                crumb.textContent = part;
                crumb.addEventListener('click', () => navigateTo(accumulated));
                bc.appendChild(crumb);
            });
        }
    }

    function updateNavButtons() {
        $('#btn-back').disabled = state.historyIndex <= 0;
        $('#btn-forward').disabled = state.historyIndex >= state.history.length - 1;
        $('#btn-up').disabled = !state.currentPath;
    }

    function updateStatus() {
        const total = state.folders.length + state.files.length;
        $('#status-items').textContent = `${total} item(ns)`;
        $('#status-path').textContent = state.currentPath || 'Raiz';
    }

    function updateWindowTitle() {
        const path = state.currentPath;
        const folderName = path ? path.replace(/\/$/, '').split('/').pop() : 'Meus Arquivos';
        $('#window-title').textContent = `Nuvem - ${folderName}`;
    }

    function showLoading(show) {
        const loading = $('#loading');
        if (show) {
            loading.style.display = 'flex';
            loading.innerHTML = '<i class="fas fa-spinner fa-spin"></i><span>Carregando arquivos...</span>';
        } else {
            loading.style.display = 'none';
        }
    }

    // === Menu de Contexto ===
    function showContextMenu(x, y, type) {
        hideAllContextMenus();

        const menu = type === 'item' ? $('#context-menu') : $('#area-context-menu');
        menu.style.display = 'block';

        // Ajustar posicao para nao sair da tela
        const rect = menu.getBoundingClientRect();
        const winW = window.innerWidth;
        const winH = window.innerHeight;

        if (x + rect.width > winW) x = winW - rect.width - 8;
        if (y + rect.height > winH) y = winH - rect.height - 8;

        menu.style.left = x + 'px';
        menu.style.top = y + 'px';

        // Atualizar visibilidade dos itens do menu baseado no tipo
        if (type === 'item' && state.contextTarget) {
            const isFolder = state.contextTarget.type === 'folder';
            const openItem = menu.querySelector('[data-action="open"]');
            const downloadItem = menu.querySelector('[data-action="download"]');
            if (openItem) openItem.style.display = isFolder ? 'flex' : 'none';
            if (downloadItem) downloadItem.style.display = isFolder ? 'none' : 'flex';
        }
    }

    function hideAllContextMenus() {
        $('#context-menu').style.display = 'none';
        $('#area-context-menu').style.display = 'none';
    }

    // === Event Listeners ===
    function setupEventListeners() {
        // Login
        $('#login-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const password = $('#login-password').value;
            const errorEl = $('#login-error');

            try {
                await api.login(password);
                showApp();
                await navigateTo('');
            } catch (err) {
                errorEl.textContent = err.message;
                errorEl.style.display = 'block';
            }
        });

        // Navegacao
        $('#btn-back').addEventListener('click', goBack);
        $('#btn-forward').addEventListener('click', goForward);
        $('#btn-up').addEventListener('click', goUp);
        $('#btn-refresh').addEventListener('click', () => navigateTo(state.currentPath));

        // Acoes
        $('#btn-new-folder').addEventListener('click', showNewFolderDialog);
        $('#btn-upload').addEventListener('click', () => $('#file-input').click());
        $('#btn-select-all').addEventListener('click', selectAll);
        $('#btn-delete-selected').addEventListener('click', showDeleteSelectedConfirm);

        // Checkbox principal
        $('#check-all').addEventListener('change', (e) => {
            if (e.target.checked) {
                selectAll();
            } else {
                state.selectedItems.clear();
                updateSelectionUI();
            }
        });

        // Visualizacao
        $('#btn-view-grid').addEventListener('click', () => {
            state.viewMode = 'grid';
            $('#btn-view-grid').classList.add('active');
            $('#btn-view-list').classList.remove('active');
            renderFiles();
        });

        $('#btn-view-list').addEventListener('click', () => {
            state.viewMode = 'list';
            $('#btn-view-list').classList.add('active');
            $('#btn-view-grid').classList.remove('active');
            renderFiles();
        });

        // Busca
        let searchTimeout;
        $('#search-input').addEventListener('input', () => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => renderFiles(), 300);
        });

        // Upload de arquivo
        $('#file-input').addEventListener('change', (e) => {
            uploadFiles(e.target.files);
            e.target.value = '';
        });

        // Fechar menus de contexto ao clicar fora
        document.addEventListener('click', () => {
            hideAllContextMenus();
        });

        // Menu de contexto da area vazia
        $('#file-area').addEventListener('contextmenu', (e) => {
            if (!e.target.closest('.file-item')) {
                e.preventDefault();
                showContextMenu(e.clientX, e.clientY, 'area');
            }
        });

        // Acoes do menu de contexto (item)
        $$('#context-menu .context-item').forEach((item) => {
            item.addEventListener('click', () => {
                const action = item.dataset.action;
                const target = state.contextTarget;
                if (!target) return;

                switch (action) {
                    case 'open':
                        if (target.type === 'folder') navigateTo(target.path);
                        break;
                    case 'download':
                        downloadFile(target.path);
                        break;
                    case 'rename':
                        showRenameDialog(target);
                        break;
                    case 'move':
                        showMoveDialog(target);
                        break;
                    case 'info':
                        showInfoDialog(target);
                        break;
                    case 'delete':
                        showDeleteConfirm(target);
                        break;
                }
                hideAllContextMenus();
            });
        });

        // Acoes do menu de contexto (area)
        $$('#area-context-menu .context-item').forEach((item) => {
            item.addEventListener('click', () => {
                const action = item.dataset.action;
                switch (action) {
                    case 'new-folder':
                        showNewFolderDialog();
                        break;
                    case 'upload':
                        $('#file-input').click();
                        break;
                    case 'refresh':
                        navigateTo(state.currentPath);
                        break;
                    case 'select-all':
                        selectAll();
                        break;
                }
                hideAllContextMenus();
            });
        });

        // Modal
        $('#modal-close').addEventListener('click', closeModal);
        $('#modal-overlay').addEventListener('click', (e) => {
            if (e.target === $('#modal-overlay')) closeModal();
        });

        // Logout
        $('#btn-logout').addEventListener('click', async () => {
            try {
                await api.logout();
            } catch { /* ignore */ }
            showLogin();
        });

        // Atalhos de teclado
        document.addEventListener('keydown', (e) => {
            if (!state.isAuthenticated) return;
            if ($('#modal-overlay').style.display === 'flex') {
                if (e.key === 'Escape') closeModal();
                return;
            }

            if (e.key === 'Delete' && state.selectedItems.size > 0) {
                e.preventDefault();
                showDeleteSelectedConfirm();
            }
            if (e.key === 'F2' && state.selectedItems.size === 1) {
                e.preventDefault();
                const path = Array.from(state.selectedItems)[0];
                const item = [...state.folders, ...state.files].find((f) => f.path === path);
                if (item) showRenameDialog(item);
            }
            if (e.key === 'F5') {
                e.preventDefault();
                navigateTo(state.currentPath);
            }
            if (e.ctrlKey && e.key === 'a') {
                e.preventDefault();
                selectAll();
            }
            if (e.key === 'Backspace') {
                e.preventDefault();
                goUp();
            }
            if (e.key === 'Escape') {
                state.selectedItems.clear();
                updateSelectionUI();
                hideAllContextMenus();
            }
        });

        // Sidebar
        $$('.sidebar-item').forEach((item) => {
            item.addEventListener('click', () => {
                const path = item.dataset.path;
                if (path !== undefined) {
                    $$('.sidebar-item').forEach((el) => el.classList.remove('active'));
                    item.classList.add('active');
                    navigateTo(path);
                }
            });
        });

        // Ordenacao
        $$('.file-list-header > div[data-sort]').forEach((col) => {
            col.addEventListener('click', () => {
                const sortBy = col.dataset.sort;
                if (state.sortBy === sortBy) {
                    state.sortDir = state.sortDir === 'asc' ? 'desc' : 'asc';
                } else {
                    state.sortBy = sortBy;
                    state.sortDir = 'asc';
                }
                renderFiles();
            });
        });

        // Botao minimizar/maximizar da janela (visual apenas)
        $('#btn-minimize-window').addEventListener('click', () => {
            const win = $('#main-window');
            win.style.display = 'none';
            setTimeout(() => { win.style.display = 'flex'; }, 300);
        });

        // Upload cancel
        $('#upload-cancel').addEventListener('click', () => {
            $('#upload-progress').style.display = 'none';
        });
    }

    // === Drag & Drop ===
    function setupDragDrop() {
        const fileArea = $('#file-area');
        const overlay = $('#drop-overlay');

        let dragCounter = 0;

        document.addEventListener('dragenter', (e) => {
            e.preventDefault();
            dragCounter++;
            if (state.isAuthenticated) {
                overlay.style.display = 'flex';
            }
        });

        document.addEventListener('dragleave', (e) => {
            e.preventDefault();
            dragCounter--;
            if (dragCounter <= 0) {
                dragCounter = 0;
                overlay.style.display = 'none';
            }
        });

        document.addEventListener('dragover', (e) => {
            e.preventDefault();
        });

        document.addEventListener('drop', (e) => {
            e.preventDefault();
            dragCounter = 0;
            overlay.style.display = 'none';

            if (state.isAuthenticated && e.dataTransfer.files.length > 0) {
                uploadFiles(e.dataTransfer.files);
            }
        });
    }

    // === Relogio ===
    function setupClock() {
        function updateClock() {
            const now = new Date();
            const time = now.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
            const date = now.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' });
            const el = $('#taskbar-clock');
            if (el) el.textContent = `${time}  ${date}`;
        }
        updateClock();
        setInterval(updateClock, 30000);
    }

    // === Toast Notifications ===
    function toast(message, type = 'info') {
        let container = document.querySelector('.toast-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'toast-container';
            document.body.appendChild(container);
        }

        const icons = {
            success: 'fas fa-check-circle',
            error: 'fas fa-times-circle',
            info: 'fas fa-info-circle',
        };

        const toastEl = document.createElement('div');
        toastEl.className = `toast ${type}`;
        toastEl.innerHTML = `
            <i class="${icons[type] || icons.info}"></i>
            <span>${escapeHtml(message)}</span>
            <span class="toast-close"><i class="fas fa-times"></i></span>
        `;

        const closeBtn = toastEl.querySelector('.toast-close');
        closeBtn.addEventListener('click', () => {
            toastEl.style.animation = 'fadeOut 0.3s ease forwards';
            setTimeout(() => toastEl.remove(), 300);
        });

        container.appendChild(toastEl);

        // Auto-remover apos 5s
        setTimeout(() => {
            if (toastEl.parentNode) {
                toastEl.style.animation = 'fadeOut 0.3s ease forwards';
                setTimeout(() => toastEl.remove(), 300);
            }
        }, 5000);
    }

    // === Utilidades ===
    function getFileIcon(ext) {
        const imageExts = ['jpg', 'jpeg', 'png', 'gif', 'svg', 'webp', 'bmp', 'ico'];
        const videoExts = ['mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm'];
        const audioExts = ['mp3', 'wav', 'ogg', 'flac', 'aac', 'wma'];
        const docExts = ['doc', 'docx', 'odt', 'rtf'];
        const sheetExts = ['xls', 'xlsx', 'csv', 'ods'];
        const codeExts = ['js', 'ts', 'py', 'php', 'html', 'css', 'json', 'xml', 'sql', 'sh', 'bat'];
        const archiveExts = ['zip', 'rar', '7z', 'tar', 'gz', 'bz2'];

        if (ext === 'pdf') return '<i class="fas fa-file-pdf icon-pdf"></i>';
        if (imageExts.includes(ext)) return '<i class="fas fa-file-image icon-image"></i>';
        if (videoExts.includes(ext)) return '<i class="fas fa-file-video icon-video"></i>';
        if (audioExts.includes(ext)) return '<i class="fas fa-file-audio icon-audio"></i>';
        if (docExts.includes(ext)) return '<i class="fas fa-file-word icon-doc"></i>';
        if (sheetExts.includes(ext)) return '<i class="fas fa-file-excel icon-sheet"></i>';
        if (codeExts.includes(ext)) return '<i class="fas fa-file-code icon-code"></i>';
        if (archiveExts.includes(ext)) return '<i class="fas fa-file-archive icon-archive"></i>';
        if (ext === 'txt' || ext === 'md' || ext === 'log') return '<i class="fas fa-file-alt icon-text"></i>';

        return '<i class="fas fa-file icon-default"></i>';
    }

    function getFolderIcon() {
        return '<i class="fas fa-folder folder-icon"></i>';
    }

    function formatSize(bytes) {
        if (bytes === 0 || bytes === undefined) return '0 B';
        const units = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return (bytes / Math.pow(1024, i)).toFixed(i > 0 ? 1 : 0) + ' ' + units[i];
    }

    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    function getSortFunction() {
        return (a, b) => {
            let valA, valB;

            switch (state.sortBy) {
                case 'name':
                    valA = a.name.toLowerCase();
                    valB = b.name.toLowerCase();
                    break;
                case 'size':
                    valA = a.size || 0;
                    valB = b.size || 0;
                    break;
                case 'date':
                    valA = a.lastModified || '';
                    valB = b.lastModified || '';
                    break;
                default:
                    valA = a.name.toLowerCase();
                    valB = b.name.toLowerCase();
            }

            let result;
            if (typeof valA === 'string') {
                result = valA.localeCompare(valB);
            } else {
                result = valA - valB;
            }

            return state.sortDir === 'desc' ? -result : result;
        };
    }

    // === Start ===
    document.addEventListener('DOMContentLoaded', init);
})();
