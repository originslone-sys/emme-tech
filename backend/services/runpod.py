import httpx
import os
import base64

RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY", "")
ENHANCE_ENDPOINT = os.getenv("RUNPOD_ENHANCE_ENDPOINT", "")
BACKEND_URL = os.getenv("BACKEND_URL", "")
BASE_URL = "https://api.runpod.ai/v2"

_HEADERS = {"Authorization": f"Bearer {RUNPOD_API_KEY}"}


def file_to_url(path: str) -> str:
    filename = os.path.basename(path)
    return f"{BACKEND_URL}/files/uploads/{filename}"


async def submit_enhance_job(video_path: str, scale: int = 2) -> str:
    """Envia o vídeo para o endpoint serverless de upscaling e retorna o job id."""
    payload = {
        "input": {
            "video_url": file_to_url(video_path),
            "scale": scale,
        }
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE_URL}/{ENHANCE_ENDPOINT}/run",
            json=payload,
            headers={**_HEADERS, "Content-Type": "application/json"},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["id"]


async def get_job_status(job_id: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/{ENHANCE_ENDPOINT}/status/{job_id}",
            headers=_HEADERS,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()


async def save_output(status_data: dict, output_path: str) -> bool:
    """Salva o resultado do RunPod. Aceita URL ou base64 no campo output."""
    output = status_data.get("output")
    if not output:
        return False

    url = None
    b64 = None
    if isinstance(output, dict):
        url = output.get("video_url") or output.get("url")
        b64 = output.get("video_base64") or output.get("video")
    elif isinstance(output, str):
        if output.startswith("http"):
            url = output
        else:
            b64 = output

    if b64:
        if b64.startswith("data:"):
            b64 = b64.split(",", 1)[1]
        with open(output_path, "wb") as f:
            f.write(base64.b64decode(b64))
        return True

    if url:
        async with httpx.AsyncClient() as client:
            r = await client.get(url, timeout=300)
            r.raise_for_status()
            with open(output_path, "wb") as f:
                f.write(r.content)
        return True

    return False
