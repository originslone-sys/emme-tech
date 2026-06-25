import httpx
import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
from pathlib import Path

from services import storage, deepseek, openrouter

router = APIRouter()


class CharacterFields(BaseModel):
    name: str
    sex: str
    age: str
    ethnicity: str
    hair: str
    eyes: str
    traits: str = ""
    tone: str = ""


class ConfirmCharacter(BaseModel):
    image_id: str


class SceneFields(BaseModel):
    scenario: str = ""
    outfit: str = ""
    pose: str = ""
    expression: str = ""
    lighting: str = ""


class UpdateReference(BaseModel):
    image_id: str


@router.get("/character")
def get_character():
    char = storage.get_character()
    if not char:
        return {"character": None}
    # Injeta URL pública da imagem de referência
    ref_path = char.get("reference_image")
    if ref_path:
        filename = Path(ref_path).name
        char = {**char, "reference_url": f"/files/images/{filename}"}
    return {"character": char}


@router.post("/character")
async def create_character(fields: CharacterFields):
    """Fase 1a: gera o anchor_prompt via DeepSeek e as 6 imagens de fundação."""
    existing = storage.get_character()
    if existing:
        raise HTTPException(400, "Já existe um personagem criado. Delete-o antes de criar um novo.")

    sheet = await deepseek.generate_character_sheet(fields.model_dump())
    anchor = sheet["anchor_prompt"]
    foundation = sheet["foundation_scene"]

    # Monta prompt de fundação: rosto frontal, fundo neutro
    foundation_prompt = f"{anchor}, {foundation}" if foundation else anchor

    images = await openrouter.generate_images(
        prompt=foundation_prompt,
        count=6,
        reference_url=None,
        aspect_ratio="1:1",
        image_size="1K",
    )
    if not images:
        raise HTTPException(500, "A geração de imagens falhou. Verifique a chave OPENROUTER_API_KEY.")

    # Salva as imagens na biblioteca e guarda os IDs
    image_ids = []
    for img in images:
        storage.add_image(img["id"], img["path"])
        image_ids.append(img["id"])

    # Salva personagem em estado "pendente" (aguardando escolha da referência)
    storage.save_character({
        "name": fields.name,
        "fields": fields.model_dump(),
        "anchor_prompt": anchor,
        "display_summary": sheet.get("display_summary", ""),
        "reference_image": None,
        "generated_image_ids": image_ids,
        "pending_selection": True,
        "created_at": datetime.now().isoformat(),
    })

    return {
        "status": "pending_selection",
        "images": [
            {
                "id": img["id"],
                "url": f"/files/images/{img['filename']}",
            }
            for img in images
        ],
    }


@router.post("/character/confirm")
def confirm_character(body: ConfirmCharacter):
    """Fase 1b: usuário escolhe a melhor imagem — ela vira a referência mestre."""
    char = storage.get_character()
    if not char:
        raise HTTPException(404, "Nenhum personagem encontrado")

    db = storage.read_db()
    img = next((i for i in db.get("images", []) if i["id"] == body.image_id), None)
    if not img:
        raise HTTPException(404, "Imagem não encontrada")

    char["reference_image"] = img["path"]
    char["pending_selection"] = False
    storage.save_character(char)

    filename = Path(img["path"]).name
    return {
        "status": "confirmed",
        "reference_url": f"/files/images/{filename}",
    }


@router.post("/character/reset")
def reset_character():
    """Remove o personagem atual e apaga as imagens geradas."""
    storage.delete_character()
    return {"deleted": True}


@router.get("/debug")
async def debug_openrouter():
    """Testa conexão com OpenRouter e lista modelos de imagem disponíveis."""
    key = os.getenv("OPENROUTER_API_KEY", "")
    if not key:
        return {"error": "OPENROUTER_API_KEY não configurada"}

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get("https://openrouter.ai/api/v1/models", headers=headers)
            if not resp.is_success:
                return {"error": f"OpenRouter retornou {resp.status_code}", "body": resp.text[:500]}
            data = resp.json()
            image_models = [
                m["id"] for m in data.get("data", [])
                if "image" in str(m.get("architecture", {}).get("modality", ""))
                or "flux" in m["id"].lower()
                or "imagen" in m["id"].lower()
                or "gemini" in m["id"].lower() and "image" in m["id"].lower()
            ]
            return {
                "current_model": openrouter._IMAGE_MODEL,
                "key_prefix": key[:8] + "...",
                "image_models": image_models[:30],
                "total_models": len(data.get("data", [])),
            }
    except Exception as e:
        return {"error": str(e)}


@router.post("/scene")
async def generate_scene(fields: SceneFields):
    """Gera 4 imagens de uma nova cena usando o personagem salvo como referência."""
    char = storage.get_character()
    if not char:
        raise HTTPException(400, "Crie um personagem antes de gerar cenas.")
    if char.get("pending_selection"):
        raise HTTPException(400, "Confirme a imagem de referência do personagem antes de gerar cenas.")

    anchor = char["anchor_prompt"]
    prompt = deepseek.build_scene_prompt(anchor, fields.model_dump())

    # URL pública da referência para o FLUX usar como âncora de identidade
    ref_path = char.get("reference_image")
    ref_url = None
    if ref_path:
        from services.storage import DIRS
        import os
        backend_url = os.getenv("BACKEND_URL", "")
        filename = Path(ref_path).name
        ref_url = f"{backend_url}/files/images/{filename}" if backend_url else None

    images = await openrouter.generate_images(
        prompt=prompt,
        count=4,
        reference_url=ref_url,
        aspect_ratio="9:16",
        image_size="1K",
    )
    if not images:
        raise HTTPException(500, "A geração de imagens falhou.")

    image_ids = char.get("generated_image_ids", [])
    for img in images:
        storage.add_image(img["id"], img["path"])
        image_ids.append(img["id"])

    char["generated_image_ids"] = image_ids
    storage.save_character(char)

    return {
        "images": [
            {"id": img["id"], "url": f"/files/images/{img['filename']}"}
            for img in images
        ]
    }


@router.patch("/character/reference")
def update_reference(body: UpdateReference):
    """Atualiza a referência mestre com uma imagem gerada em cena."""
    char = storage.get_character()
    if not char:
        raise HTTPException(404, "Nenhum personagem encontrado")

    db = storage.read_db()
    img = next((i for i in db.get("images", []) if i["id"] == body.image_id), None)
    if not img:
        raise HTTPException(404, "Imagem não encontrada")

    char["reference_image"] = img["path"]
    storage.save_character(char)

    filename = Path(img["path"]).name
    return {"reference_url": f"/files/images/{filename}"}
