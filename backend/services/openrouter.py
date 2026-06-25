import asyncio
import base64
import httpx
import logging
import os
import uuid
from pathlib import Path

from services import storage

logger = logging.getLogger(__name__)

_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
_IMAGES_URL = "https://openrouter.ai/api/v1/images/generations"

# Modelo padrão — pode ser sobrescrito com OPENROUTER_IMAGE_MODEL no Railway.
# Opções testadas: black-forest-labs/flux-1.1-pro, black-forest-labs/flux-pro,
#                  black-forest-labs/flux-1-schnell, black-forest-labs/flux.2-flex
_IMAGE_MODEL = os.getenv("OPENROUTER_IMAGE_MODEL", "black-forest-labs/flux-1.1-pro")


def _headers() -> dict:
    """Constrói headers com a API key lida em tempo de execução."""
    key = os.getenv("OPENROUTER_API_KEY", "")
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "HTTP-Referer": os.getenv("BACKEND_URL", "https://emme.app"),
        "X-Title": "Emme AI",
    }


def _build_messages(prompt: str, reference_url: str | None) -> list[dict]:
    if reference_url:
        content = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": reference_url}},
        ]
    else:
        content = [{"type": "text", "text": prompt}]
    return [{"role": "user", "content": content}]


async def _generate_via_chat(
    prompt: str,
    reference_url: str | None,
    aspect_ratio: str,
    image_size: str,
    seed: int | None,
    client: httpx.AsyncClient,
) -> bytes | None:
    """Tenta gerar imagem via /chat/completions com modalities."""
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

    resp = await client.post(_CHAT_URL, json=body, headers=_headers())
    if not resp.is_success:
        logger.warning("chat/completions falhou %d: %s", resp.status_code, resp.text[:300])
        return None

    data = resp.json()
    try:
        img_url = data["choices"][0]["message"]["images"][0]["image_url"]["url"]
        if img_url.startswith("data:"):
            return base64.b64decode(img_url.split(",", 1)[1])
        async with httpx.AsyncClient(timeout=60) as dl:
            r = await dl.get(img_url)
            r.raise_for_status()
            return r.content
    except (KeyError, IndexError, Exception) as e:
        logger.warning("Extração de imagem (chat) falhou: %s | resp: %s", e, str(data)[:300])
        return None


async def _generate_via_images(
    prompt: str,
    aspect_ratio: str,
    image_size: str,
    seed: int | None,
    client: httpx.AsyncClient,
) -> bytes | None:
    """Tenta gerar imagem via /images/generations (endpoint OpenAI-style)."""
    body: dict = {
        "model": _IMAGE_MODEL,
        "prompt": prompt,
        "n": 1,
        "response_format": "b64_json",
        "image_config": {
            "aspect_ratio": aspect_ratio,
            "image_size": image_size,
        },
    }
    if seed is not None:
        body["seed"] = seed

    resp = await client.post(_IMAGES_URL, json=body, headers=_headers())
    if not resp.is_success:
        logger.error("images/generations falhou %d: %s", resp.status_code, resp.text[:300])
        return None

    data = resp.json()
    try:
        item = data["data"][0]
        if "b64_json" in item and item["b64_json"]:
            return base64.b64decode(item["b64_json"])
        if "url" in item:
            async with httpx.AsyncClient(timeout=60) as dl:
                r = await dl.get(item["url"])
                r.raise_for_status()
                return r.content
    except (KeyError, IndexError, Exception) as e:
        logger.error("Extração de imagem (images) falhou: %s | resp: %s", e, str(data)[:300])
    return None


async def _generate_one(
    prompt: str,
    reference_url: str | None,
    aspect_ratio: str,
    image_size: str,
    seed: int | None = None,
) -> bytes | None:
    """Gera uma única imagem: tenta chat/completions, depois images/generations."""
    async with httpx.AsyncClient(timeout=120) as client:
        # Primeira tentativa: chat/completions com modalities
        result = await _generate_via_chat(
            prompt, reference_url, aspect_ratio, image_size, seed, client
        )
        if result:
            return result

        # Fallback: images/generations (OpenAI-style, sem referência visual)
        logger.info("Tentando fallback images/generations para seed=%s", seed)
        result = await _generate_via_images(
            prompt, aspect_ratio, image_size, seed, client
        )
        return result


async def generate_images(
    prompt: str,
    count: int = 6,
    reference_url: str | None = None,
    aspect_ratio: str = "1:1",
    image_size: str = "1K",
) -> list[dict]:
    """Gera `count` imagens em paralelo. Retorna lista de {id, path, filename}."""
    seeds = [i * 137 + 42 for i in range(count)]

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
