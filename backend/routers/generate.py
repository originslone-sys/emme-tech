from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pathlib import Path
from typing import List
import uuid

from services import storage, runpod

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

    job_id = await runpod.submit_generate_job(ref_paths, prompt)

    output_id = str(uuid.uuid4())
    output_path = str(storage.DIRS["images"] / f"{output_id}.png")

    storage.save_job(job_id, runpod.RUNPOD_IMAGE_ENDPOINT, "generate", {
        "output_id": output_id,
        "output_path": output_path,
        "prompt": prompt,
    })

    return {"job_id": job_id, "status": "processing"}


@router.get("/jobs/{job_id}")
async def get_generate_status(job_id: str):
    job = storage.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job não encontrado")

    result = await runpod.get_job_status(job["endpoint_id"], job_id)
    status = result.get("status")
    output_path = job["meta"]["output_path"]

    if status == "COMPLETED" and not Path(output_path).exists():
        saved = await runpod.save_output(result, output_path)
        if saved:
            storage.add_image(job["meta"]["output_id"], output_path, job["meta"]["prompt"])

    return {
        "job_id": job_id,
        "status": status,
        "image_id": job["meta"]["output_id"] if status == "COMPLETED" else None,
        "error": result.get("error"),
    }
