from fastapi import APIRouter, Header, Request, UploadFile, File, Form, HTTPException
from typing import Optional
import asyncio
import logging
import re
import uuid

import aiofiles

from services import storage, clips

logger = logging.getLogger(__name__)

router = APIRouter()

# upload_id deve ser um UUID (evita path traversal)
_UPLOAD_ID_RE = re.compile(r"^[a-f0-9-]{36}$")


def _part_path(upload_id: str):
    if not _UPLOAD_ID_RE.match(upload_id):
        raise HTTPException(400, "upload_id inválido")
    return storage.DIRS["uploads"] / f"{upload_id}.part"


@router.post("/upload-chunk")
async def upload_chunk(
    request: Request,
    upload_id: str = Header(..., alias="X-Upload-Id"),
    chunk_index: int = Header(..., alias="X-Chunk-Index"),
):
    """Recebe um pedaço de vídeo como corpo binário puro (application/octet-stream).

    Usa headers em vez de multipart para evitar limites de proxy em form-data.
    Chunks são anexados em ordem ao arquivo .part correspondente.
    """
    path = _part_path(upload_id)
    content = await request.body()
    if not content:
        raise HTTPException(400, "Chunk vazio")
    mode = "wb" if chunk_index == 0 else "ab"
    async with aiofiles.open(path, mode) as f:
        await f.write(content)
    logger.info("chunk upload_id=%s index=%d size=%d", upload_id, chunk_index, len(content))
    return {"ok": True, "size": len(content)}


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
        logger.info("generate: upload_id=%s part=%s exists=%s", upload_id, part, part.exists())
        if not part.exists():
            raise HTTPException(400, f"Upload não encontrado (esperado em {part}). Tente novamente.")
        ext = video_ext if (video_ext or "").startswith(".") else ".mp4"
        final = storage.DIRS["uploads"] / f"{upload_id}{ext}"
        part.rename(final)
        video_path = str(final)
        logger.info("generate: video assembled at %s size=%d", video_path, final.stat().st_size)
    elif video:
        video_path = await storage.save_upload_temp(video)

    banner_path = None
    if banner:
        banner_path = await storage.save_upload_temp(banner)

    job_id = str(uuid.uuid4())
    storage.save_job(job_id, "local", "clips", {"stage": "starting"})

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
