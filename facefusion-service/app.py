"""Wrapper HTTP para face swap de imagem via FaceFusion (headless, CPU).

Endpoint:
    POST /swap-image  (multipart: source=rosto, target=imagem-alvo)
        -> devolve a imagem com o rosto trocado (image/jpeg)

Protegido por SWAP_API_KEY (header X-API-Key) — defina no Railway para não
deixar o endpoint aberto na URL pública.
"""
import os
import subprocess
import tempfile
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

app = FastAPI(title="FaceFusion Swap Service")

FACEFUSION_DIR = Path("/opt/facefusion")
WORK = Path(tempfile.gettempdir()) / "ff"
WORK.mkdir(parents=True, exist_ok=True)

API_KEY = os.getenv("SWAP_API_KEY", "")
_TIMEOUT = int(os.getenv("SWAP_TIMEOUT", "300"))  # segundos por swap

# Modelos (configuráveis por env). inswapper_128_fp16 = swap; gfpgan_1.4 = nitidez.
_SWAPPER_MODEL = os.getenv("FF_SWAPPER_MODEL", "inswapper_128_fp16")
_ENHANCER_MODEL = os.getenv("FF_ENHANCER_MODEL", "gfpgan_1.4")


def _cleanup(*paths: Path):
    for p in paths:
        try:
            p.unlink(missing_ok=True)
        except OSError:
            pass


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/swap-image")
async def swap_image(
    source: UploadFile = File(..., description="Rosto a inserir (sua foto)"),
    target: UploadFile = File(..., description="Imagem-alvo (já pronta)"),
    x_api_key: str = Header(default=""),
):
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(401, "não autorizado")

    job = uuid.uuid4().hex
    src = WORK / f"{job}_src{Path(source.filename or '').suffix or '.jpg'}"
    tgt = WORK / f"{job}_tgt{Path(target.filename or '').suffix or '.jpg'}"
    out = WORK / f"{job}_out.jpg"

    src.write_bytes(await source.read())
    tgt.write_bytes(await target.read())

    cmd = [
        "python", "facefusion.py", "headless-run",
        "-s", str(src),
        "-t", str(tgt),
        "-o", str(out),
        "--processors", "face_swapper", "face_enhancer",
        "--execution-providers", "cpu",
        "--face-swapper-model", _SWAPPER_MODEL,
        "--face-enhancer-model", _ENHANCER_MODEL,
    ]

    try:
        proc = subprocess.run(
            cmd, cwd=str(FACEFUSION_DIR),
            capture_output=True, text=True, timeout=_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        _cleanup(src, tgt, out)
        raise HTTPException(504, "swap excedeu o tempo limite")

    _cleanup(src, tgt)

    if proc.returncode != 0 or not out.exists():
        _cleanup(out)
        detail = (proc.stderr or proc.stdout or "erro desconhecido")[-600:]
        raise HTTPException(500, f"swap falhou: {detail}")

    return FileResponse(
        str(out), media_type="image/jpeg", filename="swapped.jpg",
        background=BackgroundTask(_cleanup, out),
    )
