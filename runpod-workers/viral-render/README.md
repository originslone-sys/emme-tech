# Worker de Render Viral (RunPod Serverless)

Monta o vídeo viral na GPU: baixa os clipes do Pexels, corta/escala cada cena,
concatena, queima as legendas e mixa a trilha — usando `h264_nvenc` (NVENC).
O backend usa este worker quando `RUNPOD_RENDER_ENDPOINT` está configurado;
caso contrário, faz o render localmente na CPU.

## Build e deploy

```bash
cd runpod-workers/viral-render

# 1. Build da imagem
docker build -t SEU_USUARIO/emme-viral-render:latest .

# 2. Push para um registry (Docker Hub, GHCR, etc.)
docker push SEU_USUARIO/emme-viral-render:latest
```

No painel do RunPod:

1. **Serverless → New Endpoint**
2. Container Image: `SEU_USUARIO/emme-viral-render:latest`
3. GPU: qualquer uma com NVENC (ex: RTX A4000/4090) — vídeos curtos são rápidos
4. Container Disk: ~10 GB
5. Copie o **Endpoint ID** e coloque no backend como `RUNPOD_RENDER_ENDPOINT`

## Contrato

**Input**

```json
{
  "input": {
    "scenes": [
      {"video_url": "https://.../clip.mp4", "duration": 3.0, "text": "TEXTO NA TELA"}
    ],
    "width": 1080,
    "height": 1920,
    "music_url": ""
  }
}
```

- `video_url` vazio em uma cena → fundo escuro com a legenda (fallback).
- `music_url` precisa ser uma URL pública (o áudio enviado pelo usuário é
  servido pelo backend em `/files/uploads/...`).

**Output**

```json
{ "video_base64": "<mp4 em base64>" }
```

O backend decodifica e salva na biblioteca. Para vídeos longos, considere
trocar o retorno por upload para um bucket S3 (RunPod tem limite de payload).
