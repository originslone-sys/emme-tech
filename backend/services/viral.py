import asyncio
import uuid
from pathlib import Path

from services import storage, deepseek, pexels, music, ffmpeg, runpod

DIMENSIONS = {
    "9:16": (1080, 1920),
    "1:1": (1080, 1080),
    "16:9": (1920, 1080),
}

_RENDER_TIMEOUT = 60 * 20  # 20 min
_POLL_INTERVAL = 5


async def _render_on_runpod(job_id: str, scene_urls: list[str | None],
                            scenes: list[dict], width: int, height: int,
                            music_url: str, output_id: str, output_path: str):
    payload_scenes = [
        {"video_url": url or "", "duration": sc["duration"], "text": sc["text"]}
        for url, sc in zip(scene_urls, scenes)
    ]
    rp_job = await runpod.submit_render_job(payload_scenes, width, height, music_url)

    waited = 0
    while waited < _RENDER_TIMEOUT:
        data = await runpod.get_job_status(rp_job, runpod.RENDER_ENDPOINT)
        status = data.get("status")
        if status == "COMPLETED":
            if not await runpod.save_output(data, output_path):
                raise RuntimeError("O worker de render não retornou o vídeo")
            return
        if status in ("FAILED", "CANCELLED", "TIMED_OUT"):
            raise RuntimeError(data.get("error") or "Render na GPU falhou")
        await asyncio.sleep(_POLL_INTERVAL)
        waited += _POLL_INTERVAL
    raise RuntimeError("Tempo esgotado no render da GPU")


async def run_pipeline(job_id: str, topic: str, fmt: str, duration: int,
                       language: str, music_path: str | None = None):
    try:
        width, height = DIMENSIONS.get(fmt, DIMENSIONS["9:16"])

        # 1. Roteiro viral com a IA
        storage.update_job(job_id, {"stage": "scripting"})
        script = await deepseek.generate_viral_script(topic, duration, language, fmt)
        scenes = script["scenes"]

        # 2. Encontra um clipe do Pexels para cada cena
        storage.update_job(job_id, {"stage": "fetching", "total": len(scenes), "done": 0})
        used_ids: set = set()
        scene_urls: list[str | None] = []
        for i, sc in enumerate(scenes):
            try:
                url = await pexels.find_clip_url(sc["visual_query"], fmt, width, height, used_ids)
            except Exception:
                url = None
            scene_urls.append(url)
            storage.update_job(job_id, {"done": i + 1})

        output_id = str(uuid.uuid4())
        output_path = str(storage.DIRS["videos"] / f"{output_id}.mp4")

        # 3. Render — GPU no RunPod se configurado, senão local
        storage.update_job(job_id, {"stage": "rendering", "percent": 0})

        if runpod.RENDER_ENDPOINT:
            # O worker baixa direto do Pexels; música precisa ser URL pública
            music_url = ""
            if music_path:
                music_url = runpod.file_to_url(music_path)
            await _render_on_runpod(job_id, scene_urls, scenes, width, height,
                                    music_url, output_id, output_path)
        else:
            # Fallback local: baixa os clipes e monta na CPU
            local_paths: list[str | None] = []
            for i, url in enumerate(scene_urls):
                if not url:
                    local_paths.append(None)
                    continue
                clip_path = str(storage.DIRS["uploads"] / f"{output_id}_s{i}.mp4")
                try:
                    await pexels.download(url, clip_path)
                    local_paths.append(clip_path)
                except Exception:
                    local_paths.append(None)

            track = music_path or music.pick(script["music_mood"])

            def on_progress(pct: int):
                storage.update_job(job_id, {"percent": pct})

            await asyncio.to_thread(
                ffmpeg.render_viral, local_paths, scenes, width, height,
                track, output_path, on_progress,
            )
            for p in local_paths:
                if p:
                    Path(p).unlink(missing_ok=True)

        # 4. Salva na biblioteca
        storage.add_video(output_id, output_path, script["title"], meta={
            "kind": "viral",
            "title": script["title"],
            "description": script["description"],
            "tags": script["tags"],
        })
        storage.update_job(job_id, {"stage": "completed", "percent": 100,
                                    "video_id": output_id})
    except Exception as e:
        storage.update_job(job_id, {"stage": "failed", "error": str(e)})
