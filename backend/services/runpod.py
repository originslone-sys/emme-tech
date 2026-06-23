import httpx
import os
import base64

RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY", "")
ENHANCE_ENDPOINT = os.getenv("RUNPOD_ENHANCE_ENDPOINT", "")
WHISPER_ENDPOINT = os.getenv("RUNPOD_WHISPER_ENDPOINT", "")
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


async def get_job_status(job_id: str, endpoint: str = "") -> dict:
    ep = endpoint or ENHANCE_ENDPOINT
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/{ep}/status/{job_id}",
            headers=_HEADERS,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()


async def submit_transcribe_job(audio_path: str, language: str = "") -> str:
    """Envia o áudio para o endpoint WhisperX (kodxana) e retorna o job id."""
    payload = {
        "input": {
            "audio_file": file_to_url(audio_path),
            "batch_size": 16,
            "align_output": False,
        }
    }
    if language:
        payload["input"]["language"] = language

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE_URL}/{WHISPER_ENDPOINT}/run",
            json=payload,
            headers={**_HEADERS, "Content-Type": "application/json"},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["id"]


def extract_segments(status_data: dict) -> list[dict]:
    """Normaliza a saída do worker Whisper para uma lista de {start, end, text}."""
    output = status_data.get("output") or {}
    if isinstance(output, list):
        output = output[0] if output else {}

    segments = output.get("segments") or output.get("transcription_segments") or []
    result = []
    for s in segments:
        text = (s.get("text") or "").strip()
        if not text:
            continue
        result.append({
            "start": float(s.get("start", 0)),
            "end": float(s.get("end", 0)),
            "text": text,
        })
    return result


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
