from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional
import asyncio
import re
import uuid

import aiofiles

from services import storage, runpod, clips

router = APIRouter()

# upload_id deve ser um UUID (evita path traversal)
_UPLOAD_ID_RE = re.compile(r"^[a-f0-9-]{36}$")


def _part_path(upload_id: str):
    if not _UPLOAD_ID_RE.match(upload_id):
        raise HTTPException(400, "upload_id inválido")
    return storage.DIRS["uploads"] / f"{upload_id}.part"


@router.post("/upload-chunk")
async def upload_chunk(
    upload_id: str = Form(...),
    index: int = Form(...),
    chunk: UploadFile = File(...),
):
    """Recebe um pedaço de um upload grande e anexa ao arquivo .part.

    O cliente envia os pedaços em ordem (index 0, 1, 2, ...). Isso contorna
    o limite de tamanho de requisição do proxy/load balancer para vídeos
    grandes (filmes), que falhariam num upload de requisição única.
    """
    path = _part_path(upload_id)
    content = await chunk.read()
    mode = "wb" if index == 0 else "ab"
    async with aiofiles.open(path, mode) as f:
        await f.write(content)
    return {"ok": True}


@router.post("/generate")
async def generate_clips(
    video: Optional[UploadFile] = File(None),
    upload_id: Optional[str] = Form(None),
    video_ext: Optional[str] = Form(None),
    youtube_url: Optional[str] = Form(None),
    num_clips: int = Form(3),
    language: str = Form(""),
    banner: Optional[UploadFile] = File(None),
    show_title: int = Form(1),
    channel_name: Optional[str] = Form(None),
    min_duration: int = Form(15),
):
    if not video and not upload_id and not youtube_url:
        raise HTTPException(400, "Envie um vídeo ou um link do YouTube")

    num_clips = max(1, min(num_clips, 30))
    min_duration = max(5, min(min_duration, 120))

    video_path = None
    if upload_id:
        # Vídeo enviado em pedaços: finaliza o arquivo .part montado.
        part = _part_path(upload_id)
        if not part.exists():
            raise HTTPException(400, "Upload não encontrado ou incompleto")
        ext = video_ext if (video_ext or "").startswith(".") else ".mp4"
        final = storage.DIRS["uploads"] / f"{upload_id}{ext}"
        part.rename(final)
        video_path = str(final)
    elif video:
        video_path = await storage.save_upload_temp(video)

    banner_path = None
    if banner:
        banner_path = await storage.save_upload_temp(banner)

    job_id = str(uuid.uuid4())
    storage.save_job(job_id, runpod.WHISPER_ENDPOINT, "clips", {"stage": "starting"})

    asyncio.create_task(clips.run_pipeline(
        job_id, num_clips, banner_path, language,
        video_path=video_path, youtube_url=youtube_url,
        show_title=bool(show_title), channel_name=channel_name or None,
        min_duration=min_duration,
    ))

    return {"job_id": job_id, "status": "processing"}


@router.get("/jobs/{job_id}")
async def get_clips_status(job_id: str):
    job = storage.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job não encontrado")

    meta = job["meta"]
    stage = meta.get("stage", "starting")

    if stage == "failed":
        return {"status": "FAILED", "stage": stage, "error": meta.get("error"),
                "clip_ids": [], "done": 0, "total": 0}

    if stage == "completed":
        return {"status": "COMPLETED", "stage": stage, "error": None,
                "clip_ids": meta.get("clip_ids", []),
                "done": meta.get("done", 0), "total": meta.get("total", 0)}

    return {"status": "processing", "stage": stage, "error": None,
            "clip_ids": meta.get("clip_ids", []),
            "done": meta.get("done", 0), "total": meta.get("total", 0)}
