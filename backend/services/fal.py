import httpx
import os

FAL_KEY = os.getenv("FAL_KEY", "")
BACKEND_URL = os.getenv("BACKEND_URL", "")
QUEUE_BASE = "https://queue.fal.run"

# Modelos do Fal.ai
IMAGE_MODEL = "fal-ai/flux-pulid"
VIDEO_MODEL = "fal-ai/kling-video/v2.6/standard/motion-control"

_HEADERS = {"Authorization": f"Key {FAL_KEY}"}


def file_to_url(path: str) -> str:
    filename = os.path.basename(path)
    return f"{BACKEND_URL}/files/uploads/{filename}"


async def _submit(model: str, payload: dict) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{QUEUE_BASE}/{model}",
            json=payload,
            headers={**_HEADERS, "Content-Type": "application/json"},
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
    return {
        "request_id": data["request_id"],
        "status_url": data["status_url"],
        "response_url": data["response_url"],
    }


async def submit_generate_job(reference_paths: list[str], prompt: str) -> dict:
    payload = {
        "prompt": prompt,
        "reference_image_url": file_to_url(reference_paths[0]),
        "image_size": "portrait_4_3",
        "num_inference_steps": 20,
        "guidance_scale": 4,
        "id_weight": 1.0,
        "true_cfg": 1.0,
        "negative_prompt": "bad quality, worst quality, deformed, blurry, low resolution, distorted face",
    }
    return await _submit(IMAGE_MODEL, payload)


async def submit_animate_job(image_path: str, video_path: str) -> dict:
    payload = {
        "image_url": file_to_url(image_path),
        "video_url": file_to_url(video_path),
        "character_orientation": "video",
    }
    return await _submit(VIDEO_MODEL, payload)


async def get_job_status(status_url: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(status_url, headers=_HEADERS, timeout=30)
        response.raise_for_status()
        return response.json()


async def get_result(response_url: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(response_url, headers=_HEADERS, timeout=60)
        response.raise_for_status()
        return response.json()


async def save_output(result: dict, output_path: str) -> bool:
    url = None

    images = result.get("images")
    if images and images[0].get("url"):
        url = images[0]["url"]

    video = result.get("video")
    if video and video.get("url"):
        url = video["url"]

    if not url:
        return False

    async with httpx.AsyncClient() as client:
        r = await client.get(url, timeout=300)
        r.raise_for_status()
        with open(output_path, "wb") as f:
            f.write(r.content)
    return True
