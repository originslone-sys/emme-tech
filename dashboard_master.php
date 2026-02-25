<?php
// dashboard_master.php (DB + brutos no servidor)
// Requer:
// 1) /api/db.php  -> define $conn (mysqli)
// 2) tabela MySQL: fila_edicao (InnoDB recomendado)
// 3) pasta /brutos com permissão de escrita (0777 se necessário)
// 4) /api/_auth.php com $API_KEY (a key do worker)

// ================================
// CONFIG
// ================================
$PASTA_BRUTOS = __DIR__ . '/brutos';
$BRUTOS_URL_PREFIX = 'brutos/';

// A sua API KEY (mesma do /api/_auth.php) — para facilitar o copy/paste do comando do worker
$API_KEY = 'a4aLYTawyy4HEUGQIoHCSjDOtSrxh4SA';

// include DB (mysqli)
require_once __DIR__ . '/api/db.php';

// valida $conn
if (!isset($conn) || !($conn instanceof mysqli)) {
    http_response_code(500);
    echo "<pre>ERRO: Conexão inválida. O arquivo /api/db.php precisa definir \$conn como mysqli.</pre>";
    exit;
}

// cria pasta brutos se não existir
if (!is_dir($PASTA_BRUTOS)) {
    @mkdir($PASTA_BRUTOS, 0777, true);
    @chmod($PASTA_BRUTOS, 0777);
}

// ================================
// HELPERS
// ================================
function h($s) { return htmlspecialchars((string)$s, ENT_QUOTES, 'UTF-8'); }

function badge_status($st) {
    $st = (string)$st;
    if ($st === 'pendente')  return "<span class='bg-yellow-100 text-yellow-800 py-1 px-3 rounded-full text-xs font-bold border border-yellow-200'>Pendente</span>";
    if ($st === 'baixando')  return "<span class='bg-indigo-100 text-indigo-800 py-1 px-3 rounded-full text-xs font-bold border border-indigo-200'>Baixando</span>";
    if ($st === 'editando')  return "<span class='bg-blue-100 text-blue-800 py-1 px-3 rounded-full text-xs font-bold border border-blue-200'><i class='fa-solid fa-spinner fa-spin mr-1'></i>Editando</span>";
    if ($st === 'concluido') return "<span class='bg-green-100 text-green-800 py-1 px-3 rounded-full text-xs font-bold border border-green-200'>Concluído</span>";
    if ($st === 'erro')      return "<span class='bg-red-100 text-red-800 py-1 px-3 rounded-full text-xs font-bold border border-red-200'>Erro</span>";
    return "<span class='bg-gray-100 text-gray-800 py-1 px-3 rounded-full text-xs font-bold border border-gray-200'>".h($st)."</span>";
}

// ================================
// FLASH MSG
// ================================
$mensagem = '';
if (isset($_GET['msg'])) {
    if ($_GET['msg'] === 'sucesso') {
        $ok = (int)($_GET['ok'] ?? 1);
        $fail = (int)($_GET['fail'] ?? 0);
        $warn = $_GET['warn'] ?? '';
        $txt = "✅ Upload concluído: <b>{$ok}</b> arquivo(s) enfileirado(s)";
        if ($fail > 0) $txt .= " • <b>{$fail}</b> falharam";
        if (is_string($warn) && $warn !== '') $txt .= "<div class='mt-1 text-xs text-green-800 font-normal'>Aviso: " . h($warn) . "</div>";
        $mensagem = "<div class='bg-green-100 border-l-4 border-green-500 text-green-700 p-4 mb-4 shadow text-sm font-semibold'>{$txt}</div>";
    }
    if ($_GET['msg'] === 'erro')      $mensagem = "<div class='bg-red-100 border-l-4 border-red-500 text-red-700 p-4 mb-4 shadow text-sm font-semibold'>❌ Erro: ".h($_GET['err'] ?? 'Falha')."</div>";
    if ($_GET['msg'] === 'excluida')  $mensagem = "<div class='bg-yellow-100 border-l-4 border-yellow-500 text-yellow-700 p-4 mb-4 shadow text-sm font-semibold'>🗑️ Tarefa excluída e bruto removido (se existia).</div>";
    if ($_GET['msg'] === 'reset')     $mensagem = "<div class='bg-blue-100 border-l-4 border-blue-500 text-blue-700 p-4 mb-4 shadow text-sm font-semibold'>🔄 Tarefa resetada para Pendente.</div>";
    if ($_GET['msg'] === 'resetall')  $mensagem = "<div class='bg-blue-100 border-l-4 border-blue-500 text-blue-700 p-4 mb-4 shadow text-sm font-semibold'>🧯 Travadas antigas foram resetadas para Pendente.</div>";
    if ($_GET['msg'] === 'lote_excluido') {
        $n = (int)($_GET['n'] ?? 0);
        $mensagem = "<div class='bg-red-100 border-l-4 border-red-500 text-red-700 p-4 mb-4 shadow text-sm font-semibold'>🗑️ {$n} tarefa(s) excluída(s) em lote e brutos removidos (se existiam).</div>";
    }
}

// ================================
// AÇÕES (GET)
// ================================
if (isset($_GET['acao'])) {
    $acao = $_GET['acao'];

    // EXCLUIR TAREFA + APAGAR BRUTO
    if ($acao === 'excluir' && isset($_GET['id'])) {
        $id = (int)$_GET['id'];
        if ($id > 0) {
            // pega bruto_arquivo
            $stmt = $conn->prepare("SELECT bruto_arquivo FROM fila_edicao WHERE id=? LIMIT 1");
            $stmt->bind_param("i", $id);
            $stmt->execute();
            $res = $stmt->get_result();
            $row = $res ? $res->fetch_assoc() : null;
            $stmt->close();

            if ($row && !empty($row['bruto_arquivo'])) {
                $path = $PASTA_BRUTOS . '/' . basename($row['bruto_arquivo']);
                if (file_exists($path)) @unlink($path);
            }

            $stmt2 = $conn->prepare("DELETE FROM fila_edicao WHERE id=?");
            $stmt2->bind_param("i", $id);
            $stmt2->execute();
            $stmt2->close();
        }

        header("Location: dashboard_master.php?msg=excluida");
        exit;
    }

    // REPROCESSAR: volta para pendente e limpa erro/worker
    if ($acao === 'reprocessar' && isset($_GET['id'])) {
        $id = (int)$_GET['id'];
        if ($id > 0) {
            $status = 'pendente';
            $worker = null;
            $erro = null;
            $stmt = $conn->prepare("UPDATE fila_edicao SET status=?, worker_id=?, erro_msg=?, updated_at=NOW() WHERE id=?");
            $stmt->bind_param("sssi", $status, $worker, $erro, $id);
            $stmt->execute();
            $stmt->close();
        }
        header("Location: dashboard_master.php?msg=reset");
        exit;
    }

    // RESETAR TRAVADAS antigas (baixando/editando) por tempo
    if ($acao === 'reset_travadas') {
        $min = (int)($_GET['min'] ?? 30); // minutos
        if ($min < 5) $min = 5;
        if ($min > 1440) $min = 1440;

        // MySQL: NOW() - INTERVAL ? MINUTE
        $statusP = 'pendente';
        $worker = null;
        $erro = null;

        // não dá para bindar INTERVAL diretamente em prepare de forma simples; usamos int sanitizado
        $sql = "
          UPDATE fila_edicao
          SET status='pendente', worker_id=NULL, erro_msg=NULL, updated_at=NOW()
          WHERE status IN ('baixando','editando')
            AND updated_at < (NOW() - INTERVAL $min MINUTE)
        ";
        $conn->query($sql);

        header("Location: dashboard_master.php?msg=resetall");
        exit;
    }
}

// ================================
// EXCLUIR EM LOTE (POST)
// ================================
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['acao']) && $_POST['acao'] === 'excluir_lote') {
    $ids = isset($_POST['ids']) && is_array($_POST['ids']) ? $_POST['ids'] : [];
    $deletados = 0;
    foreach ($ids as $rawId) {
        $id = (int)$rawId;
        if ($id <= 0) continue;

        $stmt = $conn->prepare("SELECT bruto_arquivo FROM fila_edicao WHERE id=? LIMIT 1");
        $stmt->bind_param("i", $id);
        $stmt->execute();
        $res = $stmt->get_result();
        $row = $res ? $res->fetch_assoc() : null;
        $stmt->close();

        if ($row && !empty($row['bruto_arquivo'])) {
            $path = $PASTA_BRUTOS . '/' . basename($row['bruto_arquivo']);
            if (file_exists($path)) @unlink($path);
        }

        $stmt2 = $conn->prepare("DELETE FROM fila_edicao WHERE id=?");
        $stmt2->bind_param("i", $id);
        $stmt2->execute();
        $deletados += (int)$stmt2->affected_rows;
        $stmt2->close();
    }
    header("Location: dashboard_master.php?msg=lote_excluido&n=" . $deletados);
    exit;
}

// ================================
// UPLOAD (POST): cria tarefa + salva bruto (multi-arquivo)
// ================================
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_FILES['video'])) {
    try {
        $vmos_id = preg_replace('/[^a-zA-Z0-9_]/', '', $_POST['vmos_id'] ?? '');
        $legenda = ''; // removido do painel, mantido vazio por compatibilidade com a coluna

        if ($vmos_id === '') {
            throw new Exception("vmos_id é obrigatório.");
        }

        $f = $_FILES['video'];

        // Normaliza para lista (suporta 1 ou múltiplos arquivos)
        $names = is_array($f['name'] ?? null) ? $f['name'] : [($f['name'] ?? '')];
        $tmps  = is_array($f['tmp_name'] ?? null) ? $f['tmp_name'] : [($f['tmp_name'] ?? '')];
        $errs  = is_array($f['error'] ?? null) ? $f['error'] : [($f['error'] ?? UPLOAD_ERR_NO_FILE)];

        $ok = 0;
        $fail = 0;
        $firstErr = null;

        for ($i = 0; $i < count($names); $i++) {
            $orig = $names[$i] ?? 'video.mp4';
            $tmp  = $tmps[$i] ?? '';
            $errc = $errs[$i] ?? UPLOAD_ERR_NO_FILE;

            if ($errc !== UPLOAD_ERR_OK) {
                $fail++;
                if ($firstErr === null) $firstErr = "Erro no upload do arquivo {$orig} (code {$errc}).";
                continue;
            }

            if (!is_uploaded_file($tmp)) {
                $fail++;
                if ($firstErr === null) $firstErr = "Upload inválido para o arquivo {$orig}.";
                continue;
            }

            $ext = strtolower(pathinfo($orig, PATHINFO_EXTENSION));
            if ($ext === '') $ext = 'mp4';

            $nome_unico = $vmos_id . "_raw_" . time() . "_" . bin2hex(random_bytes(4)) . "." . $ext;
            $destino = $PASTA_BRUTOS . "/" . $nome_unico;

            if (!move_uploaded_file($tmp, $destino)) {
                $fail++;
                if ($firstErr === null) $firstErr = "Falha ao salvar bruto em /brutos ({$orig}).";
                continue;
            }
            @chmod($destino, 0666);

            // Insere tarefa
            $status = 'pendente';
            $stmt = $conn->prepare("INSERT INTO fila_edicao (vmos_id, legenda, bruto_arquivo, status) VALUES (?, ?, ?, ?)");
            if (!$stmt) {
                @unlink($destino);
                $fail++;
                if ($firstErr === null) $firstErr = "Prepare falhou: " . $conn->error;
                continue;
            }
            $stmt->bind_param("ssss", $vmos_id, $legenda, $nome_unico, $status);
            if (!$stmt->execute()) {
                $stmt->close();
                @unlink($destino);
                $fail++;
                if ($firstErr === null) $firstErr = "Execute falhou: " . $stmt->error;
                continue;
            }
            $stmt->close();

            $ok++;
        }

        if ($ok > 0) {
            $qs = "msg=sucesso&ok={$ok}&fail={$fail}";
            if ($fail > 0 && $firstErr) $qs .= "&warn=" . urlencode($firstErr);
            header("Location: dashboard_master.php?{$qs}");
            exit;
        }

        // se nenhum arquivo entrou
        $err = urlencode($firstErr ?: "Nenhum arquivo foi enviado.");
        header("Location: dashboard_master.php?msg=erro&err={$err}");
        exit;

    } catch (Throwable $e) {
        $err = urlencode($e->getMessage());
        header("Location: dashboard_master.php?msg=erro&err={$err}");
        exit;
    }
}

// ================================
// LISTAGEM FILA (últimas 50)
// ================================
$filtro_status = $_GET['status'] ?? '';
$validStatus = ['','pendente','baixando','editando','concluido','erro'];
if (!in_array($filtro_status, $validStatus, true)) $filtro_status = '';

$limit = 50;

// Detecta se a coluna resultado_arquivo existe (compatibilidade antes da migração)
$tem_resultado_col = false;
$chk = $conn->query("SHOW COLUMNS FROM fila_edicao LIKE 'resultado_arquivo'");
if ($chk && $chk->num_rows > 0) $tem_resultado_col = true;
$sel_resultado = $tem_resultado_col ? ", resultado_arquivo" : ", NULL AS resultado_arquivo";

if ($filtro_status === '') {
    $sql = "SELECT id, vmos_id, bruto_arquivo, status, worker_id, erro_msg, created_at, updated_at $sel_resultado
            FROM fila_edicao
            ORDER BY id DESC
            LIMIT $limit";
    $res = $conn->query($sql);
} else {
    $stmt = $conn->prepare("SELECT id, vmos_id, bruto_arquivo, status, worker_id, erro_msg, created_at, updated_at $sel_resultado
                            FROM fila_edicao
                            WHERE status=?
                            ORDER BY id DESC
                            LIMIT $limit");
    $stmt->bind_param("s", $filtro_status);
    $stmt->execute();
    $res = $stmt->get_result();
    $stmt->close();
}

$fila_atual = [];
if ($res) {
    while ($row = $res->fetch_assoc()) {
        $fila_atual[] = $row;
    }
}

// contagens rápidas
$counts = ['pendente'=>0,'baixando'=>0,'editando'=>0,'concluido'=>0,'erro'=>0];
$rc = $conn->query("SELECT status, COUNT(*) as c FROM fila_edicao GROUP BY status");
if ($rc) {
    while ($r = $rc->fetch_assoc()) {
        $st = $r['status'];
        if (isset($counts[$st])) $counts[$st] = (int)$r['c'];
    }
}
?>
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Painel Central | Fábrica Kwai</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
</head>
<body class="bg-gray-100 font-sans leading-normal tracking-normal">
<div class="flex flex-col md:flex-row min-h-screen">
    
    <!-- SIDEBAR -->
    <div class="bg-gray-900 shadow-xl w-full md:w-64 flex-shrink-0 md:sticky md:top-0 md:h-screen z-20">
        <div class="p-4 md:p-6">
            <!-- Título + toggle mobile -->
            <div class="flex items-center justify-between md:block">
                <h1 class="text-white text-xl md:text-2xl font-bold uppercase tracking-wider">
                    <i class="fa-solid fa-robot mr-2 text-blue-500"></i> Fábrica Master
                </h1>
                <button id="sidebarToggle"
                        class="md:hidden text-gray-300 hover:text-white bg-gray-800 hover:bg-gray-700 rounded p-2 transition"
                        aria-label="Expandir/recolher menu">
                    <i id="sidebarToggleIcon" class="fa-solid fa-chevron-down text-sm"></i>
                </button>
            </div>

            <!-- Conteúdo colapsável no mobile -->
            <div id="sidebarContent" class="hidden md:block">
                <!-- Estatísticas -->
                <div class="mt-4 text-sm text-gray-300 grid grid-cols-2 gap-x-4 gap-y-1 md:block md:space-y-2 bg-gray-800 rounded p-3">
                    <div><span class="font-bold text-yellow-300"><?= (int)$counts['pendente'] ?></span> pendentes</div>
                    <div><span class="font-bold text-indigo-300"><?= (int)$counts['baixando'] ?></span> baixando</div>
                    <div><span class="font-bold text-blue-300"><?= (int)$counts['editando'] ?></span> editando</div>
                    <div><span class="font-bold text-green-300"><?= (int)$counts['concluido'] ?></span> concluídos</div>
                    <div class="col-span-2 md:col-span-1"><span class="font-bold text-red-300"><?= (int)$counts['erro'] ?></span> erros</div>
                </div>

                <div class="mt-4 space-y-2">
                    <a class="flex items-center text-sm text-gray-200 hover:text-white bg-gray-800 hover:bg-gray-700 rounded px-3 py-2 transition"
                       href="dashboard_master.php?status=concluido">
                        <i class="fa-solid fa-check-circle mr-2 text-green-400 w-4"></i> Ver concluídos
                    </a>
                    <a class="flex items-center text-sm text-gray-200 hover:text-white bg-gray-800 hover:bg-gray-700 rounded px-3 py-2 transition"
                       href="dashboard_master.php?status=erro">
                        <i class="fa-solid fa-triangle-exclamation mr-2 text-red-400 w-4"></i> Ver com erro
                    </a>
                    <a class="flex items-center text-sm text-gray-200 hover:text-white bg-gray-800 hover:bg-gray-700 rounded px-3 py-2 transition"
                       href="dashboard_master.php?acao=reset_travadas&min=30"
                       onclick="return confirm('Resetar tarefas BAIXANDO/EDITANDO com updated_at > 30min para PENDENTE?');">
                        <i class="fa-solid fa-fire-extinguisher mr-2 text-blue-400 w-4"></i> Resetar travadas (30min)
                    </a>
                    <a class="flex items-center text-sm text-gray-200 hover:text-white bg-gray-800 hover:bg-gray-700 rounded px-3 py-2 transition"
                       href="dashboard_master.php">
                        <i class="fa-solid fa-rotate mr-2 text-gray-400 w-4"></i> Atualizar página
                    </a>
                </div>
            </div>
        </div>
    </div>

    <!-- ÁREA PRINCIPAL -->
    <div class="w-full flex-col flex-1 overflow-y-auto">
        <main class="w-full p-4 md:p-6">
            <h1 class="text-2xl md:text-3xl text-gray-800 font-medium mb-3">Controle de Produção</h1>
            <?= $mensagem ?>

            <!-- Worker Command -->
            <div class="bg-white rounded-lg shadow-lg p-4 mb-6">
                <h2 class="text-lg font-semibold text-gray-700 mb-2 border-b pb-2">
                    <i class="fa-solid fa-desktop mr-2 text-purple-500"></i> Worker Local (Windows)
                </h2>
                <p class="text-sm text-gray-600 mb-2">
                    O worker fica puxando tarefas pendentes, baixa o bruto, edita e sobe o editado (que vira vídeo na fila do VMOS).
                    Configure <code class="bg-gray-100 px-1 rounded text-xs">WORKER_ID</code> e os caminhos na classe <code class="bg-gray-100 px-1 rounded text-xs">Config</code> do arquivo antes de rodar.
                </p>
                <pre class="bg-gray-900 text-gray-100 text-xs p-3 rounded overflow-auto"><?=
h("# Rodar worker (PowerShell / CMD — na pasta D:\\automacao_videos)\n".
  "D:\\automacao_videos\\.venv\\Scripts\\python.exe D:\\automacao_videos\\worker_edicao.py\n\n".
  "# Identificar este PC como worker específico (opcional):\n".
  "set WORKER_ID=PC01 && D:\\automacao_videos\\.venv\\Scripts\\python.exe D:\\automacao_videos\\worker_edicao.py")
?></pre>
            </div>

            <div class="flex flex-wrap -mx-3">
                
                <!-- PAINEL DE UPLOAD -->
                <div class="w-full lg:w-1/3 px-3 mb-6">
                    <div class="bg-white rounded-lg shadow-lg p-6">
                        <h2 class="text-lg font-semibold text-gray-700 mb-4 border-b pb-2">
                            <i class="fa-solid fa-cloud-arrow-up mr-2 text-blue-500"></i> Nova Ordem (Upload Bruto)
                        </h2>
                        <form method="POST" enctype="multipart/form-data">
                            <div class="mb-4">
                                <label class="block text-gray-700 text-sm font-bold mb-2">Conta VMOS</label>
                                <input type="text" name="vmos_id"
                                       class="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none"
                                       required placeholder="Ex: conta_01">
                            </div>
<div class="mb-6">
                                <label class="block text-gray-700 text-sm font-bold mb-2">Vídeos Brutos (selecione 1 ou mais)</label>
                                <input type="file" name="video[]" multiple accept="video/mp4,video/quicktime,video/x-matroska,video/webm,video/x-m4v"
                                       class="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                                       required>
                                <p class="mt-2 text-xs text-gray-500" id="fileCountHint">Nenhum arquivo selecionado.</p>
                                <p class="text-xs text-gray-500 mt-2">
                                    O bruto será salvo em <b>/brutos/</b> e entrará na tabela <b>fila_edicao</b> como <b>pendente</b>.
                                </p>
                            </div>

                            <button type="submit"
                                    class="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded focus:outline-none transition">
                                <i class="fa-solid fa-plus mr-2"></i> Criar Tarefa de Edição
                            </button>
                        </form>
                    </div>
                </div>

                <!-- TABELA DE GERENCIAMENTO DA FILA -->
                <div class="w-full lg:w-2/3 px-3 mb-6">
                    <div class="bg-white rounded-lg shadow-lg p-6 h-full">
                        <div class="flex items-center justify-between gap-3 mb-4 border-b pb-2">
                            <h2 class="text-lg font-semibold text-gray-700">
                                <i class="fa-solid fa-list-check mr-2 text-green-500"></i> Esteira Operacional (fila_edicao)
                            </h2>

                            <form method="GET" class="flex items-center gap-2">
                                <input type="hidden" name="page" value="1">
                                <select name="status" class="border rounded px-2 py-1 text-sm">
                                    <option value="" <?= $filtro_status===''?'selected':'' ?>>Todos</option>
                                    <option value="pendente" <?= $filtro_status==='pendente'?'selected':'' ?>>Pendente</option>
                                    <option value="baixando" <?= $filtro_status==='baixando'?'selected':'' ?>>Baixando</option>
                                    <option value="editando" <?= $filtro_status==='editando'?'selected':'' ?>>Editando</option>
                                    <option value="concluido" <?= $filtro_status==='concluido'?'selected':'' ?>>Concluído</option>
                                    <option value="erro" <?= $filtro_status==='erro'?'selected':'' ?>>Erro</option>
                                </select>
                                <button class="bg-gray-800 hover:bg-gray-900 text-white rounded px-3 py-1 text-sm">
                                    Filtrar
                                </button>
                            </form>
                        </div>
                        
                        
                        <!-- Toolbar de exclusão em lote -->
                        <div id="bulkToolbar" class="hidden mb-3 flex flex-wrap items-center gap-3 bg-red-50 border border-red-200 rounded-lg p-3">
                            <i class="fa-solid fa-trash-can text-red-500"></i>
                            <span id="bulkCount" class="text-sm font-semibold text-red-700">0 selecionado(s)</span>
                            <button type="button" onclick="submitBulkDelete()"
                                    class="bg-red-600 hover:bg-red-700 text-white px-4 py-1.5 rounded text-sm font-semibold transition">
                                <i class="fa-solid fa-trash-can mr-1"></i> Excluir selecionados
                            </button>
                            <button type="button" onclick="clearSelection()"
                                    class="bg-gray-200 hover:bg-gray-300 text-gray-700 px-3 py-1.5 rounded text-sm transition">
                                Limpar seleção
                            </button>
                        </div>

                        <form method="POST" id="formLote">
                        <input type="hidden" name="acao" value="excluir_lote">

                        <!-- MOBILE: Cards -->
                        <div class="md:hidden space-y-3">
                            <?php if (empty($fila_atual)): ?>
                                <div class="text-center py-8 text-gray-500">
                                    Nenhuma tarefa encontrada.
                                </div>
                            <?php else: ?>
                                <?php foreach ($fila_atual as $item): ?>
                                    <div class="bg-gray-50 border rounded-lg p-4 shadow-sm">
                                        <div class="flex items-start justify-between gap-3">
                                            <div class="flex items-start gap-3">
                                                <input type="checkbox" name="ids[]" value="<?= (int)$item['id'] ?>"
                                                       class="row-check mt-1 w-4 h-4 cursor-pointer accent-red-500 shrink-0">
                                                <div>
                                                    <div class="text-xs text-gray-500">Conta VMOS</div>
                                                    <div class="text-base font-bold text-gray-800"><?= h($item['vmos_id']) ?></div>
                                                </div>
                                            </div>
                                            <div class="shrink-0">
                                                <?= badge_status($item['status']) ?>
                                            </div>
                                        </div>

                                        <div class="mt-3 grid grid-cols-2 gap-3 text-sm">
                                            <div>
                                                <div class="text-xs text-gray-500">Bruto</div>
                                                <div class="text-xs text-gray-700 truncate" title="<?= h($item['bruto_arquivo']) ?>">
                                                    ...<?= h(substr($item['bruto_arquivo'], -24)) ?>
                                                </div>
                                                <a class="text-blue-600 underline text-sm"
                                                   href="<?= h($BRUTOS_URL_PREFIX . basename($item['bruto_arquivo'])) ?>"
                                                   target="_blank">Abrir</a>
                                            </div>

                                            <div>
                                                <div class="text-xs text-gray-500">Worker</div>
                                                <div class="text-sm text-gray-700"><?= h($item['worker_id'] ?? '') ?></div>

                                                <div class="text-xs text-gray-500 mt-2">Atualizado</div>
                                                <div class="text-sm text-gray-700"><?= h($item['updated_at'] ?? '') ?></div>
                                            </div>
                                        </div>

                                        <?php if (!empty($item['erro_msg'])): ?>
                                            <div class="mt-3 text-sm text-red-700 bg-red-50 border border-red-100 rounded p-2">
                                                <div class="font-semibold text-xs mb-1">Erro</div>
                                                <div class="text-xs break-words"><?= h($item['erro_msg']) ?></div>
                                            </div>
                                        <?php endif; ?>

                                        <?php if (!empty($item['resultado_arquivo'])): ?>
                                            <div class="mt-3">
                                                <a href="/videos/<?= h(basename($item['resultado_arquivo'])) ?>"
                                                   download
                                                   class="flex items-center justify-center gap-2 w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-2 rounded text-sm">
                                                    <i class="fa-solid fa-download"></i> Baixar editado
                                                </a>
                                            </div>
                                        <?php endif; ?>

                                        <div class="mt-3 flex gap-2">
                                            <a href="dashboard_master.php?acao=reprocessar&id=<?= (int)$item['id'] ?>"
                                               onclick="return confirm('Reprocessar: voltar para PENDENTE e limpar erro/worker?');"
                                               class="flex-1 text-center bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 rounded text-sm">
                                                <i class="fa-solid fa-rotate-right mr-1"></i> Reprocessar
                                            </a>

                                            <a href="dashboard_master.php?acao=excluir&id=<?= (int)$item['id'] ?>"
                                               onclick="return confirm('ATENÇÃO: excluir tarefa e apagar o bruto do servidor. Continuar?');"
                                               class="flex-1 text-center bg-red-600 hover:bg-red-700 text-white font-semibold py-2 rounded text-sm">
                                                <i class="fa-solid fa-trash-can mr-1"></i> Excluir
                                            </a>
                                        </div>
                                    </div>
                                <?php endforeach; ?>
                            <?php endif; ?>
                        </div>

                        <!-- DESKTOP: Tabela -->
                        <div class="hidden md:block overflow-x-auto mt-2">
                            <table class="min-w-full bg-white">

                                <thead class="bg-gray-800 text-white border-b">
                                    <tr>
                                        <th class="text-center py-3 px-2 w-10">
                                            <input type="checkbox" id="selectAll" title="Selecionar/Desmarcar todos"
                                                   class="w-4 h-4 cursor-pointer accent-red-500">
                                        </th>
                                        <th class="text-left py-3 px-4 uppercase font-semibold text-sm">Conta</th>
                                                                                <th class="text-center py-3 px-4 uppercase font-semibold text-sm">Bruto</th>
                                        <th class="text-center py-3 px-4 uppercase font-semibold text-sm">Status</th>
                                        <th class="text-center py-3 px-4 uppercase font-semibold text-sm">Worker</th>
                                        <th class="text-center py-3 px-4 uppercase font-semibold text-sm">Atualizado</th>
                                        <th class="text-center py-3 px-4 uppercase font-semibold text-sm">Ações</th>
                                    </tr>
                                </thead>
                                <tbody class="text-gray-700">
                                    <?php if (empty($fila_atual)): ?>
                                        <tr>
                                            <td colspan="7" class="text-center py-8 text-gray-500">
                                                Nenhuma tarefa encontrada.
                                            </td>
                                        </tr>
                                    <?php else: ?>
                                        <?php foreach ($fila_atual as $item): ?>
                                            <tr class="border-b hover:bg-gray-50 transition align-top">
                                                <td class="text-center py-3 px-2">
                                                    <input type="checkbox" name="ids[]" value="<?= (int)$item['id'] ?>"
                                                           class="row-check w-4 h-4 cursor-pointer accent-red-500">
                                                </td>
                                                <td class="text-left py-3 px-4 font-bold text-gray-800"><?= h($item['vmos_id']) ?></td>
<td class="text-center py-3 px-4 text-xs text-gray-500">
                                                    <div title="<?= h($item['bruto_arquivo']) ?>">
                                                        ...<?= h(substr($item['bruto_arquivo'], -18)) ?>
                                                    </div>
                                                    <a class="text-blue-600 hover:text-blue-800 underline text-xs"
                                                       href="<?= h($BRUTOS_URL_PREFIX . basename($item['bruto_arquivo'])) ?>"
                                                       target="_blank">abrir</a>
                                                </td>

                                                <td class="text-center py-3 px-4">
                                                    <?= badge_status($item['status']) ?>
                                                    <?php if (!empty($item['erro_msg'])): ?>
                                                        <div class="text-xs text-red-600 mt-2" title="<?= h($item['erro_msg']) ?>">
                                                            <?= h(mb_strimwidth($item['erro_msg'], 0, 60, '...')) ?>
                                                        </div>
                                                    <?php endif; ?>
                                                </td>

                                                <td class="text-center py-3 px-4 text-xs text-gray-600">
                                                    <?= h($item['worker_id'] ?? '') ?>
                                                </td>

                                                <td class="text-center py-3 px-4 text-xs text-gray-600">
                                                    <?= h($item['updated_at'] ?? '') ?>
                                                </td>

                                                <td class="text-center py-3 px-4">
                                                    <div class="flex items-center justify-center gap-2 flex-wrap">

                                                        <?php if (!empty($item['resultado_arquivo'])): ?>
                                                        <a href="/videos/<?= h(basename($item['resultado_arquivo'])) ?>"
                                                           download
                                                           class="text-green-600 hover:text-green-800 bg-green-50 hover:bg-green-100 p-2 rounded transition"
                                                           title="Baixar editado (<?= h(basename($item['resultado_arquivo'])) ?>)">
                                                            <i class="fa-solid fa-download"></i>
                                                        </a>
                                                        <?php endif; ?>

                                                        <a href="dashboard_master.php?acao=reprocessar&id=<?= (int)$item['id'] ?>"
                                                           onclick="return confirm('Reprocessar: voltar para PENDENTE e limpar erro/worker?');"
                                                           class="text-blue-600 hover:text-blue-800 bg-blue-50 hover:bg-blue-100 p-2 rounded transition"
                                                           title="Reprocessar">
                                                            <i class="fa-solid fa-rotate-right"></i>
                                                        </a>

                                                        <a href="dashboard_master.php?acao=excluir&id=<?= (int)$item['id'] ?>"
                                                           onclick="return confirm('ATENÇÃO: excluir tarefa e apagar o bruto do servidor. Continuar?');"
                                                           class="text-red-500 hover:text-red-700 bg-red-50 hover:bg-red-100 p-2 rounded transition"
                                                           title="Excluir">
                                                            <i class="fa-solid fa-trash-can"></i>
                                                        </a>

                                                    </div>
                                                </td>
                                            </tr>
                                        <?php endforeach; ?>
                                    <?php endif; ?>
                                </tbody>
                            </table>
                        </div><!-- /hidden md:block -->

                        </form><!-- /formLote -->

                        <div class="mt-4 text-xs text-gray-500">
                            Mostrando as últimas <?= (int)$limit ?> tarefas<?= $filtro_status ? " (status: <b>".h($filtro_status)."</b>)" : "" ?>.
                        </div>

                    </div><!-- /bg-white card -->
                </div><!-- /w-2/3 -->

            </div>
        </main>
    </div>
</div>

<style>
/* Tailwind line clamp fallback (caso não tenha plugin) */
.line-clamp-3 {
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
}
</style>

<script>
// ── Sidebar toggle (mobile) ──────────────────────────────────────────────────
(function () {
  const btn     = document.getElementById('sidebarToggle');
  const content = document.getElementById('sidebarContent');
  const icon    = document.getElementById('sidebarToggleIcon');
  if (!btn || !content) return;

  btn.addEventListener('click', function () {
    const open = !content.classList.contains('hidden');
    content.classList.toggle('hidden', open);
    icon.classList.toggle('fa-chevron-down', open);
    icon.classList.toggle('fa-chevron-up',   !open);
  });
})();

// ── Contador de arquivos selecionados ────────────────────────────────────────
(function () {
  const input = document.querySelector('input[type="file"][name="video[]"]');
  const hint  = document.getElementById('fileCountHint');
  if (!input || !hint) return;

  function fmt(n) {
    if (n === 0) return "Nenhum arquivo selecionado.";
    if (n === 1) return "1 arquivo selecionado.";
    return n + " arquivos selecionados.";
  }

  input.addEventListener('change', function () {
    hint.textContent = fmt(input.files ? input.files.length : 0);
  });
})();

// ── Feedback visual de upload (barra de progresso simples) ───────────────────
(function () {
  const form   = document.querySelector('form[enctype="multipart/form-data"]');
  const btn    = form ? form.querySelector('button[type="submit"]') : null;
  if (!form || !btn) return;

  form.addEventListener('submit', function () {
    const original = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-2"></i> Enviando...';
    // Restaura após 60s por segurança (caso o servidor demore ou dê erro)
    setTimeout(function () {
      btn.disabled = false;
      btn.innerHTML = original;
    }, 60000);
  });
})();

// ── Seleção em lote ───────────────────────────────────────────────────────────
(function () {
  const selectAll  = document.getElementById('selectAll');
  const toolbar    = document.getElementById('bulkToolbar');
  const countLabel = document.getElementById('bulkCount');
  const formLote   = document.getElementById('formLote');

  function getChecked() {
    return Array.from(document.querySelectorAll('.row-check:checked'));
  }

  function updateToolbar() {
    const checked = getChecked();
    const n = checked.length;
    if (n > 0) {
      toolbar.classList.remove('hidden');
      countLabel.textContent = n + ' selecionado(s)';
    } else {
      toolbar.classList.add('hidden');
    }
    if (selectAll) {
      const all = document.querySelectorAll('.row-check');
      selectAll.checked       = all.length > 0 && n === all.length;
      selectAll.indeterminate = n > 0 && n < all.length;
    }
  }

  if (selectAll) {
    selectAll.addEventListener('change', function () {
      document.querySelectorAll('.row-check').forEach(function (cb) {
        cb.checked = selectAll.checked;
      });
      updateToolbar();
    });
  }

  document.querySelectorAll('.row-check').forEach(function (cb) {
    cb.addEventListener('change', updateToolbar);
  });

  window.submitBulkDelete = function () {
    const n = getChecked().length;
    if (n === 0) return;
    if (!confirm('ATENÇÃO: excluir ' + n + ' tarefa(s) e apagar os brutos do servidor. Continuar?')) return;
    formLote.submit();
  };

  window.clearSelection = function () {
    document.querySelectorAll('.row-check').forEach(function (cb) { cb.checked = false; });
    if (selectAll) { selectAll.checked = false; selectAll.indeterminate = false; }
    updateToolbar();
  };
})();
</script>

</body>
</html>