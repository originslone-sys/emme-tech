import logging
import os

import httpx

log = logging.getLogger("zernio")

ZERNIO_API_KEY = os.getenv("ZERNIO_API_KEY", "")
_BASE = "https://zernio.com/api/v1"


async def get_creator_info(account_id: str) -> dict:
    """Busca privacy_levels permitidos e limites de postagem do criador TikTok."""
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(
            f"{_BASE}/accounts/{account_id}/tiktok/creator-info",
            params={"mediaType": "video"},
            headers={"Authorization": f"Bearer {ZERNIO_API_KEY}"},
        )
        if not resp.is_success:
            raise RuntimeError(f"creator-info {resp.status_code}: {resp.text[:200]}")
        return resp.json()


async def publish_tiktok(
    video_url: str, caption: str, hashtags: list[str], account_id: str,
    privacy_level: str = "PUBLIC_TO_EVERYONE",
) -> dict:
    """Publica um vídeo no TikTok via Zernio API."""
    if not ZERNIO_API_KEY:
        raise RuntimeError("ZERNIO_API_KEY não configurada")
    if not account_id:
        raise RuntimeError("TikTok account_id não configurado")

    tags_str = " ".join(f"#{t.lstrip('#')}" for t in hashtags[:10] if t.strip())
    full_caption = f"{caption}\n\n{tags_str}".strip() if tags_str else caption
    # TikTok limita legenda de vídeo a 2200 chars
    full_caption = full_caption[:2200]

    payload = {
        "content": full_caption,
        "mediaItems": [
            {"type": "video", "url": video_url}
        ],
        "platforms": [
            {"platform": "tiktok", "accountId": account_id}
        ],
        "tiktokSettings": {
            "privacy_level": privacy_level,
            "allow_comment": True,
            "allow_duet": True,
            "allow_stitch": True,
            "content_preview_confirmed": True,   # obrigatório pelo TikTok
            "express_consent_given": True,        # obrigatório pelo TikTok
            "video_made_with_ai": True,           # disclosure: conteúdo gerado por IA
            "video_cover_timestamp_ms": 1000,
        },
        "publishNow": True,
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
