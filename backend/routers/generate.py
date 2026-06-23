from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pathlib import Path
from typing import List
import uuid

from services import storage, fal

router = APIRouter()


@router.post("/")
async def generate_image(
    references: List[UploadFile] = File(...),
    prompt: str = Form(...),
):
    if not 1 <= len(references) <= 5:
        raise HTTPException(400, "Envie entre 1 e 5 fotos de referência")

    ref_paths = []
    for ref in references:
        _, path = await storage.save_upload(ref, "uploads")
        ref_paths.append(path)

    job = await fal.submit_generate_job(ref_paths, prompt)

    output_id = str(uuid.uuid4())
    output_path = str(storage.DIRS["images"] / f"{output_id}.png")

    storage.save_job(job["request_id"], fal.IMAGE_MODEL, "generate", {
        "output_id": output_id,
        "output_path": output_path,
        "prompt": prompt,
        "status_url": job["status_url"],
        "response_url": job["response_url"],
    })

    return {"job_id": job["request_id"], "status": "processing"}


@router.get("/jobs/{job_id}")
async def get_generate_status(job_id: str):
    job = storage.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job não encontrado")

    meta = job["meta"]
    output_path = meta["output_path"]

    try:
        status_data = await fal.get_job_status(meta["status_url"])
    except Exception as e:
        return {"job_id": job_id, "status": "FAILED", "image_id": None, "error": str(e)}

    status = status_data.get("status")

    if status == "COMPLETED":
        try:
            if not Path(output_path).exists():
                result = await fal.get_result(meta["response_url"])
                if await fal.save_output(result, output_path):
                    storage.add_image(meta["output_id"], output_path, meta["prompt"])
        except Exception as e:
            return {"job_id": job_id, "status": "FAILED", "image_id": None, "error": str(e)}

        return {"job_id": job_id, "status": "COMPLETED", "image_id": meta["output_id"], "error": None}

    return {"job_id": job_id, "status": status, "image_id": None, "error": None}
