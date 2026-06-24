import asyncio
import uuid
from pathlib import Path

from services import storage, runpod, deepseek, ffmpeg, youtube

_WHISPER_TIMEOUT = 60 * 30  # 30 min
_POLL_INTERVAL = 5


async def _transcribe(audio_path: str, language: str) -> list[dict]:
    job_id = await runpod.submit_transcribe_job(audio_path, language)
    waited = 0
    while waited < _WHISPER_TIMEOUT:
        data = await runpod.get_job_status(job_id, runpod.WHISPER_ENDPOINT)
        status = data.get("status")
        if status == "COMPLETED":
            return runpod.extract_segments(data)
        if status in ("FAILED", "CANCELLED", "TIMED_OUT"):
            raise RuntimeError(data.get("error") or "Transcrição falhou")
        await asyncio.sleep(_POLL_INTERVAL)
        waited += _POLL_INTERVAL
    raise RuntimeError("Tempo esgotado na transcrição")


async def run_pipeline(job_id: str, num_clips: int, banner_path: str | None,
                       language: str, video_path: str | None = None,
                       youtube_url: str | None = None,
                       show_title: bool = True,
                       channel_name: str | None = None):
    try:
        # 0. Baixa do YouTube se for o caso
        if youtube_url:
            storage.update_job(job_id, {"stage": "downloading"})
            video_path = await asyncio.to_thread(youtube.download, youtube_url)
        if not video_path:
            raise RuntimeError("Nenhum vídeo de entrada")

        # 1. Áudio para transcrição
        storage.update_job(job_id, {"stage": "transcribing"})
        audio_path = str(storage.DIRS["uploads"] / f"{uuid.uuid4()}.mp3")
        await asyncio.to_thread(ffmpeg.extract_audio, video_path, audio_path)

        segments = await _transcribe(audio_path, language)
        if not segments:
            raise RuntimeError("Não foi possível transcrever o áudio do vídeo")

        # 2. DeepSeek escolhe os melhores trechos
        storage.update_job(job_id, {"stage": "analyzing"})
        clips = await deepseek.select_clips(segments, num_clips)
        if not clips:
            raise RuntimeError("A IA não encontrou bons trechos para cortes")

        # 3. Renderiza cada corte em vertical com legenda
        storage.update_job(job_id, {"stage": "rendering", "total": len(clips)})
        # Banner vai no rodapé; sobe a legenda para ficar acima dele.
        sub_margin_v = 120
        if banner_path:
            sub_margin_v = 120 + ffmpeg.banner_overlay_height(banner_path)
        produced = []
        for i, clip in enumerate(clips):
            out_id = str(uuid.uuid4())
            out_path = str(storage.DIRS["videos"] / f"{out_id}.mp4")
            ass_path = str(storage.DIRS["uploads"] / f"{out_id}.ass")

            clip_title = clip["title"] if show_title else None
            await asyncio.to_thread(
                ffmpeg.build_ass, segments, clip["start"], clip["end"], ass_path,
                clip_title, sub_margin_v,
            )
            await asyncio.to_thread(
                ffmpeg.render_clip, video_path, out_path,
                clip["start"], clip["end"], ass_path, banner_path, channel_name,
            )
            Path(ass_path).unlink(missing_ok=True)

            storage.add_video(out_id, out_path, clip["title"], meta={
                "kind": "clip",
                "title": clip["title"],
                "description": clip["description"],
                "tags": clip["tags"],
                "score": clip["score"],
            })
            produced.append(out_id)
            storage.update_job(job_id, {"done": i + 1, "clip_ids": produced})

        storage.update_job(job_id, {"stage": "completed", "clip_ids": produced})
    except Exception as e:
        storage.update_job(job_id, {"stage": "failed", "error": str(e)})
