import os
import uuid
import json
import aiofiles
from pathlib import Path
from datetime import datetime
from typing import Optional

STORAGE_PATH = Path(os.getenv("STORAGE_PATH", "/data"))
DB_FILE = STORAGE_PATH / "db.json"

DIRS = {
    "uploads": STORAGE_PATH / "uploads",
    "images": STORAGE_PATH / "images",
    "videos": STORAGE_PATH / "videos",
}


def init_storage():
    for dir_path in DIRS.values():
        dir_path.mkdir(parents=True, exist_ok=True)
    if not DB_FILE.exists():
        DB_FILE.write_text(json.dumps({"images": [], "videos": [], "jobs": {}}))


def read_db() -> dict:
    return json.loads(DB_FILE.read_text())


def write_db(data: dict):
    DB_FILE.write_text(json.dumps(data, indent=2, default=str))


async def save_upload(file, category: str) -> tuple[str, str]:
    file_id = str(uuid.uuid4())
    ext = Path(file.filename).suffix.lower()
    filename = f"{file_id}{ext}"
    file_path = DIRS.get(category, DIRS["uploads"]) / filename

    content = await file.read()
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    return file_id, str(file_path)


def add_image(file_id: str, path: str, prompt: str = ""):
    db = read_db()
    db["images"].append({
        "id": file_id,
        "path": path,
        "filename": Path(path).name,
        "prompt": prompt,
        "created_at": datetime.now().isoformat(),
    })
    write_db(db)


def add_video(file_id: str, path: str):
    db = read_db()
    db["videos"].append({
        "id": file_id,
        "path": path,
        "filename": Path(path).name,
        "created_at": datetime.now().isoformat(),
    })
    write_db(db)


def delete_file(file_id: str, file_type: str) -> bool:
    db = read_db()
    items = db.get(file_type, [])
    item = next((i for i in items if i["id"] == file_id), None)
    if not item:
        return False
    path = Path(item["path"])
    if path.exists():
        path.unlink()
    db[file_type] = [i for i in items if i["id"] != file_id]
    write_db(db)
    return True


def save_job(job_id: str, endpoint_id: str, job_type: str, meta: dict = {}):
    db = read_db()
    db["jobs"][job_id] = {
        "endpoint_id": endpoint_id,
        "type": job_type,
        "meta": meta,
        "created_at": datetime.now().isoformat(),
    }
    write_db(db)


def get_job(job_id: str) -> Optional[dict]:
    db = read_db()
    return db["jobs"].get(job_id)
