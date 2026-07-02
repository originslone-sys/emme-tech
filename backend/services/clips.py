import asyncio
import uuid
from pathlib import Path

from services import storage, ffmpeg, youtube


def _plan_segments(duration: float, num_clips: int, seg_len: float) -> list[tuple[float, float]]:
    """Distribui N cortes ao longo do vídeo, sem sobreposição.

    Sem transcrição, não dá pra saber "os melhores momentos" — então
    espalhamos os cortes de forma uniforme do começo ao fim, cada um com
    duração seg_len."""
    if duration <= 0:
        return []
    seg_len = max(5.0, min(seg_len, duration))
    if duration <= seg_len:
        return [(0.0, round(duration, 2))]

    n = max(1, num_clips)
    step = duration / n
    segs: list[tuple[float, float]] = []
    for i in range(n):
        center = step * (i + 0.5)
        start = max(0.0, min(center - seg_len / 2, duration - seg_len))
        segs.append((round(start, 2), round(start + seg_len, 2)))
    return segs


async def run_pipeline(job_id: str, num_clips: int, banner_path: str | None,
                       language: str, video_path: str | None = None,
                       youtube_url: str | None = None,
                       show_title: bool = True,
                       channel_name: str | None = None,
                       min_duration: int = 15):
    """Gera cortes verticais 100% no Railway (FFmpeg + yt-dlp), sem transcrição
    nem GPU externa. Os cortes são distribuídos ao longo do vídeo."""
    source_video: str | None = None
    try:
        # 0. Baixa do YouTube se for o caso
        if youtube_url:
            storage.update_job(job_id, {"stage": "downloading"})
            video_path = await asyncio.to_thread(youtube.download, youtube_url)
        if not video_path:
            raise RuntimeError("Nenhum vídeo de entrada")
        source_video = video_path

        # 1. Duração + planejamento dos cortes (local, sem transcrição)
        storage.update_job(job_id, {"stage": "analyzing", "done": 0, "total": 0})
        duration = await asyncio.to_thread(ffmpeg.probe_duration, video_path)
        # Comprimento de cada corte: entre 30 e 90s, respeitando min_duration.
        seg_len = float(min(max(min_duration, 30), 90))
        segments = _plan_segments(duration, num_clips, seg_len)
        if not segments:
            raise RuntimeError("Não foi possível determinar a duração do vídeo")

        # 2. Renderiza cada corte em vertical com fundo desfocado
        storage.update_job(job_id, {"stage": "rendering", "done": 0, "total": len(segments)})
        # Banner vai no rodapé; sobe o título para ficar acima dele.
        sub_margin_v = 120
        if banner_path:
            sub_margin_v = 120 + ffmpeg.banner_overlay_height(banner_path)

        produced = []
        for i, (start, end) in enumerate(segments):
            out_id = str(uuid.uuid4())
            out_path = str(storage.DIRS["videos"] / f"{out_id}.mp4")
            ass_path = str(storage.DIRS["uploads"] / f"{out_id}.ass")
            title = f"Corte {i + 1}"

            # .ass só com o título (sem legendas — não há transcrição).
            # Segmentos vazios => nenhuma legenda, apenas o título opcional no topo.
            clip_title = title if show_title else None
            await asyncio.to_thread(
                ffmpeg.build_ass, [], 0.0, end - start, ass_path,
                clip_title, sub_margin_v,
            )
            await asyncio.to_thread(
                ffmpeg.render_clip, video_path, out_path,
                start, end, ass_path, banner_path, channel_name,
            )
            Path(ass_path).unlink(missing_ok=True)

            storage.add_video(out_id, out_path, title, meta={
                "kind": "clip",
                "title": title,
            })
            produced.append(out_id)
            storage.update_job(job_id, {"done": i + 1, "clip_ids": produced})

        storage.update_job(job_id, {"stage": "completed", "clip_ids": produced})
    except Exception as e:
        storage.update_job(job_id, {"stage": "failed", "error": str(e)})
    finally:
        # Remove o vídeo de origem (os cortes finais já estão em videos/).
        if source_video:
            Path(source_video).unlink(missing_ok=True)
