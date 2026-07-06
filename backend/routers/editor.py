from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.concurrency import run_in_threadpool
from pathlib import Path
from typing import List
import asyncio
import uuid

from services import storage, ffmpeg

router = APIRouter()


def _new_video_path() -> tuple[str, str]:
    vid = str(uuid.uuid4())
    return vid, str(storage.DIRS["videos"] / f"{vid}.mp4")


# ---------- Edição completa num único passe ----------

@router.post("/process")
async def process_video(
    video: UploadFile = File(...),
    trim_start: float = Form(0.0),
    trim_end: float = Form(0.0),      # 0 = até o fim
    brightness: float = Form(0.0),
    contrast: float = Form(1.0),
    saturation: float = Form(1.0),
    upscale: int = Form(0),           # 0 = não, 2 ou 4 = fator de upscaling
):
    src = await storage.save_upload_temp(video)
    label = f"{Path(video.filename).stem} (editado)"
    output_id, output_path = _new_video_path()

    try:
        if upscale:
            # Melhoria de qualidade (upscale + sharpen + denoise) — 100% CPU,
            # sem GPU. Roda em background com progresso pois pode demorar.
            job_id = str(uuid.uuid4())
            storage.save_job(job_id, "ffmpeg", "enhance", {
                "stage": "starting", "percent": 0,
                "output_id": output_id, "output_path": output_path, "label": label,
            })
            asyncio.create_task(_run_enhance(
                job_id, src, output_id, output_path, label,
                trim_start, trim_end, brightness, contrast, saturation, upscale,
            ))
            return {"job_id": job_id, "status": "processing", "video_id": None}

        # Sem upscaling: tudo num único passe local, resultado imediato.
        await run_in_threadpool(
            ffmpeg.process, src, output_path,
            trim_start, trim_end, brightness, contrast, saturation,
        )
    except Exception as e:
        raise HTTPException(500, f"Falha ao processar: {e}")

    storage.add_video(output_id, output_path, label)
    return {"job_id": None, "status": "COMPLETED", "video_id": output_id}


async def _run_enhance(job_id: str, src: str, output_id: str, output_path: str,
                       label: str, start: float, end: float,
                       brightness: float, contrast: float, saturation: float,
                       upscale: int):
    try:
        def on_progress(pct: int):
            storage.update_job(job_id, {"percent": pct})

        storage.update_job(job_id, {"stage": "processing", "percent": 0})
        await asyncio.to_thread(
            ffmpeg.enhance, src, output_path, start, end,
            brightness, contrast, saturation, upscale, on_progress,
        )
        storage.add_video(output_id, output_path, label)
        storage.update_job(job_id, {"stage": "completed", "percent": 100,
                                    "video_id": output_id})
    except Exception as e:
        storage.update_job(job_id, {"stage": "failed", "error": str(e)})
    finally:
        Path(src).unlink(missing_ok=True)


# ---------- Linha do tempo / juntar (FFmpeg) ----------

@router.post("/join")
async def join_videos(videos: List[UploadFile] = File(...)):
    if len(videos) < 2:
        raise HTTPException(400, "Envie pelo menos 2 vídeos para juntar")

    srcs = [await storage.save_upload_temp(v) for v in videos]
    output_id, output_path = _new_video_path()
    try:
        await run_in_threadpool(ffmpeg.join, srcs, output_path)
    except Exception as e:
        raise HTTPException(500, f"Falha ao juntar: {e}")

    storage.add_video(output_id, output_path, "Vídeos unidos")
    return {"video_id": output_id, "status": "COMPLETED"}


# ---------- Originalizar (repostagem em outras redes) ----------

async def _run_spin(job_id: str, src: str, output_id: str, output_path: str, label: str):
    try:
        def on_progress(pct: int):
            storage.update_job(job_id, {"percent": pct})

        storage.update_job(job_id, {"stage": "processing", "percent": 0})
        await asyncio.to_thread(ffmpeg.spin, src, output_path, on_progress)
        storage.add_video(output_id, output_path, label, meta={"kind": "repost"})
        storage.update_job(job_id, {"stage": "completed", "percent": 100,
                                    "video_id": output_id})
    except Exception as e:
        storage.update_job(job_id, {"stage": "failed", "error": str(e)})


@router.post("/spin")
async def spin_video(video: UploadFile = File(...)):
    src = await storage.save_upload_temp(video)
    output_id, output_path = _new_video_path()
    label = f"{Path(video.filename).stem} (repost)"

    job_id = str(uuid.uuid4())
    storage.save_job(job_id, "ffmpeg", "spin", {"stage": "starting", "percent": 0})
    asyncio.create_task(_run_spin(job_id, src, output_id, output_path, label))

    return {"job_id": job_id, "status": "processing"}


@router.get("/local-jobs/{job_id}")
async def get_local_job(job_id: str):
    job = storage.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job não encontrado")

    meta = job["meta"]
    stage = meta.get("stage", "starting")

    if stage == "failed":
        return {"status": "FAILED", "stage": stage, "percent": meta.get("percent", 0),
                "video_id": None, "error": meta.get("error")}
    if stage == "completed":
        return {"status": "COMPLETED", "stage": stage, "percent": 100,
                "video_id": meta.get("video_id"), "error": None}
    return {"status": "processing", "stage": stage,
            "percent": meta.get("percent", 0), "video_id": None, "error": None}
