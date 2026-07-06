"""Orquestrador da automação Instagram.

Um "slot" de publicação (feed ou story): escolhe o tipo pela disponibilidade do
cofre (com fallback), gera a legenda na voz da persona, publica via Zernio e
consome a mídia do cofre. Registra tudo no histórico.
"""
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path

from services import deepseek, storage, vault, zernio

log = logging.getLogger("instagram")

_VIDEO_EXTS = {".mp4", ".mov"}

# Controla execução única por vez (evita sobreposição de slots).
_running = False


def is_running() -> bool:
    return _running


def _media_items(item: dict, backend_url: str) -> list[dict]:
    out = []
    for f in item.get("files", []):
        ext = Path(f).suffix.lower()
        mtype = "video" if ext in _VIDEO_EXTS else "image"
        out.append({"type": mtype, "url": f"{backend_url}/files/vault/{f}"})
    return out


async def run_slot(kind: str, config: dict) -> dict:
    """Executa um slot de publicação. kind: 'feed' ou 'story'."""
    global _running
    entry: dict = {
        "id": str(uuid.uuid4()),
        "slot": kind,
        "at": datetime.now().isoformat(),
    }
    if _running:
        entry.update({"status": "skipped", "reason": "outro slot em execução"})
        storage.add_ig_history(entry)
        return entry

    _running = True
    try:
        account_id = config.get("account_id", "")
        persona = config.get("persona", {})
        is_ai = bool(config.get("is_ai_generated"))
        backend_url = os.getenv("BACKEND_URL", "").rstrip("/")
        if not backend_url:
            raise RuntimeError(
                "BACKEND_URL não configurada — necessária para gerar URLs públicas "
                "das mídias que o Instagram vai baixar."
            )

        # Escolha do item com fallback.
        if kind == "story":
            item = vault.pick_item(["photo", "video", "carousel"])
        else:
            item = vault.pick_item(["video", "carousel", "photo"])

        if not item:
            entry.update({"status": "skipped", "reason": "cofre vazio"})
            storage.add_ig_history(entry)
            return entry

        media = _media_items(item, backend_url)
        if not media:
            entry.update({"status": "skipped", "reason": "item sem arquivos válidos"})
            storage.add_ig_history(entry)
            return entry

        # Tipo de conteúdo e legenda.
        caption = ""
        if kind == "story":
            content_type = "story"
            media = media[:1]  # story = 1 mídia
        else:
            # Feed: sem contentType. O Zernio auto-detecta Reel se o vídeo for
            # 9:16 e < 90s; senão publica como vídeo/foto/carrossel de feed.
            content_type = None
            caption_kind = "video" if item["kind"] == "video" else item["kind"]
            cap = await deepseek.generate_persona_caption(persona, caption_kind)
            tags = " ".join(f"#{t}" for t in cap.get("hashtags", []))
            caption = f"{cap.get('caption', '')}\n\n{tags}".strip()

        result = await zernio.publish_instagram(
            media_items=media,
            caption=caption,
            account_id=account_id,
            content_type=content_type,
            is_ai_generated=is_ai,
        )

        vault.consume(item["id"])
        post = result.get("post") or result
        entry.update({
            "status": "completed",
            "kind": "story" if content_type == "story" else item["kind"],
            "item_id": item["id"],
            "caption": caption,
            "post_id": str(post.get("_id", "")) if isinstance(post, dict) else "",
        })

    except Exception as e:
        log.exception("Slot de publicação falhou")
        entry.update({"status": "failed", "error": str(e)})
    finally:
        _running = False
        storage.add_ig_history(entry)

    return entry
