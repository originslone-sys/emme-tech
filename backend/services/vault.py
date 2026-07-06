"""Cofre de mídias da automação Instagram.

Guarda fotos, vídeos e carrosséis que o usuário sobe. A publicação consome um
item (peek -> publica -> remove). Arquivos ficam em DIRS['vault'] e são servidos
publicamente em /files/vault para o Zernio/Instagram baixar.
"""
import uuid
from datetime import datetime
from pathlib import Path

from services import storage

_IMAGE_EXTS = {".jpg", ".jpeg", ".png"}
_VIDEO_EXTS = {".mp4", ".mov"}


def _kind_of(files: list[str]) -> str:
    """Deduz o tipo do item a partir dos arquivos."""
    if len(files) > 1:
        return "carousel"
    ext = Path(files[0]).suffix.lower() if files else ""
    return "video" if ext in _VIDEO_EXTS else "photo"


async def save_item(uploads: list, hint: str = "") -> dict:
    """Salva os arquivos enviados no cofre e registra o item.

    uploads: lista de UploadFile (1 = foto/vídeo, 2+ = carrossel).
    """
    saved: list[str] = []
    for up in uploads:
        ext = Path(up.filename or "").suffix.lower()
        if ext not in _IMAGE_EXTS and ext not in _VIDEO_EXTS:
            continue
        fname = f"{uuid.uuid4().hex}{ext}"
        dest = storage.DIRS["vault"] / fname
        content = await up.read()
        dest.write_bytes(content)
        saved.append(fname)

    if not saved:
        raise ValueError("Nenhum arquivo válido (use JPEG, PNG, MP4 ou MOV)")

    item = {
        "id": str(uuid.uuid4()),
        "kind": _kind_of(saved),
        "files": saved,
        "hint": (hint or "").strip(),
        "created_at": datetime.now().isoformat(),
    }
    storage.add_vault_item(item)
    return item


def list_items() -> list[dict]:
    return storage.list_vault()


def counts() -> dict:
    """Quantos itens de cada tipo há no cofre."""
    c = {"photo": 0, "carousel": 0, "video": 0}
    for it in storage.list_vault():
        c[it.get("kind", "photo")] = c.get(it.get("kind", "photo"), 0) + 1
    return c


def delete_item(item_id: str) -> bool:
    if not storage.get_vault_item(item_id):
        return False
    storage.remove_vault_item(item_id)
    return True


def pick_item(preferred_kinds: list[str]) -> dict | None:
    """Retorna (sem remover) o item mais antigo cujo tipo aparece primeiro na
    ordem de preferência. Ex: ['video','carousel','photo']. None se o cofre
    não tiver nenhum tipo pedido."""
    items = storage.list_vault()
    for kind in preferred_kinds:
        matches = [i for i in items if i.get("kind") == kind]
        if matches:
            matches.sort(key=lambda i: i.get("created_at", ""))
            return matches[0]
    return None


def consume(item_id: str):
    """Remove o item do cofre após publicação bem-sucedida (apaga arquivos)."""
    storage.remove_vault_item(item_id)
