import asyncio
import base64
import httpx
import logging
import os
import uuid
from pathlib import Path

from services import storage

logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

# FLUX.2 [flex] — melhor da família FLUX para consistência com referência.
# Nota: OpenRouter usa ponto no nome (flux.2-flex, não flux-2-flex).
_IMAGE_MODEL = "black-forest-labs/flux.2-flex"

_HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": os.getenv("BACKEND_URL", "https://emme.app"),
    "X-Title": "Emme AI",
}


def _build_messages(prompt: str, reference_url: str | None) -> list[dict]:
    """Monta o array de messages para o chat/completions de geração de imagem.

    Se houver uma imagem de referência, inclui ela como input visual para
    que o FLUX mantenha a identidade do personagem.
    """
    if reference_url:
        content = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": reference_url}},
        ]
    else:
        content = [{"type": "text", "text": prompt}]
    return [{"role": "user", "content": content}]


async def _generate_one(
    prompt: str,
    reference_url: str | None,
    aspect_ratio: str,
    image_size: str,
    seed: int | None = None,
) -> bytes | None:
    """Gera uma única imagem e retorna os bytes PNG."""
    body: dict = {
        "model": _IMAGE_MODEL,
        "messages": _build_messages(prompt, reference_url),
        "modalities": ["image", "text"],
        "image_config": {
            "aspect_ratio": aspect_ratio,
            "image_size": image_size,
        },
    }
    if seed is not None:
        body["seed"] = seed

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(_BASE_URL, json=body, headers=_HEADERS)
        if not resp.is_success:
            logger.error("OpenRouter error %d: %s", resp.status_code, resp.text[:500])
            return None
        data = resp.json()

    try:
        img_url = data["choices"][0]["message"]["images"][0]["image_url"]["url"]
        # A API retorna base64 data URL: "data:image/png;base64,<dados>"
        if img_url.startswith("data:"):
            b64 = img_url.split(",", 1)[1]
            return base64.b64decode(b64)
        # Ou URL direta — baixa
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.get(img_url)
            r.raise_for_status()
            return r.content
    except (KeyError, IndexError, Exception) as e:
        logger.error("Falha ao extrair imagem da resposta: %s | resp: %s", e, str(data)[:300])
        return None


async def generate_images(
    prompt: str,
    count: int = 6,
    reference_url: str | None = None,
    aspect_ratio: str = "1:1",
    image_size: str = "1K",
) -> list[dict]:
    """Gera `count` imagens em paralelo. Retorna lista de {id, path, filename}.

    Cada geração usa uma seed diferente para variar a composição mantendo
    o prompt-âncora (e referência visual, se fornecida) para consistência.
    """
    seeds = [i * 137 + 42 for i in range(count)]  # seeds distribuídas, determinísticas

    tasks = [
        _generate_one(prompt, reference_url, aspect_ratio, image_size, seed=s)
        for s in seeds
    ]
    raw_images = await asyncio.gather(*tasks, return_exceptions=True)

    results = []
    for raw in raw_images:
        if isinstance(raw, Exception) or not raw:
            continue
        img_id = str(uuid.uuid4())
        path = storage.DIRS["images"] / f"{img_id}.png"
        path.write_bytes(raw)
        results.append({
            "id": img_id,
            "path": str(path),
            "filename": f"{img_id}.png",
        })

    logger.info("Geradas %d/%d imagens com sucesso", len(results), count)
    return results
