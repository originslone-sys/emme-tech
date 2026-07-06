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
        DB_FILE.write_text(json.dumps({"images": [], "videos": [], "jobs": {}, "character": None}))
    cleanup_uploads()


def cleanup_uploads():
    """Esvazia a pasta de uploads.

    Tudo em uploads/ é intermediário (vídeo de origem, áudio extraído,
    chunks .part, legendas .ass). Os cortes finais ficam em videos/ e as
    imagens em images/, que não tocamos aqui. Chamado no boot para liberar
    espaço — um restart já invalida qualquer upload em andamento.
    """
    up = DIRS["uploads"]
    if not up.exists():
        return
    for p in up.iterdir():
        try:
            if p.is_file():
                p.unlink()
        except OSError:
            pass


def read_db() -> dict:
    try:
        return json.loads(DB_FILE.read_text())
    except (json.JSONDecodeError, FileNotFoundError, OSError):
        return {"images": [], "videos": [], "jobs": {}}


def write_db(data: dict):
    tmp = DB_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, default=str))
    tmp.replace(DB_FILE)


def list_storage() -> dict:
    """Lista os arquivos em cada diretório de storage com tamanho em bytes.

    Útil para administração manual do disco (ver o que ocupa espaço e
    apagar sem esperar deploy).
    """
    result = {}
    total = 0
    for category, dir_path in DIRS.items():
        files = []
        if dir_path.exists():
            for p in sorted(dir_path.iterdir()):
                if not p.is_file():
                    continue
                try:
                    size = p.stat().st_size
                except OSError:
                    size = 0
                files.append({"name": p.name, "size": size})
                total += size
        result[category] = files
    return {"dirs": result, "total": total}


def delete_storage_file(category: str, name: str) -> bool:
    """Apaga um arquivo bruto de um diretório de storage.

    Valida category e name para evitar path traversal.
    """
    if category not in DIRS:
        return False
    if "/" in name or "\\" in name or ".." in name:
        return False
    path = DIRS[category] / name
    if not path.exists() or not path.is_file():
        return False
    # Garante que o caminho resolvido continua dentro do diretório esperado.
    try:
        path.resolve().relative_to(DIRS[category].resolve())
    except ValueError:
        return False
    path.unlink()
    return True


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


def add_video(file_id: str, path: str, label: str = "", meta: Optional[dict] = None):
    db = read_db()
    entry = {
        "id": file_id,
        "path": path,
        "filename": Path(path).name,
        "label": label,
        "created_at": datetime.now().isoformat(),
    }
    if meta:
        entry.update(meta)
    db["videos"].append(entry)
    write_db(db)


async def save_upload_temp(file) -> str:
    """Salva um upload na pasta de uploads e retorna apenas o caminho."""
    _, path = await save_upload(file, "uploads")
    return path


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


def update_job(job_id: str, meta_updates: dict):
    db = read_db()
    job = db["jobs"].get(job_id)
    if not job:
        return
    job["meta"].update(meta_updates)
    write_db(db)


def get_job(job_id: str) -> Optional[dict]:
    db = read_db()
    return db["jobs"].get(job_id)


# ---------- Personagem de IA generativa (único por instância) ----------

def get_character() -> Optional[dict]:
    db = read_db()
    return db.get("character")


def save_character(data: dict):
    db = read_db()
    db["character"] = data
    write_db(db)


def delete_character():
    db = read_db()
    char = db.get("character")
    if char:
        # Apaga a imagem de referência do disco
        ref = char.get("reference_image")
        if ref:
            p = Path(ref)
            if p.exists():
                p.unlink(missing_ok=True)
        # Apaga imagens geradas associadas
        for img_id in char.get("generated_image_ids", []):
            for f in DIRS["images"].glob(f"{img_id}.*"):
                f.unlink(missing_ok=True)
    db["character"] = None
    write_db(db)
