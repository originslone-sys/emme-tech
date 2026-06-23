from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from pathlib import Path

from services import storage

router = APIRouter()

_CHUNK = 1024 * 1024  # 1 MB


def _video_stream(path: Path, start: int, end: int):
    with open(path, "rb") as f:
        f.seek(start)
        remaining = end - start + 1
        while remaining > 0:
            chunk = f.read(min(_CHUNK, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk


@router.get("/")
def list_all():
    db = storage.read_db()
    return {
        "images": db.get("images", []),
        "videos": db.get("videos", []),
    }


@router.get("/images/{image_id}/download")
def download_image(image_id: str):
    db = storage.read_db()
    item = next((i for i in db["images"] if i["id"] == image_id), None)
    if not item:
        raise HTTPException(404, "Imagem não encontrada")
    path = Path(item["path"])
    if not path.exists():
        raise HTTPException(404, "Arquivo não encontrado no disco")
    return FileResponse(str(path), media_type="image/png", filename=item["filename"])


@router.get("/videos/{video_id}/download")
def download_video(video_id: str, request: Request):
    db = storage.read_db()
    item = next((i for i in db["videos"] if i["id"] == video_id), None)
    if not item:
        raise HTTPException(404, "Vídeo não encontrado")
    path = Path(item["path"])
    if not path.exists():
        raise HTTPException(404, "Arquivo não encontrado no disco")

    file_size = path.stat().st_size
    range_header = request.headers.get("range")

    if range_header:
        # Parse "bytes=start-end"
        byte_range = range_header.replace("bytes=", "").strip()
        parts = byte_range.split("-")
        start = int(parts[0]) if parts[0] else 0
        end = int(parts[1]) if parts[1] else file_size - 1
        end = min(end, file_size - 1)

        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(end - start + 1),
            "Content-Disposition": f'inline; filename="{item["filename"]}"',
        }
        return StreamingResponse(
            _video_stream(path, start, end),
            status_code=206,
            media_type="video/mp4",
            headers=headers,
        )

    # Resposta completa (download direto)
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(file_size),
        "Content-Disposition": f'attachment; filename="{item["filename"]}"',
    }
    return StreamingResponse(
        _video_stream(path, 0, file_size - 1),
        status_code=200,
        media_type="video/mp4",
        headers=headers,
    )


@router.delete("/images/{image_id}")
def delete_image(image_id: str):
    if not storage.delete_file(image_id, "images"):
        raise HTTPException(404, "Imagem não encontrada")
    return {"deleted": True}


@router.delete("/videos/{video_id}")
def delete_video(video_id: str):
    if not storage.delete_file(video_id, "videos"):
        raise HTTPException(404, "Vídeo não encontrado")
    return {"deleted": True}
