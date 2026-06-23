# Deploy dos endpoints RunPod — passo a passo

O emme usa o RunPod Serverless para as tarefas pesadas. São **4 endpoints**,
mas só os necessários para as funções que você vai usar precisam existir.
Cada endpoint vira uma variável de ambiente no backend.

| Endpoint | Variável | Usado por | Obrigatório? | Worker |
|---|---|---|---|---|
| Transcrição | `RUNPOD_WHISPER_ENDPOINT` | Cortes Virais | Sim (p/ cortes) | RunPod Hub (WhisperX) |
| Upscaling | `RUNPOD_ENHANCE_ENDPOINT` | Editar Vídeo (melhorar qualidade) | Só p/ upscaling | Externo / Hub |
| Render viral | `RUNPOD_RENDER_ENDPOINT` | Gerar Vídeo Viral | **Opcional** (fallback CPU local) | `runpod-workers/viral-render` |
| Narração (TTS) | `RUNPOD_TTS_ENDPOINT` | Gerar Vídeo Viral | **Opcional** (fallback gTTS local) | `runpod-workers/viral-tts` |

> Os dois últimos têm **fallback local**: sem eles, o gerador de vídeo viral
> funciona mesmo assim (render na CPU do backend e narração via gTTS). Os
> endpoints só deixam tudo mais rápido e com voz mais natural.

Antes de começar, tenha:
- Conta no RunPod com **API Key** → vira `RUNPOD_API_KEY` no backend.
- Uma conta de registry de imagens (Docker Hub, GHCR, etc.) para os workers próprios.
- O backend acessível por uma **URL pública** → `BACKEND_URL` (os workers baixam
  áudio/arquivos servidos em `/files/uploads/...`).

---

## 1) Transcrição — WhisperX (do RunPod Hub)

Necessário para **Cortes Virais** (transcreve o áudio para a IA escolher os trechos).

1. No RunPod: **Serverless → Explore / Hub**.
2. Procure por **WhisperX** (worker do `kodxana`, "WhisperX Worker").
3. Faça o deploy. Ele pede um **Hugging Face token** (para baixar o modelo) —
   crie um token gratuito em huggingface.co e cole na config do endpoint.
4. GPU pequena já resolve (ex: RTX A4000). Crie o endpoint.
5. Copie o **Endpoint ID** → backend: `RUNPOD_WHISPER_ENDPOINT`.

Contrato esperado pelo backend (já compatível com esse worker): input
`audio_file` (URL) e saída em `segments` com `start/end/text`.

---

## 2) Upscaling de vídeo (opcional — só p/ "melhorar qualidade")

Necessário **apenas** se você usar a opção de upscaling em **Editar Vídeo**.
Não há worker próprio neste repositório — use um worker de upscaling de vídeo
(ex: Real-ESRGAN/vídeo) do Hub ou um seu.

O backend envia:
```json
{ "input": { "video_url": "https://.../video.mp4", "scale": 2 } }
```
e espera o vídeo de volta em `output` (URL ou base64).

1. Faça deploy de um endpoint de upscaling compatível com esse contrato.
2. Copie o **Endpoint ID** → backend: `RUNPOD_ENHANCE_ENDPOINT`.

Se você não vai usar upscaling, pode deixar essa variável vazia.

---

## ⚠️ Importante: os workers 3 e 4 NÃO estão no RunPod Hub

`viral-render` e `viral-tts` são **workers próprios deste repositório** — não
adianta procurar no Hub, eles não aparecem lá. Você faz o deploy do código que
está em `runpod-workers/`. Há duas formas:

- **Forma A — Deploy pelo GitHub (recomendada, sem Docker no seu PC):** o RunPod
  faz o build do Dockerfile direto do repositório.
- **Forma B — Build manual:** você builda a imagem Docker e dá push num registry.

---

## 3) Render viral na GPU (opcional — recomendado p/ velocidade)

Monta o vídeo viral na GPU (corta, concatena, legenda, mixa narração+música).
Sem ele, o backend monta na CPU (mais lento).

**Forma A — Deploy pelo GitHub (sem Docker local):**
1. No RunPod: **Serverless → New Endpoint → Import Git Repository**
   (conecte sua conta GitHub e autorize o repositório `originslone-sys/emme-tech`).
2. Branch: a sua branch de deploy.
3. **Dockerfile Path:** `runpod-workers/viral-render/Dockerfile`
4. **Build Context:** deixe **em branco** (a raiz do repositório). Os `COPY` do
   Dockerfile já apontam o caminho completo a partir da raiz.
5. GPU com NVENC (ex: RTX A4000/4090), disco ~10 GB → Deploy.
6. Copie o **Endpoint ID** → backend: `RUNPOD_RENDER_ENDPOINT`.

**Forma B — Build manual:**
```bash
cd runpod-workers/viral-render
docker build -t SEU_USUARIO/emme-viral-render:latest .
docker push SEU_USUARIO/emme-viral-render:latest
```
Depois: **New Endpoint** → Container Image `SEU_USUARIO/emme-viral-render:latest`.

Detalhes e contrato: `runpod-workers/viral-render/README.md`.

---

## 4) Narração / TTS na GPU (opcional — voz natural)

Gera a narração com **XTTS-v2** (voz natural, pt/en/es). Sem ele, o backend usa
**gTTS** (mais robótico, mas funciona sem deploy).

**Forma A — Deploy pelo GitHub (sem Docker local):**
1. **Serverless → New Endpoint → Import Git Repository** (repo `originslone-sys/emme-tech`).
2. **Dockerfile Path:** `runpod-workers/viral-tts/Dockerfile`
3. **Build Context:** deixe **em branco** (a raiz do repositório). Os `COPY` do
   Dockerfile já apontam o caminho completo a partir da raiz.
4. GPU ~8–12 GB, disco ~15 GB (o modelo XTTS-v2 é embutido na imagem) → Deploy.
5. Copie o **Endpoint ID** → backend: `RUNPOD_TTS_ENDPOINT`.

**Forma B — Build manual:**
```bash
cd runpod-workers/viral-tts
docker build -t SEU_USUARIO/emme-viral-tts:latest .
docker push SEU_USUARIO/emme-viral-tts:latest
```

Detalhes e contrato: `runpod-workers/viral-tts/README.md`.

> Alternativa pronta no Hub: o **Chatterbox TTS** (que apareceu na sua busca)
> é um TTS com clonagem de voz. Dá pra usar no lugar do nosso worker, mas o
> contrato de input/output é diferente — eu precisaria adaptar o `services/tts.py`
> do backend pra ele. Me avise se preferir esse caminho.

---

## Variáveis no backend (resumo)

```env
RUNPOD_API_KEY=...                 # obrigatório p/ qualquer endpoint
BACKEND_URL=https://seu-backend    # URL pública (workers baixam arquivos daqui)

RUNPOD_WHISPER_ENDPOINT=...        # Cortes Virais
RUNPOD_ENHANCE_ENDPOINT=...        # opcional (upscaling)
RUNPOD_RENDER_ENDPOINT=...         # opcional (render viral na GPU)
RUNPOD_TTS_ENDPOINT=...            # opcional (narração na GPU)

DEEPSEEK_API_KEY=...               # roteiro / seleção de cortes
PEXELS_API_KEY=...                 # cenas do gerador viral
```

## Caminho mínimo por função

- **Só quero Gerar Vídeo Viral, sem deploy de GPU:** configure só
  `DEEPSEEK_API_KEY` + `PEXELS_API_KEY`. Render local + gTTS já funcionam.
- **Gerar Vídeo Viral rápido e com voz natural:** + `RUNPOD_RENDER_ENDPOINT`
  (passo 3) e `RUNPOD_TTS_ENDPOINT` (passo 4).
- **Cortes Virais:** + `RUNPOD_WHISPER_ENDPOINT` (passo 1).
- **Upscaling em Editar Vídeo:** + `RUNPOD_ENHANCE_ENDPOINT` (passo 2).
