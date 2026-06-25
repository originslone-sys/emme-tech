import asyncio
import base64
import httpx
import logging
import os
import uuid
from pathlib import Path

from services import storage

logger = logging.getLogger(__name__)

# Endpoint dedicado de imagens (FLUX e similares)
_IMAGES_URL = "https://openrouter.ai/api/v1/images"
# Endpoint chat/completions (Gemini image models)
_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"

# Configurável via OPENROUTER_IMAGE_MODEL no Railway.
# FLUX.2 Pro: black-forest-labs/flux.2-pro  ($0.03/mp, consistência multi-referência)
# FLUX.2 Flex: black-forest-labs/flux.2-flex ($0.06/mp, multi-reference editing)
# Gemini fallback: google/gemini-3-pro-image
_IMAGE_MODEL = os.getenv("OPENROUTER_IMAGE_MODEL", "black-forest-labs/flux.2-pro")


def _headers() -> dict:
    key = os.getenv("OPENROUTER_API_KEY", "")
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "HTTP-Referer": os.getenv("BACKEND_URL", "https://emme.app"),
        "X-Title": "Emme AI",
    }


def _is_flux(model: str) -> bool:
    return "flux" in model.lower()


_NEGATIVE_PROMPT = (
    "plastic skin, smooth skin, airbrushed, instagram filter, beauty mode, porcelain skin, "
    "anime, illustration, cartoon, 3D render, CGI, painting, hyper-smooth, overexposed, "
    "glowing skin, perfectly symmetrical face, beauty retouch, studio makeup, fake"
)


async def _generate_flux(
    prompt: str,
    reference_url: str | None,
    seed: int | None,
    client: httpx.AsyncClient,
) -> bytes | None:
    """Gera imagem via /api/v1/images (endpoint dedicado FLUX)."""
    body: dict = {
        "model": _IMAGE_MODEL,
        "prompt": prompt,
        "negative_prompt": _NEGATIVE_PROMPT,
        "n": 1,
        "output_format": "png",
        "guidance": 4.0,
        "steps": 35,
    }
    if seed is not None:
        body["seed"] = seed
    if reference_url:
        body["input_references"] = [reference_url]

    resp = await client.post(_IMAGES_URL, json=body, headers=_headers())
    if not resp.is_success:
        logger.error("FLUX /images falhou %d: %s", resp.status_code, resp.text[:400])
        return None

    data = resp.json()
    try:
        item = data["data"][0]
        if item.get("b64_json"):
            return base64.b64decode(item["b64_json"])
        if item.get("url"):
            async with httpx.AsyncClient(timeout=60) as dl:
                r = await dl.get(item["url"])
                r.raise_for_status()
                return r.content
    except (KeyError, IndexError, Exception) as e:
        logger.error("Extração FLUX falhou: %s | resp: %s", e, str(data)[:300])
    return None


async def _generate_gemini(
    prompt: str,
    reference_url: str | None,
    aspect_ratio: str,
    image_size: str,
    seed: int | None,
    client: httpx.AsyncClient,
) -> bytes | None:
    """Gera imagem via /api/v1/chat/completions com modalities (Gemini)."""
    if reference_url:
        content = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": reference_url}},
        ]
    else:
        content = [{"type": "text", "text": prompt}]

    body: dict = {
        "model": _IMAGE_MODEL,
        "messages": [{"role": "user", "content": content}],
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
        logger.error("Gemini chat/completions falhou %d: %s", resp.status_code, resp.text[:400])
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
        logger.error("Extração Gemini falhou: %s | resp: %s", e, str(data)[:300])
    return None


async def _generate_one(
    prompt: str,
    reference_url: str | None,
    aspect_ratio: str,
    image_size: str,
    seed: int | None = None,
) -> bytes | None:
    async with httpx.AsyncClient(timeout=120) as client:
        if _is_flux(_IMAGE_MODEL):
            return await _generate_flux(prompt, reference_url, seed, client)
        else:
            return await _generate_gemini(
                prompt, reference_url, aspect_ratio, image_size, seed, client
            )


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
