<?php
// Onde a ordem de serviço será salva
$arquivo_ordem = 'api/ordem.json';

// Se você enviou o formulário, ele salva as novas regras
$mensagem = "";
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $dados = [
        'vmos_id' => $_POST['vmos_id'] ?? 'teste_01',
        'legenda' => $_POST['legenda'] ?? ''
    ];
    
    // Cria a pasta api se não existir
    if (!is_dir('api')) {
        mkdir('api', 0755, true);
    }
    
    file_put_contents($arquivo_ordem, json_encode($dados));
    $mensagem = "✅ Ordem de Serviço atualizada! Os próximos vídeos do robô usarão essas regras.";
}

// Lê a ordem atual para mostrar na tela
$ordem_atual = ['vmos_id' => '', 'legenda' => ''];
if (file_exists($arquivo_ordem)) {
    $ordem_atual = json_decode(file_get_contents($arquivo_ordem), true);
}
?>
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Comando da Fábrica Kwai</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f4f4f9; padding: 20px; }
        .card { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); max-width: 500px; margin: auto; }
        input, textarea, button { width: 100%; margin-top: 10px; padding: 10px; border-radius: 5px; border: 1px solid #ccc; box-sizing: border-box;}
        button { background: #28a745; color: white; font-weight: bold; border: none; cursor: pointer; margin-top: 20px;}
        button:hover { background: #218838; }
        .msg { background: #d4edda; color: #155724; padding: 10px; border-radius: 5px; margin-bottom: 20px;}
    </style>
</head>
<body>

<div class="card">
    <h2>🎯 Configurar Lote de Vídeos</h2>
    <p>O robô do Google Cloud perguntará para esta página para onde enviar os vídeos.</p>
    
    <?php if($mensagem) echo "<div class='msg'>$mensagem</div>"; ?>

    <form method="POST">
        <label><b>Nome/ID da Conta Kwai/VMOS:</b></label>
        <input type="text" name="vmos_id" value="<?php echo htmlspecialchars($ordem_atual['vmos_id']); ?>" placeholder="Ex: conta_joao_01" required>

        <label style="display:block; margin-top:15px;"><b>Legenda da Postagem:</b></label>
        <textarea name="legenda" rows="4" placeholder="Ex: Vídeo incrível! 🚀 #viral" required><?php echo htmlspecialchars($ordem_atual['legenda']); ?></textarea>

        <button type="submit">Atualizar Fábrica</button>
    </form>
</div>

</body>
</html>