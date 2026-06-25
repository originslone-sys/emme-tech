import asyncio
import httpx
import os
import uuid
from pathlib import Path

from services import storage

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
_BASE_URL = "https://openrouter.ai/api/v1"

# FLUX.2 [flex] — suporta até 10 imagens de referência para consistência de personagem.
_IMAGE_MODEL = "black-forest-labs/flux-2-flex"

_HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": os.getenv("BACKEND_URL", "https://emme.app"),
    "X-Title": "Emme AI",
}


async def _generate_one(prompt: str, reference_url: str | None,
                        width: int, height: int) -> str | None:
    """Gera uma única imagem e retorna a URL pública retornada pela API."""
    body: dict = {
        "model": _IMAGE_MODEL,
        "prompt": prompt,
        "width": width,
        "height": height,
        "num_inference_steps": 28,
        "guidance_scale": 3.5,
    }
    if reference_url:
        # FLUX.2 flex aceita imagens de referência via image_references.
        body["image_references"] = [{"url": reference_url, "weight": 0.85}]

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{_BASE_URL}/images/generations",
            json=body,
            headers=_HEADERS,
        )
        resp.raise_for_status()
        data = resp.json()

    # OpenRouter retorna data[].url
    images = data.get("data", [])
    if not images:
        return None
    return images[0].get("url")


async def _download_image(url: str) -> str:
    """Baixa uma imagem e salva no storage de imagens. Retorna o caminho local."""
    img_id = str(uuid.uuid4())
    path = storage.DIRS["images"] / f"{img_id}.png"
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        path.write_bytes(resp.content)
    return str(path)


async def generate_images(
    prompt: str,
    count: int = 6,
    reference_url: str | None = None,
    width: int = 1024,
    height: int = 1024,
) -> list[dict]:
    """Gera `count` imagens em paralelo e retorna lista de {id, path, filename}.

    Se reference_url for passada, o FLUX.2 flex usa ela como referência de
    identidade (preserva o rosto do personagem na nova cena).
    """
    tasks = [
        _generate_one(prompt, reference_url, width, height)
        for _ in range(count)
    ]
    urls = await asyncio.gather(*tasks, return_exceptions=True)

    results = []
    for url in urls:
        if isinstance(url, Exception) or not url:
            continue
        try:
            path = await _download_image(url)
            img_id = Path(path).stem
            results.append({
                "id": img_id,
                "path": path,
                "filename": Path(path).name,
            })
        except Exception:
            continue

    return results
