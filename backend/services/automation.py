import asyncio
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path

import httpx

from services import deepseek, ffmpeg, openrouter, pexels, pixabay, storage, tts, zernio

log = logging.getLogger("automation")

_DIMENSIONS = {"9:16": (1080, 1920)}

# Controlador de execução única (evita sobreposição de ciclos)
_is_running = False


def is_running() -> bool:
    return _is_running


async def _download_any(url: str, dest: str):
    async with httpx.AsyncClient(follow_redirects=True, timeout=120) as c:
        async with c.stream("GET", url) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                async for chunk in r.aiter_bytes(1 << 16):
                    f.write(chunk)


async def _find_clip(
    query: str, fmt: str, width: int, height: int,
    used_pexels: set, used_pixabay: set,
) -> str | None:
    """Tenta Pexels → Pixabay → Kling AI como fallback."""
    try:
        url = await pexels.find_clip_url(query, fmt, width, height, used_pexels)
        if url:
            return url
    except Exception as e:
        log.debug("Pexels falhou para '%s': %s", query, e)

    try:
        url = await pixabay.find_clip_url(query, fmt, used_pixabay)
        if url:
            return url
    except Exception as e:
        log.debug("Pixabay falhou para '%s': %s", query, e)

    try:
        url = await openrouter.generate_video_clip(
            prompt=f"cinematic {query}, vertical 9:16, TikTok style",
            duration=5,
            aspect_ratio="9:16",
        )
        return url
    except Exception as e:
        log.warning("AI video falhou para '%s': %s", query, e)
    return None


async def run_once(config: dict) -> dict:
    """Executa um ciclo completo: roteiro → mídia → TTS → render → publicar."""
    global _is_running
    if _is_running:
        log.info("Ciclo ignorado: já em execução")
        return {"skipped": True, "reason": "já em execução"}

    _is_running = True
    entry: dict = {
        "id": str(uuid.uuid4()),
        "started_at": datetime.now().isoformat(),
        "status": "running",
    }
    try:
        width, height = _DIMENSIONS["9:16"]
        fmt = "9:16"

        # 1. Roteiro
        log.info("Gerando roteiro de curiosidade...")
        used_keys = storage.get_used_fact_keys()
        script = await deepseek.generate_curiosity_script(used_keys)
        storage.add_used_fact_key(script["fact_key"])
        scenes = script["scenes"]
        log.info("Roteiro: '%s' (%d cenas)", script["title"], len(scenes))

        # 2. Narração TTS
        narr: list[dict | None] | None = None
        try:
            narr = await tts.synthesize_scenes(
                [sc["narration"] for sc in scenes],
                language="Português",
                voice=config.get("voice", "feminina"),
            )
            if narr and any(narr):
                for sc, n in zip(scenes, narr):
                    if n and n.get("duration", 0) > 0:
                        sc["duration"] = round(min(5.0, max(2.0, n["duration"] + 0.35)), 2)
            else:
                narr = None
        except Exception as e:
            log.warning("TTS falhou, sem narração: %s", e)
            narr = None

        # 3. Clipes por cena
        log.info("Buscando clipes para %d cenas...", len(scenes))
        used_pexels: set = set()
        used_pixabay: set = set()
        scene_urls: list[str | None] = []
        for sc in scenes:
            url = await _find_clip(sc["visual_query"], fmt, width, height, used_pexels, used_pixabay)
            scene_urls.append(url)
        found = sum(1 for u in scene_urls if u)
        log.info("Clipes encontrados: %d/%d", found, len(scenes))

        output_id = str(uuid.uuid4())
        output_path = str(storage.DIRS["videos"] / f"{output_id}.mp4")

        # 4. Download local
        local_paths: list[str | None] = []
        for i, url in enumerate(scene_urls):
            if not url:
                local_paths.append(None)
                continue
            clip_path = str(storage.DIRS["uploads"] / f"auto_{output_id}_s{i}.mp4")
            try:
                if "pexels.com" in url:
                    await pexels.download(url, clip_path)
                elif "pixabay.com" in url:
                    await pixabay.download(url, clip_path)
                else:
                    await _download_any(url, clip_path)
                local_paths.append(clip_path)
            except Exception as e:
                log.warning("Download falhou cena %d: %s", i, e)
                local_paths.append(None)

        # 5. Render FFmpeg
        log.info("Renderizando vídeo...")
        narr_paths = [n["path"] if n else None for n in narr] if narr else None

        await asyncio.to_thread(
            ffmpeg.render_viral,
            local_paths, scenes, width, height,
            None,       # sem trilha sonora dedicada
            output_path,
            None,       # sem callback de progresso
            narr_paths,
            None,       # sem channel_name watermark
        )

        # Limpeza de temporários
        for p in local_paths:
            if p:
                Path(p).unlink(missing_ok=True)

        # 6. Salva na biblioteca
        storage.add_video(output_id, output_path, script["title"], meta={
            "kind": "tiktok_auto",
            "title": script["title"],
            "description": script["description"],
            "tags": script["tags"],
            "fact_key": script["fact_key"],
            "subtheme": script.get("subtheme", ""),
        })
        log.info("Vídeo salvo: %s", output_id)

        # 7. Publicar no TikTok
        published = None
        if config.get("auto_publish") and config.get("tiktok_account_id"):
            try:
                backend_url = os.getenv("BACKEND_URL", "").rstrip("/")
                filename = Path(output_path).name
                video_public_url = f"{backend_url}/files/videos/{filename}"
                published = await zernio.publish_tiktok(
                    video_url=video_public_url,
                    caption=script["description"],
                    hashtags=script["tags"],
                    account_id=config["tiktok_account_id"],
                )
                log.info("Publicado no TikTok: %s", published)
            except Exception as e:
                log.warning("Publicação TikTok falhou: %s", e)
                published = {"error": str(e)}

        entry.update({
            "status": "completed",
            "title": script["title"],
            "fact_key": script["fact_key"],
            "subtheme": script.get("subtheme", ""),
            "video_id": output_id,
            "published": published,
            "finished_at": datetime.now().isoformat(),
        })

    except Exception as e:
        log.exception("Ciclo de automação falhou")
        entry.update({
            "status": "failed",
            "error": str(e),
            "finished_at": datetime.now().isoformat(),
        })
    finally:
        _is_running = False
        storage.add_automation_history(entry)

    return entry
