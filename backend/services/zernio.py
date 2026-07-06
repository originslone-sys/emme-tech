"""Integração com o Zernio para publicação no Instagram.

Publica feed (foto/carrossel), Reels e Stories via POST /api/v1/posts.
Comentários e DMs (auto-resposta) serão adicionados na Fase 2, quando tivermos
a referência exata da Messages/Comments API.
"""
import logging
import os

import httpx

log = logging.getLogger("zernio")

ZERNIO_API_KEY = os.getenv("ZERNIO_API_KEY", "")
_BASE = "https://zernio.com/api/v1"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {ZERNIO_API_KEY}",
        "Content-Type": "application/json",
    }


async def publish_instagram(
    media_items: list[dict],
    caption: str,
    account_id: str,
    content_type: str | None = None,   # None=feed, "story", "reels"
    is_ai_generated: bool = False,
    first_comment: str | None = None,
) -> dict:
    """Publica no Instagram via Zernio.

    media_items: [{"type": "image"|"video", "url": "https://..."}] (URLs públicas).
    content_type: None (feed/carrossel), "story" ou "reels".
    """
    if not ZERNIO_API_KEY:
        raise RuntimeError("ZERNIO_API_KEY não configurada")
    if not account_id:
        raise RuntimeError("Instagram account_id não configurado")
    if not media_items:
        raise RuntimeError("Nenhuma mídia para publicar")

    psd: dict = {}
    if content_type:
        psd["contentType"] = content_type
    if content_type == "reels":
        psd["shareToFeed"] = True
    if is_ai_generated:
        psd["isAiGenerated"] = True
    if first_comment:
        psd["firstComment"] = first_comment

    platform: dict = {"platform": "instagram", "accountId": account_id}
    if psd:
        platform["platformSpecificData"] = psd

    body: dict = {
        "mediaItems": media_items,
        "platforms": [platform],
        "publishNow": True,
    }
    # Stories não exibem legenda; nos demais, envia o caption.
    if caption and content_type != "story":
        body["content"] = caption[:2200]

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(f"{_BASE}/posts", json=body, headers=_headers())
        if not resp.is_success:
            raise RuntimeError(f"Zernio {resp.status_code}: {resp.text[:400]}")
        return resp.json()
