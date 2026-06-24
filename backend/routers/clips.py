from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional
import asyncio
import uuid

from services import storage, runpod, clips

router = APIRouter()


@router.post("/generate")
async def generate_clips(
    video: Optional[UploadFile] = File(None),
    youtube_url: Optional[str] = Form(None),
    num_clips: int = Form(3),
    language: str = Form(""),
    banner: Optional[UploadFile] = File(None),
    show_title: int = Form(1),
    channel_name: Optional[str] = Form(None),
):
    if not video and not youtube_url:
        raise HTTPException(400, "Envie um vídeo ou um link do YouTube")

    num_clips = max(1, min(num_clips, 30))

    video_path = None
    if video:
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
