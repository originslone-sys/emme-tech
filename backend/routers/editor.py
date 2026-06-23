from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.concurrency import run_in_threadpool
from pathlib import Path
from typing import List
import uuid

from services import storage, runpod, ffmpeg

router = APIRouter()


def _new_video_path() -> tuple[str, str]:
    vid = str(uuid.uuid4())
    return vid, str(storage.DIRS["videos"] / f"{vid}.mp4")


# ---------- Melhoria de qualidade (RunPod / GPU) ----------

@router.post("/enhance")
async def enhance_video(
    video: UploadFile = File(...),
    scale: int = Form(2),
):
    video_path = await storage.save_upload_temp(video)
    job_id = await runpod.submit_enhance_job(video_path, scale)

    output_id, output_path = _new_video_path()
    storage.save_job(job_id, runpod.ENHANCE_ENDPOINT, "enhance", {
        "output_id": output_id,
        "output_path": output_path,
        "label": f"{Path(video.filename).stem} (melhorado)",
    })
    return {"job_id": job_id, "status": "processing"}


@router.get("/jobs/{job_id}")
async def get_status(job_id: str):
    job = storage.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job não encontrado")

    meta = job["meta"]
    output_path = meta["output_path"]

    try:
        data = await runpod.get_job_status(job_id)
    except Exception as e:
        return {"job_id": job_id, "status": "FAILED", "video_id": None, "error": str(e)}

    status = data.get("status")

    if status == "COMPLETED":
        try:
            if not Path(output_path).exists():
                if await runpod.save_output(data, output_path):
                    storage.add_video(meta["output_id"], output_path, meta.get("label", ""))
        except Exception as e:
            return {"job_id": job_id, "status": "FAILED", "video_id": None, "error": str(e)}
        return {"job_id": job_id, "status": "COMPLETED", "video_id": meta["output_id"], "error": None}

    if status in ("FAILED", "CANCELLED", "TIMED_OUT"):
        return {"job_id": job_id, "status": "FAILED", "video_id": None,
                "error": data.get("error") or "Processamento falhou"}

    return {"job_id": job_id, "status": status, "video_id": None, "error": None}


# ---------- Corte (FFmpeg / síncrono) ----------

@router.post("/trim")
async def trim_video(
    video: UploadFile = File(...),
    start: float = Form(...),
    end: float = Form(...),
):
    if end <= start:
        raise HTTPException(400, "O fim deve ser maior que o início")

    src = await storage.save_upload_temp(video)
    output_id, output_path = _new_video_path()
    try:
        await run_in_threadpool(ffmpeg.trim, src, output_path, start, end)
    except Exception as e:
        raise HTTPException(500, f"Falha ao cortar: {e}")

    storage.add_video(output_id, output_path, f"{Path(video.filename).stem} (corte)")
    return {"video_id": output_id, "status": "COMPLETED"}


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


# ---------- Ajuste de iluminação (FFmpeg) ----------

@router.post("/adjust")
async def adjust_video(
    video: UploadFile = File(...),
    brightness: float = Form(0.0),
    contrast: float = Form(1.0),
    saturation: float = Form(1.0),
):
    src = await storage.save_upload_temp(video)
    output_id, output_path = _new_video_path()
    try:
        await run_in_threadpool(ffmpeg.adjust, src, output_path,
                                brightness, contrast, saturation)
    except Exception as e:
        raise HTTPException(500, f"Falha ao ajustar: {e}")

    storage.add_video(output_id, output_path, f"{Path(video.filename).stem} (ajustado)")
    return {"video_id": output_id, "status": "COMPLETED"}


# ---------- Duração (utilitário para o frontend) ----------

@router.post("/duration")
async def video_duration(video: UploadFile = File(...)):
    src = await storage.save_upload_temp(video)
    duration = await run_in_threadpool(ffmpeg.probe_duration, src)
    return {"duration": duration}
