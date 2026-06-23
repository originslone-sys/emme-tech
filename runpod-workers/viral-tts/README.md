# Worker de Narração / TTS (RunPod Serverless)

Gera a narração de cada cena do vídeo viral usando **Coqui XTTS-v2** (voz
multilíngue e natural) na GPU. O backend usa este worker quando
`RUNPOD_TTS_ENDPOINT` está configurado; caso contrário, faz o fallback local
com **gTTS** (mais simples/robótico, mas funciona sem deploy).

## Build e deploy

```bash
cd runpod-workers/viral-tts

docker build -t SEU_USUARIO/emme-viral-tts:latest .
docker push SEU_USUARIO/emme-viral-tts:latest
```

No painel do RunPod:

1. **Serverless → New Endpoint**
2. Container Image: `SEU_USUARIO/emme-viral-tts:latest`
3. GPU: qualquer uma com ~8–12 GB (ex: RTX A4000/4090)
4. Container Disk: ~15 GB (o modelo XTTS-v2 é embutido na imagem)
5. Copie o **Endpoint ID** → backend como `RUNPOD_TTS_ENDPOINT`

> A imagem já baixa o modelo no build (`COQUI_TOS_AGREED=1` aceita a licença
> do XTTS-v2 para uso). O primeiro request ainda carrega o modelo na GPU.

## Contrato

**Input**

```json
{
  "input": {
    "texts": ["frase da cena 1", "frase da cena 2"],
    "language": "pt",
    "voice": "feminina"
  }
}
```

- `language`: `pt`, `en` ou `es`.
- `voice`: `feminina` (Ana Florence) ou `masculina` (Damien Black).

**Output**

```json
{ "clips": [{"audio_base64": "<wav>", "duration": 3.42}, ...] }
```

Cada item alinhado à cena correspondente. `audio_base64` vazio = cena sem
narração (vira silêncio na montagem).
