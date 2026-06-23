"""
Teste rápido do endpoint Wan Animate no RunPod.
Envia um job com URLs de imagem e vídeo públicas e verifica se o endpoint aceita.

Uso:
  RUNPOD_API_KEY=xxx RUNPOD_ANIMATE_ENDPOINT=yyy python test_animate.py
"""

import asyncio
import httpx
import os
import sys

API_KEY = os.getenv("RUNPOD_API_KEY", "")
ENDPOINT_ID = os.getenv("RUNPOD_ANIMATE_ENDPOINT", "")
BASE_URL = "https://api.runpod.io/v2"

# Imagem e vídeo públicos para teste (pequenos e acessíveis)
TEST_IMAGE_URL = "https://images.unsplash.com/photo-1529626455594-4ff0802cfb7e?w=512&h=512&fit=crop"
TEST_VIDEO_URL = "https://www.w3schools.com/html/mov_bbb.mp4"


async def submit_test_job() -> dict:
    payload = {
        "image_url": TEST_IMAGE_URL,
        "video_url": TEST_VIDEO_URL,
        "prompt": "animate the character replicating the movements from the reference video, high quality, realistic motion",
        "steps": 20,
        "fps": 10,
        "seed": 42,
        "cfg": 7,
        "width": 512,
        "height": 320,
        "num_frames": 81,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/{ENDPOINT_ID}/run",
            json={"input": payload},
            headers={"Authorization": f"Bearer {API_KEY}"},
            timeout=30,
        )
        return response.status_code, response.json()


async def get_status(job_id: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/{ENDPOINT_ID}/status/{job_id}",
            headers={"Authorization": f"Bearer {API_KEY}"},
            timeout=30,
        )
        return response.json()


async def main():
    if not API_KEY:
        print("ERRO: variável RUNPOD_API_KEY não definida")
        sys.exit(1)
    if not ENDPOINT_ID:
        print("ERRO: variável RUNPOD_ANIMATE_ENDPOINT não definida")
        sys.exit(1)

    print(f"Endpoint: {ENDPOINT_ID}")
    print(f"Enviando job de teste...")

    status_code, result = await submit_test_job()

    print(f"\nHTTP Status: {status_code}")
    print(f"Resposta: {result}")

    if status_code != 200:
        print("\nFALHOU - o endpoint recusou a requisição")
        sys.exit(1)

    job_id = result.get("id")
    if not job_id:
        print("\nFALHOU - resposta não contém job ID")
        sys.exit(1)

    print(f"\nJob aceito! ID: {job_id}")
    print("Aguardando status inicial (10s)...")
    await asyncio.sleep(10)

    status_result = await get_status(job_id)
    job_status = status_result.get("status")
    print(f"Status do job: {job_status}")
    print(f"Resposta completa: {status_result}")

    if job_status in ("IN_QUEUE", "IN_PROGRESS", "COMPLETED"):
        print("\nSUCESSO - endpoint está recebendo e processando requisições corretamente")
    else:
        print(f"\nATENÇÃO - status inesperado: {job_status}")
        if status_result.get("error"):
            print(f"Erro: {status_result['error']}")


if __name__ == "__main__":
    asyncio.run(main())
