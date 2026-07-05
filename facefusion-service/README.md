# FaceFusion — Serviço de Face Swap de Imagem (Railway, CPU)

Serviço HTTP self-contained que troca um rosto em uma imagem usando o
[FaceFusion](https://github.com/facefusion/facefusion) (motor `inswapper` +
enhancer `gfpgan`). Roda **100% no Railway, sem GPU** — pensado para **imagem**
(segundos por foto). Para **vídeo**, use o worker serverless de GPU (RunPod);
este serviço é só para imagem.

> **Licença / uso responsável:** o FaceFusion usa a licença OpenRAIL-AS, que
> **proíbe uso não-consensual**. Use apenas com rostos que você tem direito de
> usar (o seu próprio, por exemplo).

## Como fazer o deploy no Railway

1. **Novo serviço** no seu projeto Railway → *Deploy from repo* → aponte para
   este repositório.
2. Em **Settings → Build**, defina o **Root Directory** como `facefusion-service`
   e o **Builder** como **Dockerfile**.
3. Em **Variables**, defina:
   - `SWAP_API_KEY` — uma senha qualquer; será exigida no header `X-API-Key`.
   - *(opcional)* `SWAP_TIMEOUT` — segundos por swap (padrão `300`).
   - *(opcional)* `FF_SWAPPER_MODEL` (padrão `inswapper_128_fp16`),
     `FF_ENHANCER_MODEL` (padrão `gfpgan_1.4`).
4. Deploy. O **primeiro build é lento** (instala o FaceFusion e baixa todos os
   modelos). Depois disso, nada é baixado em runtime.

### Rede privada (recomendado)

O app principal chama este serviço pela rede interna do Railway
(`http://<nome-do-servico>.railway.internal:8000`), sem expor à internet.

## Endpoints

### `GET /health`
Retorna `{"status": "ok"}`.

### `POST /swap-image`
Multipart form-data:
- `source` — imagem do **rosto** a inserir (sua foto).
- `target` — **imagem-alvo** (já pronta) onde o rosto será colado.

Header: `X-API-Key: <SWAP_API_KEY>`

Resposta: `image/jpeg` com o rosto trocado.

Exemplo:

```bash
curl -X POST http://localhost:8000/swap-image \
  -H "X-API-Key: SUA_CHAVE" \
  -F "source=@meu_rosto.jpg" \
  -F "target=@imagem_alvo.jpg" \
  --output resultado.jpg
```

## Notas de operação

- **Tamanho da imagem Docker:** o `force-download` baixa **todos** os modelos do
  FaceFusion, o que deixa a imagem grande (vários GB). Se estourar o limite do
  Railway, troque o passo `force-download` no `Dockerfile` por um *headless-run*
  de aquecimento só com os modelos usados (swapper + enhancer).
- **Versão do FaceFusion:** o `Dockerfile` usa `ARG FACEFUSION_VERSION=master`.
  Para builds reproduzíveis, fixe uma tag (ex: `3.4.1`) — a CLI muda entre
  versões maiores. Se o build/CLI falhar, verifique os flags de
  `headless-run` da versão fixada.
- **Performance:** CPU do Railway → segundos por imagem. Nada de vídeo aqui.
