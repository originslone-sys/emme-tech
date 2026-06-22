from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
import uuid

from services import storage, runpod

router = APIRouter()


@router.post("/")
async def animate_video(
    image: UploadFile = File(...),
    reference_video: UploadFile = File(...),
):
    _, image_path = await storage.save_upload(image, "uploads")
    _, video_path = await storage.save_upload(reference_video, "uploads")

    job_id = await runpod.submit_animate_job(image_path, video_path)

    output_id = str(uuid.uuid4())
    output_path = str(storage.DIRS["videos"] / f"{output_id}.mp4")

    storage.save_job(job_id, runpod.RUNPOD_ANIMATE_ENDPOINT, "animate", {
        "output_id": output_id,
        "output_path": output_path,
    })

    return {"job_id": job_id, "status": "processing"}


@router.get("/jobs/{job_id}")
async def get_animate_status(job_id: str):
    job = storage.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job não encontrado")

    result = await runpod.get_job_status(job["endpoint_id"], job_id)
    status = result.get("status")
    output_path = job["meta"]["output_path"]

    if status == "COMPLETED" and not Path(output_path).exists():
        saved = await runpod.save_output(result, output_path)
        if saved:
            storage.add_video(job["meta"]["output_id"], output_path)

    return {
        "job_id": job_id,
        "status": status,
        "video_id": job["meta"]["output_id"] if status == "COMPLETED" else None,
        "error": result.get("error"),
    }
