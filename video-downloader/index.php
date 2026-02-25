<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Video Downloader em Lote</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        .video-card.selected { outline: 2px solid #3b82f6; }
        .thumb-wrap { aspect-ratio: 9/16; }
        @media (min-width: 640px) { .thumb-wrap { aspect-ratio: 16/9; } }
    </style>
</head>
<body class="bg-gray-100 min-h-screen">

<!-- Header -->
<header class="bg-gray-900 text-white shadow">
    <div class="max-w-7xl mx-auto px-4 py-3 flex items-center gap-4">
        <i class="fa-solid fa-film text-blue-400 text-xl"></i>
        <span class="font-bold text-lg tracking-tight">Video Downloader em Lote</span>
        <span class="text-xs text-gray-400 hidden sm:inline">TikTok · Instagram · Facebook · YouTube · e mais</span>
        <div class="ml-auto flex items-center gap-3">
            <span id="localBadge" class="hidden text-xs bg-green-600 text-white px-2.5 py-1 rounded-full font-medium items-center gap-1.5">
                <i class="fa-solid fa-circle text-green-300 text-[8px]"></i> Modo Local Ativo
            </span>
            <a href="setup.php" class="text-xs text-gray-400 hover:text-white transition flex items-center gap-1">
                <i class="fa-solid fa-screwdriver-wrench"></i> Setup
            </a>
        </div>
    </div>
</header>

<main class="max-w-7xl mx-auto px-4 py-6 space-y-6">

    <!-- Aviso yt-dlp / modo Cobalt -->
    <div id="ytdlpWarn" class="hidden bg-amber-50 border border-amber-300 rounded-lg p-4 flex gap-3 items-start">
        <i class="fa-solid fa-triangle-exclamation text-amber-500 mt-0.5 shrink-0"></i>
        <div class="text-sm text-amber-800 flex-1">
            <strong>yt-dlp não disponível neste servidor.</strong>
            Execute o <strong>Agente Local</strong> na sua máquina para habilitar todas as funções
            (incluindo navegação de perfis), ou use <strong>URL direta</strong> abaixo via Cobalt API.
            <a href="setup.php" class="underline ml-1">Ver Setup →</a>
        </div>
    </div>

    <!-- Card: Download por URL direta (modo Cobalt — aparece quando yt-dlp indisponível) -->
    <div id="directUrlCard" class="hidden bg-white rounded-xl shadow p-5">
        <h2 class="font-semibold text-gray-700 mb-1 flex items-center gap-2">
            <i class="fa-solid fa-link text-purple-500"></i>
            Download por URL direta
            <span class="text-xs font-normal text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">via Cobalt API</span>
        </h2>
        <p class="text-xs text-gray-500 mb-3">Cole um ou mais links de vídeos, um por linha. Suporta YouTube, TikTok, Instagram, Twitter/X, Facebook e centenas de outros sites.</p>
        <textarea id="directUrls" rows="5"
                  placeholder="https://www.youtube.com/watch?v=...&#10;https://www.tiktok.com/@usuario/video/...&#10;https://www.instagram.com/p/..."
                  class="w-full border rounded-lg px-3 py-2.5 text-sm focus:ring-2 focus:ring-purple-500 focus:outline-none font-mono resize-y"></textarea>
        <div class="flex flex-wrap items-center gap-3 mt-3">
            <button onclick="startDirectDownload()"
                    class="bg-purple-600 hover:bg-purple-700 text-white px-6 py-2.5 rounded-lg text-sm font-semibold transition flex items-center gap-2">
                <i class="fa-solid fa-download"></i> Baixar vídeos
            </button>
            <span class="text-xs text-gray-400">Os vídeos serão empacotados em ZIP para download.</span>
        </div>
    </div>

    <!-- Card de busca -->
    <div class="bg-white rounded-xl shadow p-5">
        <h2 class="font-semibold text-gray-700 mb-4 flex items-center gap-2">
            <i class="fa-solid fa-magnifying-glass text-blue-500"></i>
            Buscar vídeos de um perfil
        </h2>

        <!-- Plataformas suportadas -->
        <div class="flex flex-wrap gap-2 mb-4">
            <?php
            $plataformas = [
                ['TikTok',    'fa-brands fa-tiktok',    'bg-black text-white'],
                ['Instagram', 'fa-brands fa-instagram', 'bg-pink-600 text-white'],
                ['Facebook',  'fa-brands fa-facebook',  'bg-blue-700 text-white'],
                ['YouTube',   'fa-brands fa-youtube',   'bg-red-600 text-white'],
                ['Twitter/X', 'fa-brands fa-x-twitter', 'bg-gray-800 text-white'],
            ];
            foreach ($plataformas as [$nome, $icon, $cls]):
            ?>
            <span class="inline-flex items-center gap-1.5 <?= $cls ?> text-xs px-2.5 py-1 rounded-full font-medium">
                <i class="<?= $icon ?>"></i> <?= $nome ?>
            </span>
            <?php endforeach; ?>
            <span class="text-xs text-gray-400 self-center">+ 1000 sites via yt-dlp</span>
        </div>

        <form id="searchForm" class="flex flex-col sm:flex-row gap-3">
            <input type="url" id="profileUrl" name="url" required
                   placeholder="https://www.tiktok.com/@usuario  ou  https://www.instagram.com/usuario/"
                   class="flex-1 border rounded-lg px-4 py-2.5 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none">
            <button type="submit" id="btnSearch"
                    class="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2.5 rounded-lg text-sm font-semibold transition flex items-center gap-2 justify-center whitespace-nowrap">
                <i class="fa-solid fa-search"></i> Buscar vídeos
            </button>
        </form>

        <p class="mt-2 text-xs text-gray-400">
            Cole o link do <strong>perfil/canal</strong> (não de um vídeo individual).
            Perfis privados podem exigir configuração de cookies no servidor.
        </p>
    </div>

    <!-- Resultado: info do perfil + toolbar -->
    <div id="profileInfo" class="hidden bg-white rounded-xl shadow p-4 flex flex-wrap items-center justify-between gap-3">
        <div>
            <span class="font-semibold text-gray-800" id="profileName"></span>
            <span class="text-xs text-gray-500 ml-2" id="profileCount"></span>
        </div>
        <div class="flex items-center gap-2 flex-wrap">
            <button onclick="selectAll(true)"
                    class="text-xs bg-gray-100 hover:bg-gray-200 px-3 py-1.5 rounded transition">
                <i class="fa-solid fa-check-double mr-1"></i>Marcar todos
            </button>
            <button onclick="selectAll(false)"
                    class="text-xs bg-gray-100 hover:bg-gray-200 px-3 py-1.5 rounded transition">
                <i class="fa-solid fa-xmark mr-1"></i>Desmarcar
            </button>
        </div>
    </div>

    <!-- Toolbar de download (aparece ao selecionar) -->
    <div id="dlToolbar" class="hidden bg-blue-50 border border-blue-200 rounded-xl p-4 flex flex-wrap items-center gap-3">
        <i class="fa-solid fa-circle-check text-blue-500"></i>
        <span id="dlCount" class="text-sm font-semibold text-blue-800">0 selecionado(s)</span>
        <button onclick="startDownload()"
                class="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2 rounded-lg text-sm font-semibold transition flex items-center gap-2">
            <i class="fa-solid fa-download"></i> Baixar selecionados
        </button>
        <button onclick="selectAll(false)"
                class="bg-gray-200 hover:bg-gray-300 text-gray-700 px-3 py-2 rounded-lg text-sm transition">
            Limpar seleção
        </button>
    </div>

    <!-- Grade de vídeos -->
    <div id="videoGrid" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4"></div>

    <!-- Estado vazio / loading -->
    <div id="stateMsg" class="text-center py-16 text-gray-400">
        <i class="fa-solid fa-film text-5xl mb-3 opacity-30"></i>
        <p class="text-sm">Informe o link de um perfil acima para buscar os vídeos.</p>
    </div>

    <!-- Botão "Carregar mais" -->
    <div id="loadMoreWrap" class="hidden text-center">
        <button id="btnLoadMore" onclick="loadMore()"
                class="bg-white border hover:bg-gray-50 text-gray-700 px-8 py-3 rounded-xl text-sm font-semibold shadow transition">
            <i class="fa-solid fa-chevron-down mr-2"></i>Carregar mais 100 vídeos
        </button>
    </div>

</main>

<!-- Modal de progresso -->
<div id="progressModal" class="fixed inset-0 bg-black/60 z-50 hidden flex items-center justify-center p-4">
    <div class="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6 space-y-4">
        <div class="flex items-center gap-3">
            <i id="modalIcon" class="fa-solid fa-spinner fa-spin text-blue-500 text-2xl"></i>
            <div>
                <h3 class="font-bold text-gray-800 text-lg">Baixando vídeos</h3>
                <p id="modalSubtitle" class="text-xs text-gray-500">Aguarde, isso pode demorar alguns minutos...</p>
            </div>
        </div>

        <!-- Barra de progresso -->
        <div class="space-y-1">
            <div class="flex justify-between text-xs text-gray-500">
                <span id="progressLabel">Iniciando...</span>
                <span id="progressFraction">0 / 0</span>
            </div>
            <div class="w-full bg-gray-200 rounded-full h-3">
                <div id="progressBar" class="bg-blue-500 h-3 rounded-full transition-all duration-300" style="width:0%"></div>
            </div>
        </div>

        <!-- Mensagem atual -->
        <div id="modalMsg" class="text-sm text-gray-600 min-h-[1.5rem]"></div>

        <!-- Erros -->
        <div id="errorList" class="hidden text-xs text-red-600 bg-red-50 rounded p-2 max-h-20 overflow-y-auto space-y-0.5"></div>

        <!-- Ações finais -->
        <div id="modalActions" class="hidden pt-2 flex flex-col sm:flex-row gap-3">
            <a id="btnDownloadZip" href="#" target="_blank"
               class="flex-1 bg-green-600 hover:bg-green-700 text-white text-center py-2.5 px-4 rounded-lg font-semibold text-sm transition flex items-center justify-center gap-2">
                <i class="fa-solid fa-file-zipper"></i> Baixar ZIP
            </a>
            <button onclick="closeModal()"
                    class="flex-1 bg-gray-200 hover:bg-gray-300 text-gray-700 py-2.5 px-4 rounded-lg font-semibold text-sm transition">
                Fechar
            </button>
        </div>
    </div>
</div>

<script>
// ── Estado da aplicação ───────────────────────────────────────────────────────
const state = {
  allVideos: [],    // todos os vídeos carregados
  selected: new Set(),
  profileUrl: '',
  nextStart: 1,
  hasMore: false,
  profileName: '',
};

// Estado do agente local
const local = {
  available: false,
  url: 'http://localhost:9999',
  version: '',
  downloadDir: '',
};

// ── Checar agente local + yt-dlp ao carregar ──────────────────────────────────
(async function checkOnLoad() {
  // 1. Tenta detectar o agente local (timeout curto para não travar)
  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 1200);
    const r = await fetch(local.url + '/ping', { signal: ctrl.signal });
    clearTimeout(timer);
    const d = await r.json();
    if (d.ok && d.ytdlp) {
      local.available = true;
      local.version = d.version || '';
      local.downloadDir = d.download_dir || '';
      // Mostra badge no header
      const badge = document.getElementById('localBadge');
      badge.classList.remove('hidden');
      badge.classList.add('flex');
      badge.title = `yt-dlp ${local.version} · Downloads: ${local.downloadDir}`;
      return; // agente local disponível — não precisa checar servidor
    }
  } catch (_) { /* agente não encontrado — continua para checar servidor */ }

  // 2. Agente local não disponível — verifica yt-dlp no servidor
  try {
    const r = await fetch('api.php?action=check');
    const d = await r.json();
    if (!d.ok) {
      document.getElementById('ytdlpWarn').classList.remove('hidden');
      if (d.cobalt_mode) {
        document.getElementById('directUrlCard').classList.remove('hidden');
        document.getElementById('stateMsg').innerHTML =
          '<i class="fa-solid fa-link text-purple-400 text-4xl mb-3 opacity-50"></i>' +
          '<p class="text-sm text-gray-500">Navegação de perfis indisponível (requer yt-dlp ou Agente Local).<br>' +
          'Use o <strong>Download por URL direta</strong> abaixo.</p>';
        document.getElementById('btnSearch').disabled = true;
        document.getElementById('btnSearch').classList.add('opacity-40', 'cursor-not-allowed');
        document.getElementById('profileUrl').disabled = true;
        document.getElementById('profileUrl').placeholder = 'Navegação indisponível — use Agente Local ou URL direta acima';
        document.getElementById('profileUrl').classList.add('bg-gray-50', 'text-gray-400');
      }
    }
  } catch (_) {}
})();

// ── Formata segundos em mm:ss / hh:mm:ss ─────────────────────────────────────
function fmtDuration(secs) {
  if (!secs) return '';
  const h = Math.floor(secs / 3600);
  const m = Math.floor((secs % 3600) / 60);
  const s = secs % 60;
  if (h > 0) return `${h}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
  return `${m}:${String(s).padStart(2,'0')}`;
}

// ── Formata número de views ───────────────────────────────────────────────────
function fmtViews(n) {
  if (!n) return '';
  if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M views';
  if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K views';
  return n + ' views';
}

// ── Renderiza um card de vídeo ────────────────────────────────────────────────
function renderCard(video) {
  const card = document.createElement('div');
  card.className = 'video-card bg-white rounded-xl shadow overflow-hidden cursor-pointer transition hover:shadow-md';
  card.dataset.url = video.url;
  card.dataset.idx = state.allVideos.length - 1;

  const sel = state.selected.has(video.url);
  if (sel) card.classList.add('selected');

  card.innerHTML = `
    <div class="thumb-wrap bg-gray-900 relative overflow-hidden">
      ${video.thumb
        ? `<img src="${escHtml(video.thumb)}" alt="" class="w-full h-full object-cover" loading="lazy" onerror="this.style.display='none'">`
        : `<div class="w-full h-full flex items-center justify-center text-gray-600"><i class="fa-solid fa-video text-3xl opacity-30"></i></div>`
      }
      ${video.duration ? `<span class="absolute bottom-1 right-1 bg-black/70 text-white text-xs px-1.5 py-0.5 rounded">${fmtDuration(video.duration)}</span>` : ''}
      <div class="absolute top-1.5 left-1.5">
        <div class="check-circle w-5 h-5 rounded-full border-2 flex items-center justify-center transition
                    ${sel ? 'bg-blue-500 border-blue-500' : 'bg-white/70 border-gray-300'}">
          ${sel ? '<i class="fa-solid fa-check text-white text-[10px]"></i>' : ''}
        </div>
      </div>
    </div>
    <div class="p-2">
      <p class="text-xs font-medium text-gray-800 leading-snug line-clamp-2" title="${escHtml(video.title)}">${escHtml(video.title)}</p>
      ${video.views ? `<p class="text-[10px] text-gray-400 mt-0.5">${fmtViews(video.views)}</p>` : ''}
    </div>`;

  card.addEventListener('click', () => toggleCard(card, video.url));
  return card;
}

function escHtml(str) {
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function toggleCard(card, url) {
  if (state.selected.has(url)) {
    state.selected.delete(url);
    card.classList.remove('selected');
    card.querySelector('.check-circle').className = 'check-circle w-5 h-5 rounded-full border-2 flex items-center justify-center transition bg-white/70 border-gray-300';
    card.querySelector('.check-circle').innerHTML = '';
  } else {
    state.selected.add(url);
    card.classList.add('selected');
    card.querySelector('.check-circle').className = 'check-circle w-5 h-5 rounded-full border-2 flex items-center justify-center transition bg-blue-500 border-blue-500';
    card.querySelector('.check-circle').innerHTML = '<i class="fa-solid fa-check text-white text-[10px]"></i>';
  }
  updateToolbar();
}

// ── Toolbar de seleção ────────────────────────────────────────────────────────
function updateToolbar() {
  const n = state.selected.size;
  const tb = document.getElementById('dlToolbar');
  document.getElementById('dlCount').textContent = n + ' selecionado(s)';
  if (n > 0) tb.classList.remove('hidden'); else tb.classList.add('hidden');
}

function selectAll(sel) {
  state.selected.clear();
  document.querySelectorAll('.video-card').forEach(card => {
    const url = card.dataset.url;
    if (sel) state.selected.add(url);
    const circle = card.querySelector('.check-circle');
    if (sel) {
      card.classList.add('selected');
      circle.className = 'check-circle w-5 h-5 rounded-full border-2 flex items-center justify-center transition bg-blue-500 border-blue-500';
      circle.innerHTML = '<i class="fa-solid fa-check text-white text-[10px]"></i>';
    } else {
      card.classList.remove('selected');
      circle.className = 'check-circle w-5 h-5 rounded-full border-2 flex items-center justify-center transition bg-white/70 border-gray-300';
      circle.innerHTML = '';
    }
  });
  updateToolbar();
}

// ── Buscar vídeos ─────────────────────────────────────────────────────────────
document.getElementById('searchForm').addEventListener('submit', async function(e) {
  e.preventDefault();
  const url = document.getElementById('profileUrl').value.trim();
  if (!url) return;

  state.allVideos = [];
  state.selected.clear();
  state.profileUrl = url;
  state.nextStart = 1;
  state.hasMore = false;

  document.getElementById('videoGrid').innerHTML = '';
  document.getElementById('profileInfo').classList.add('hidden');
  document.getElementById('dlToolbar').classList.add('hidden');
  document.getElementById('loadMoreWrap').classList.add('hidden');
  document.getElementById('stateMsg').innerHTML =
    '<i class="fa-solid fa-spinner fa-spin text-blue-400 text-4xl mb-3"></i><p class="text-sm">Buscando vídeos...</p>';
  document.getElementById('stateMsg').classList.remove('hidden');

  const btn = document.getElementById('btnSearch');
  btn.disabled = true;
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Buscando...';

  await fetchVideos(url, 1, true);

  btn.disabled = false;
  btn.innerHTML = '<i class="fa-solid fa-search"></i> Buscar vídeos';
});

async function fetchVideos(url, start, fresh) {
  try {
    const fd = new FormData();
    fd.append('url', url);
    fd.append('start', start);
    fd.append('count', 100);

    const endpoint = local.available
      ? local.url + '/fetch_videos'
      : 'api.php?action=fetch_videos';
    const r = await fetch(endpoint, { method: 'POST', body: toBody(fd, local.available), headers: toHeaders(local.available) });
    const d = await r.json();

    if (!d.ok) {
      document.getElementById('stateMsg').innerHTML =
        `<i class="fa-solid fa-triangle-exclamation text-red-400 text-4xl mb-3"></i><p class="text-sm text-red-600">${escHtml(d.error)}</p>`;
      return;
    }

    state.allVideos.push(...d.videos);
    state.nextStart = start + d.fetched;
    state.hasMore = d.has_more;

    if (d.profile) state.profileName = d.profile;

    renderVideos(d.videos);
    updateProfileInfo(d);

  } catch (err) {
    document.getElementById('stateMsg').innerHTML =
      `<i class="fa-solid fa-wifi text-red-400 text-4xl mb-3"></i><p class="text-sm text-red-600">Erro de rede: ${escHtml(err.message)}</p>`;
  }
}

function renderVideos(videos) {
  const grid = document.getElementById('videoGrid');
  const stateMsg = document.getElementById('stateMsg');

  if (videos.length === 0 && state.allVideos.length === 0) {
    stateMsg.innerHTML = '<i class="fa-solid fa-inbox text-4xl mb-3 opacity-30"></i><p class="text-sm">Nenhum vídeo encontrado neste perfil.</p>';
    return;
  }

  stateMsg.classList.add('hidden');
  videos.forEach(v => {
    state.allVideos.length; // comprimento antes do push já foi incrementado
    grid.appendChild(renderCard(v));
  });

  // Carregar mais
  const lmw = document.getElementById('loadMoreWrap');
  if (state.hasMore) lmw.classList.remove('hidden'); else lmw.classList.add('hidden');
}

function updateProfileInfo(d) {
  const pi = document.getElementById('profileInfo');
  pi.classList.remove('hidden');
  document.getElementById('profileName').textContent = state.profileName || 'Perfil';
  document.getElementById('profileCount').textContent =
    state.allVideos.length + ' vídeo(s) carregado(s)' + (state.hasMore ? ' — há mais disponíveis' : '');
}

async function loadMore() {
  const btn = document.getElementById('btnLoadMore');
  btn.disabled = true;
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-2"></i>Carregando...';

  await fetchVideos(state.profileUrl, state.nextStart, false);

  btn.disabled = false;
  btn.innerHTML = '<i class="fa-solid fa-chevron-down mr-2"></i>Carregar mais 100 vídeos';
}

// ── Converte FormData para o formato adequado ao endpoint ─────────────────────
// Para o agente local usamos JSON; para o PHP usamos FormData normal.
function toBody(formData, isLocal) {
  if (!isLocal) return formData;
  const obj = {};
  for (const [k, v] of formData.entries()) {
    const key = k.endsWith('[]') ? k.slice(0, -2) : k;
    if (k.endsWith('[]')) {
      obj[key] = obj[key] || [];
      obj[key].push(v);
    } else {
      obj[key] = v;
    }
  }
  return JSON.stringify(obj);
}

function toHeaders(isLocal) {
  return isLocal ? { 'Content-Type': 'application/json' } : {};
}

// ── Download com SSE ──────────────────────────────────────────────────────────
function startDownload() {
  const urls = Array.from(state.selected);
  if (urls.length === 0) return;

  openModal(urls.length);

  const fd = new FormData();
  urls.forEach(u => fd.append('urls[]', u));

  const endpoint = local.available
    ? local.url + '/download'
    : 'api.php?action=download';
  fetchSSE(endpoint, fd, urls.length);
}

// ── Download direto por URLs (modo Cobalt) ────────────────────────────────────
function startDirectDownload() {
  const raw = (document.getElementById('directUrls').value || '').trim();
  if (!raw) return;

  const urls = raw.split('\n')
    .map(u => u.trim())
    .filter(u => /^https?:\/\//i.test(u));

  if (urls.length === 0) {
    alert('Nenhuma URL válida encontrada. Cole links completos começando com https://');
    return;
  }

  openModal(urls.length);
  const fd = new FormData();
  urls.forEach(u => fd.append('urls[]', u));
  fetchSSE('api.php?action=download', fd, urls.length);
}

async function fetchSSE(url, formData, total) {
  const isLocal = url.startsWith('http://localhost') || url.startsWith('http://127.');
  try {
    const resp = await fetch(url, {
      method: 'POST',
      body: toBody(formData, isLocal),
      headers: toHeaders(isLocal),
    });
    if (!resp.ok) {
      setModalError('Erro HTTP ' + resp.status);
      return;
    }

    const reader = resp.body.getReader();
    const dec    = new TextDecoder();
    let   buf    = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });

      const lines = buf.split('\n');
      buf = lines.pop(); // guarda linha incompleta

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        try {
          const ev = JSON.parse(line.slice(6));
          handleSSEEvent(ev, total);
        } catch (_) {}
      }
    }
  } catch (err) {
    setModalError('Erro de conexão: ' + err.message);
  }
}

function handleSSEEvent(ev, total) {
  const bar   = document.getElementById('progressBar');
  const label = document.getElementById('progressLabel');
  const frac  = document.getElementById('progressFraction');
  const msg   = document.getElementById('modalMsg');

  switch (ev.type) {
    case 'start':
      frac.textContent = '0 / ' + ev.total;
      label.textContent = 'Iniciando downloads...';
      break;

    case 'progress':
      label.textContent = ev.msg;
      frac.textContent  = ev.done + ' / ' + ev.total;
      bar.style.width   = Math.round((ev.done / ev.total) * 90) + '%';
      msg.textContent   = ev.msg;
      break;

    case 'done_one':
      frac.textContent = ev.done + ' / ' + ev.total;
      bar.style.width  = Math.round((ev.done / ev.total) * 90) + '%';
      msg.textContent  = ev.done + ' vídeo(s) baixado(s)...';
      break;

    case 'error': {
      msg.textContent = ev.msg;
      const el = document.getElementById('errorList');
      el.classList.remove('hidden');
      const li = document.createElement('div');
      li.textContent = ev.msg;
      el.appendChild(li);
      break;
    }

    case 'zipping':
      label.textContent = 'Criando arquivo ZIP...';
      msg.textContent   = 'Compactando ' + ev.done + ' vídeo(s)...';
      bar.style.width   = '95%';
      break;

    case 'complete': {
      bar.style.width = '100%';
      bar.classList.replace('bg-blue-500', 'bg-green-500');
      label.textContent = 'Concluído!';
      frac.textContent  = ev.done + ' / ' + ev.total;
      document.getElementById('modalIcon').className = 'fa-solid fa-circle-check text-green-500 text-2xl';
      const failStr = ev.failed > 0 ? ` · ${ev.failed} falha(s)` : '';
      const actions = document.getElementById('modalActions');

      if (ev.download_dir) {
        // Modo local: arquivos já estão na máquina do usuário — não há ZIP
        msg.textContent = `${ev.done} vídeo(s) salvos localmente${failStr}`;
        document.getElementById('modalSubtitle').textContent = 'Arquivos salvos em:';
        actions.innerHTML = `
          <div class="w-full bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-xs font-mono text-gray-600 break-all">${escHtml(ev.download_dir)}</div>
          <button onclick="closeModal()"
                  class="flex-1 bg-gray-200 hover:bg-gray-300 text-gray-700 py-2.5 px-4 rounded-lg font-semibold text-sm transition">
            Fechar
          </button>`;
      } else {
        // Modo servidor: ZIP para download
        msg.textContent = `${ev.done} vídeo(s) baixado(s)${failStr}${ev.size_mb ? ` · ZIP: ${ev.size_mb} MB` : ''}`;
        document.getElementById('modalSubtitle').textContent = 'Clique em "Baixar ZIP" para salvar os arquivos.';
        actions.innerHTML = `
          <a href="api.php?action=zip&job=${encodeURIComponent(ev.job)}" target="_blank"
             class="flex-1 bg-green-600 hover:bg-green-700 text-white text-center py-2.5 px-4 rounded-lg font-semibold text-sm transition flex items-center justify-center gap-2">
            <i class="fa-solid fa-file-zipper"></i> Baixar ZIP
          </a>
          <button onclick="closeModal()"
                  class="flex-1 bg-gray-200 hover:bg-gray-300 text-gray-700 py-2.5 px-4 rounded-lg font-semibold text-sm transition">
            Fechar
          </button>`;
      }
      actions.classList.remove('hidden');
      break;
    }

    case 'failed':
      setModalError(ev.msg);
      break;
  }
}

function openModal(total) {
  const modal = document.getElementById('progressModal');
  document.getElementById('modalIcon').className = 'fa-solid fa-spinner fa-spin text-blue-500 text-2xl';
  document.getElementById('modalSubtitle').textContent = 'Aguarde, isso pode demorar alguns minutos...';
  document.getElementById('progressBar').style.width = '0%';
  document.getElementById('progressBar').className = 'bg-blue-500 h-3 rounded-full transition-all duration-300';
  document.getElementById('progressLabel').textContent = 'Iniciando...';
  document.getElementById('progressFraction').textContent = '0 / ' + total;
  document.getElementById('modalMsg').textContent = '';
  document.getElementById('errorList').innerHTML = '';
  document.getElementById('errorList').classList.add('hidden');
  document.getElementById('modalActions').classList.add('hidden');
  modal.classList.remove('hidden');
}

function setModalError(msg) {
  document.getElementById('modalIcon').className = 'fa-solid fa-circle-xmark text-red-500 text-2xl';
  document.getElementById('modalSubtitle').textContent = 'Ocorreu um erro.';
  document.getElementById('modalMsg').textContent = msg;
  document.getElementById('modalActions').classList.remove('hidden');
  document.getElementById('btnDownloadZip').style.display = 'none';
}

function closeModal() {
  document.getElementById('progressModal').classList.add('hidden');
}

// Fecha modal clicando fora
document.getElementById('progressModal').addEventListener('click', function(e) {
  if (e.target === this) closeModal();
});
</script>
</body>
</html>
