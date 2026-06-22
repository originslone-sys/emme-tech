import httpx
import os
import base64

RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY", "")
RUNPOD_ANIMATE_ENDPOINT = os.getenv("RUNPOD_ANIMATE_ENDPOINT", "")
RUNPOD_IMAGE_ENDPOINT = os.getenv("RUNPOD_IMAGE_ENDPOINT", "")
BASE_URL = "https://api.runpod.io/v2"


def file_to_base64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


async def submit_animate_job(image_path: str, video_path: str) -> str:
    payload = {
        "image": file_to_base64(image_path),
        "video": file_to_base64(video_path),
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/{RUNPOD_ANIMATE_ENDPOINT}/run",
            json={"input": payload},
            headers={"Authorization": f"Bearer {RUNPOD_API_KEY}"},
            timeout=60,
        )
        response.raise_for_status()
        return response.json()["id"]


async def submit_generate_job(reference_paths: list[str], prompt: str) -> str:
    images_b64 = [file_to_base64(p) for p in reference_paths]
    payload = {
        "reference_images": images_b64,
        "prompt": prompt,
        "num_inference_steps": 30,
        "guidance_scale": 5.0,
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/{RUNPOD_IMAGE_ENDPOINT}/run",
            json={"input": payload},
            headers={"Authorization": f"Bearer {RUNPOD_API_KEY}"},
            timeout=60,
        )
        response.raise_for_status()
        return response.json()["id"]


async def get_job_status(endpoint_id: str, job_id: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/{endpoint_id}/status/{job_id}",
            headers={"Authorization": f"Bearer {RUNPOD_API_KEY}"},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()


async def save_output(job_result: dict, output_path: str) -> bool:
    output = job_result.get("output", {})
    if "video" in output:
        data = base64.b64decode(output["video"])
    elif "image" in output:
        data = base64.b64decode(output["image"])
    else:
        return False
    with open(output_path, "wb") as f:
        f.write(data)
    return True
