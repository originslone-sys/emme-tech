import logging
import os

import httpx

log = logging.getLogger("zernio")

ZERNIO_API_KEY = os.getenv("ZERNIO_API_KEY", "")
_BASE = "https://zernio.com/api/v1"


async def publish_tiktok(
    video_url: str, caption: str, hashtags: list[str], account_id: str
) -> dict:
    if not ZERNIO_API_KEY:
        raise RuntimeError("ZERNIO_API_KEY não configurada")
    if not account_id:
        raise RuntimeError("TikTok account_id não configurado")

    tags_str = " ".join(f"#{t.lstrip('#')}" for t in hashtags[:10] if t.strip())
    full_caption = f"{caption}\n\n{tags_str}".strip() if tags_str else caption

    payload = {
        "platform": "tiktok",
        "accountId": account_id,
        "videoUrl": video_url,
        "caption": full_caption,
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{_BASE}/posts",
            json=payload,
            headers={
                "Authorization": f"Bearer {ZERNIO_API_KEY}",
                "Content-Type": "application/json",
            },
        )
        if not resp.is_success:
            raise RuntimeError(f"Zernio {resp.status_code}: {resp.text[:300]}")
        return resp.json()
