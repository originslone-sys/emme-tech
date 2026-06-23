import httpx
import os
import base64

RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY", "")
RUNPOD_ANIMATE_ENDPOINT = os.getenv("RUNPOD_ANIMATE_ENDPOINT", "")
RUNPOD_IMAGE_ENDPOINT = os.getenv("RUNPOD_IMAGE_ENDPOINT", "")
BACKEND_URL = os.getenv("BACKEND_URL", "")
BASE_URL = "https://api.runpod.io/v2"


def file_to_base64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def file_to_url(path: str) -> str:
    filename = os.path.basename(path)
    return f"{BACKEND_URL}/files/uploads/{filename}"


async def submit_animate_job(image_path: str, video_path: str) -> str:
    payload = {
        "image": file_to_url(image_path),
        "video": file_to_url(video_path),
        "prompt": "animate the character replicating the movements from the reference video, high quality, realistic motion",
        "num_inference_steps": 30,
        "guidance_scale": 7.5,
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

    # tenta URL primeiro (mais comum para vídeos grandes)
    if "video_url" in output:
        async with httpx.AsyncClient() as client:
            r = await client.get(output["video_url"], timeout=120)
            with open(output_path, "wb") as f:
                f.write(r.content)
        return True

    if "image_url" in output:
        async with httpx.AsyncClient() as client:
            r = await client.get(output["image_url"], timeout=60)
            with open(output_path, "wb") as f:
                f.write(r.content)
        return True

    # fallback base64
    if "video" in output:
        with open(output_path, "wb") as f:
            f.write(base64.b64decode(output["video"]))
        return True

    if "image" in output:
        with open(output_path, "wb") as f:
            f.write(base64.b64decode(output["image"]))
        return True

    return False
