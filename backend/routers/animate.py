from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
import uuid

from services import storage, fal

router = APIRouter()


@router.post("/")
async def animate_video(
    image: UploadFile = File(...),
    reference_video: UploadFile = File(...),
):
    _, image_path = await storage.save_upload(image, "uploads")
    _, video_path = await storage.save_upload(reference_video, "uploads")

    job = await fal.submit_animate_job(image_path, video_path)

    output_id = str(uuid.uuid4())
    output_path = str(storage.DIRS["videos"] / f"{output_id}.mp4")

    storage.save_job(job["request_id"], fal.VIDEO_MODEL, "animate", {
        "output_id": output_id,
        "output_path": output_path,
        "status_url": job["status_url"],
        "response_url": job["response_url"],
    })

    return {"job_id": job["request_id"], "status": "processing"}


@router.get("/jobs/{job_id}")
async def get_animate_status(job_id: str):
    job = storage.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job não encontrado")

    meta = job["meta"]
    output_path = meta["output_path"]

    try:
        status_data = await fal.get_job_status(meta["status_url"])
    except Exception as e:
        return {"job_id": job_id, "status": "FAILED", "video_id": None, "error": str(e)}

    status = status_data.get("status")

    if status == "COMPLETED":
        try:
            if not Path(output_path).exists():
                result = await fal.get_result(meta["response_url"])
                if await fal.save_output(result, output_path):
                    storage.add_video(meta["output_id"], output_path)
        except Exception as e:
            return {"job_id": job_id, "status": "FAILED", "video_id": None, "error": str(e)}

        return {"job_id": job_id, "status": "COMPLETED", "video_id": meta["output_id"], "error": None}

    return {"job_id": job_id, "status": status, "video_id": None, "error": None}
