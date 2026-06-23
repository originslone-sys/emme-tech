from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional
import asyncio
import uuid

from services import storage, runpod, viral

router = APIRouter()

_FORMATS = {"9:16", "1:1", "16:9"}


@router.post("/generate")
async def generate_viral(
    topic: str = Form(...),
    fmt: str = Form("9:16"),
    duration: int = Form(30),
    language: str = Form("Português"),
    narration: int = Form(1),
    voice: str = Form("feminina"),
    music_source: str = Form("library"),
    music: Optional[UploadFile] = File(None),
    channel_name: Optional[str] = Form(None),
    intro_title: int = Form(1),
):
    topic = topic.strip()
    if not topic:
        raise HTTPException(400, "Descreva o tema do vídeo")
    if fmt not in _FORMATS:
        fmt = "9:16"
    duration = max(10, min(duration, 90))
    voice = voice if voice in ("feminina", "masculina") else "feminina"
    if music_source not in ("generate", "library", "none"):
        music_source = "library"

    music_path = None
    if music:
        music_path = await storage.save_upload_temp(music)
        music_source = "upload"  # arquivo enviado tem prioridade

    job_id = str(uuid.uuid4())
    endpoint = runpod.RENDER_ENDPOINT or "local"
    storage.save_job(job_id, endpoint, "viral", {"stage": "starting"})

    asyncio.create_task(viral.run_pipeline(
        job_id, topic, fmt, duration, language, music_path,
        narration=bool(narration), voice=voice, music_source=music_source,
        channel_name=channel_name or None, intro_title=bool(intro_title),
    ))

    return {"job_id": job_id, "status": "processing"}


@router.get("/jobs/{job_id}")
async def get_viral_status(job_id: str):
    job = storage.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job não encontrado")

    meta = job["meta"]
    stage = meta.get("stage", "starting")

    if stage == "failed":
        return {"status": "FAILED", "stage": stage, "error": meta.get("error"),
                "video_id": None, "done": 0, "total": 0, "percent": 0}
    if stage == "completed":
        warnings = [w for w in (meta.get("warning"), meta.get("warning_music")) if w]
        return {"status": "COMPLETED", "stage": stage, "error": None,
                "video_id": meta.get("video_id"),
                "warnings": warnings,
                "done": meta.get("done", 0), "total": meta.get("total", 0),
                "percent": 100}
    return {"status": "processing", "stage": stage, "error": None,
            "video_id": None,
            "done": meta.get("done", 0), "total": meta.get("total", 0),
            "percent": meta.get("percent", 0)}
