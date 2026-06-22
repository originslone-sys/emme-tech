from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path

from services import storage

router = APIRouter()


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
def download_video(video_id: str):
    db = storage.read_db()
    item = next((i for i in db["videos"] if i["id"] == video_id), None)
    if not item:
        raise HTTPException(404, "Vídeo não encontrado")
    path = Path(item["path"])
    if not path.exists():
        raise HTTPException(404, "Arquivo não encontrado no disco")
    return FileResponse(str(path), media_type="video/mp4", filename=item["filename"])


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
