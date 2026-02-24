<?php
// painel_edicao_local.php
$job_file = __DIR__ . '/api/edicao_job.json';

function h($s){ return htmlspecialchars($s ?? "", ENT_QUOTES, 'UTF-8'); }

$msg = "";

$job = [
  "status" => "idle",
  "vmos_id" => "",
  "legenda" => "",
  "max_videos" => 1,
  "on_success" => "move", // move|delete|keep
  "clean_output_after_upload" => false,
];

if (file_exists($job_file)) {
  $tmp = json_decode(file_get_contents($job_file), true);
  if (is_array($tmp)) $job = array_merge($job, $tmp);
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
  $vmos_id = preg_replace('/[^a-zA-Z0-9_]/', '', $_POST['vmos_id'] ?? '');
  $legenda = $_POST['legenda'] ?? '';
  $max_videos = (int)($_POST['max_videos'] ?? 1);
  if ($max_videos < 1) $max_videos = 1;
  if ($max_videos > 50) $max_videos = 50;

  $on_success = $_POST['on_success'] ?? 'move';
  if (!in_array($on_success, ['move','delete','keep'])) $on_success = 'move';

  $clean_output_after_upload = isset($_POST['clean_output_after_upload']) ? true : false;

  // cria job novo
  $nonce = bin2hex(random_bytes(8));
  $job = [
    "status" => "pending",
    "nonce" => $nonce,
    "vmos_id" => $vmos_id,
    "legenda" => $legenda,
    "max_videos" => $max_videos,
    "on_success" => $on_success,
    "clean_output_after_upload" => $clean_output_after_upload,
    "created_at" => date('c'),
    "updated_at" => date('c'),
    "result_ok" => 0,
    "result_fail" => 0,
    "message" => "",
  ];

  $written = file_put_contents($job_file, json_encode($job, JSON_PRETTY_PRINT|JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES));
  if ($written === false) {
    $msg = "❌ Erro ao salvar o job. Verifique permissões de escrita em /api/.";
  } else {
    $msg = "✅ Job criado: o seu PC pode puxar e executar agora.";
  }
}
?>
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Painel - Edição Local</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-100">
  <div class="max-w-3xl mx-auto p-6">
    <h1 class="text-2xl font-bold mb-4">🧰 Painel — Edição Local (Worker no seu PC)</h1>

    <?php if($msg): ?>
      <div class="bg-green-100 border border-green-300 text-green-800 p-3 rounded mb-4"><?= h($msg) ?></div>
    <?php endif; ?>

    <div class="bg-white rounded shadow p-5 mb-6">
      <h2 class="font-semibold mb-3">Criar Job</h2>

      <form method="POST" class="space-y-4">
        <div>
          <label class="block text-sm font-medium">VMOS ID (destino do upload)</label>
          <input name="vmos_id" value="<?= h($job['vmos_id']) ?>" class="w-full border rounded p-2" placeholder="teste_02" required>
        </div>

        <div>
          <label class="block text-sm font-medium">Legenda</label>
          <textarea name="legenda" class="w-full border rounded p-2" rows="4" placeholder="Opcional"><?= h($job['legenda']) ?></textarea>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div>
            <label class="block text-sm font-medium">Qtd vídeos (da pasta input)</label>
            <input type="number" min="1" max="50" name="max_videos" value="<?= h((string)$job['max_videos']) ?>" class="w-full border rounded p-2">
          </div>

          <div>
            <label class="block text-sm font-medium">Após sucesso (bruto)</label>
            <select name="on_success" class="w-full border rounded p-2">
              <option value="move" <?= ($job['on_success']==='move'?'selected':'') ?>>Mover p/ processed</option>
              <option value="delete" <?= ($job['on_success']==='delete'?'selected':'') ?>>Deletar</option>
              <option value="keep" <?= ($job['on_success']==='keep'?'selected':'') ?>>Manter</option>
            </select>
          </div>

          <div class="flex items-end">
            <label class="inline-flex items-center gap-2">
              <input type="checkbox" name="clean_output_after_upload" <?= ($job['clean_output_after_upload'] ? 'checked' : '') ?>>
              <span class="text-sm">Apagar editado após upload</span>
            </label>
          </div>
        </div>

        <button class="bg-blue-600 hover:bg-blue-700 text-white rounded px-4 py-2 font-semibold">
          Criar Job (Executar no PC)
        </button>
      </form>
    </div>

    <div class="bg-white rounded shadow p-5">
      <h2 class="font-semibold mb-3">Status atual do Job</h2>
      <pre class="bg-slate-900 text-slate-100 p-3 rounded overflow-auto text-sm"><?= h(json_encode($job, JSON_PRETTY_PRINT|JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES)) ?></pre>
      <p class="text-sm text-slate-600 mt-2">
        Status possíveis: idle / pending / running / done / error.
      </p>
    </div>
  </div>
</body>
</html>