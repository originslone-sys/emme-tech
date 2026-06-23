import asyncio
import logging
import uuid
from pathlib import Path

from services import storage, deepseek, pexels, music, ffmpeg, runpod, tts

log = logging.getLogger("viral")

DIMENSIONS = {
    "9:16": (1080, 1920),
    "1:1": (1080, 1080),
    "16:9": (1920, 1080),
}

_RENDER_TIMEOUT = 60 * 20  # 20 min
_POLL_INTERVAL = 5


def _apply_narration_timing(scenes: list[dict], narr: list[dict | None]):
    """Ajusta a duração de cada cena para caber a narração (ritmo natural)."""
    for sc, n in zip(scenes, narr):
        if n and n.get("duration", 0) > 0:
            sc["duration"] = round(min(9.0, max(1.8, n["duration"] + 0.45)), 2)


async def _render_on_runpod(scene_urls: list[str | None], scenes: list[dict],
                            narr: list[dict | None] | None,
                            width: int, height: int, music_url: str,
                            output_path: str):
    payload_scenes = []
    for i, (url, sc) in enumerate(zip(scene_urls, scenes)):
        narr_url = ""
        if narr and narr[i]:
            narr_url = runpod.file_to_url(narr[i]["path"])
        payload_scenes.append({
            "video_url": url or "",
            "duration": sc["duration"],
            "text": sc["text"],
            "narration_url": narr_url,
        })
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


async def _resolve_music(job_id: str, mood: str, music_path: str | None,
                         music_source: str) -> str | None:
    """Decide a trilha conforme a opção escolhida no app.

    - upload tem prioridade absoluta (music_path)
    - "generate": gera nova faixa via Eleven Music e salva na biblioteca
    - "library": usa uma faixa já existente na biblioteca
    - "none": sem música
    """
    if music_path:
        return music_path
    if music_source == "none":
        return None
    if music_source == "generate":
        storage.update_job(job_id, {"stage": "music"})
        try:
            track = await music.generate(mood)
            if track:
                return track
        except Exception as e:
            log.exception("Eleven Music falhou")
            storage.update_job(job_id, {"warning_music":
                f"Geração de música falhou, tentando a biblioteca: {e}"})
        return music.pick(mood)  # fallback se a geração falhar
    # "library" (ou padrão)
    return music.pick(mood)


async def run_pipeline(job_id: str, topic: str, fmt: str, duration: int,
                       language: str, music_path: str | None = None,
                       narration: bool = True, voice: str = "feminina",
                       music_source: str = "library",
                       channel_name: str | None = None,
                       intro_title: bool = True):
    try:
        width, height = DIMENSIONS.get(fmt, DIMENSIONS["9:16"])

        # 1. Roteiro viral com a IA
        storage.update_job(job_id, {"stage": "scripting"})
        script = await deepseek.generate_viral_script(topic, duration, language, fmt)
        scenes = script["scenes"]

        # O narrador abre apresentando o vídeo com o título (vira fala + legenda).
        title = (script.get("title") or "").strip()
        if intro_title and scenes and title:
            first = scenes[0]
            opening = (first.get("narration") or "").strip()
            if not opening.lower().startswith(title.lower()[:18]):
                lead = title.rstrip(" .!?:;,")  # evita pontuação dupla
                first["narration"] = f"{lead}. {opening}".strip()

        # 2. Narração (TTS) — define o ritmo/duração das cenas
        narr: list[dict | None] | None = None
        if narration:
            storage.update_job(job_id, {"stage": "narrating"})
            try:
                narr = await tts.synthesize_scenes(
                    [sc["narration"] for sc in scenes], language, voice)
                if not narr or not any(narr):
                    raise RuntimeError("o TTS não retornou áudio")
                _apply_narration_timing(scenes, narr)
            except Exception as e:
                # Não falha o vídeo todo, mas registra o motivo para diagnóstico.
                narr = None
                log.exception("Narração (TTS) falhou")
                storage.update_job(job_id, {"warning": f"Narração falhou: {e}"})

        # 3. Encontra um clipe do Pexels para cada cena
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

        # 4. Trilha sonora (pode gerar via Eleven Music e salvar na biblioteca)
        track = await _resolve_music(job_id, script["music_mood"], music_path, music_source)
        if not track and music_source != "none":
            storage.update_job(job_id, {"warning_music":
                "Sem trilha: a biblioteca de músicas está vazia. Gere uma faixa ou envie a sua."})

        # 5. Render — GPU no RunPod se configurado, senão local
        storage.update_job(job_id, {"stage": "rendering", "percent": 0})

        if runpod.RENDER_ENDPOINT:
            music_url = runpod.file_to_url(track) if track else ""
            await _render_on_runpod(scene_urls, scenes, narr, width, height,
                                    music_url, output_path)
        else:
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

            narr_paths = [n["path"] if n else None for n in narr] if narr else None

            def on_progress(pct: int):
                storage.update_job(job_id, {"percent": pct})

            await asyncio.to_thread(
                ffmpeg.render_viral, local_paths, scenes, width, height,
                track, output_path, on_progress, narr_paths, channel_name,
            )
            for p in local_paths:
                if p:
                    Path(p).unlink(missing_ok=True)

        # 6. Salva na biblioteca
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
