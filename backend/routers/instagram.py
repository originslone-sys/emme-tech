from pathlib import Path
from typing import List

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from services import instagram, storage, vault
from services.scheduler import apply_ig_schedule, get_scheduler

router = APIRouter()


class Persona(BaseModel):
    name: str = ""
    vibe: str = ""
    themes: str = ""
    language: str = "Português"


class IgConfig(BaseModel):
    enabled: bool = False
    posts_per_day: int = 2
    stories_per_day: int = 1
    account_id: str = ""
    is_ai_generated: bool = False
    persona: Persona = Persona()


@router.get("/config")
def get_config():
    cfg = storage.get_ig_config()
    return cfg if cfg else IgConfig().model_dump()


@router.post("/config")
def save_config(config: IgConfig):
    cfg = config.model_dump()
    storage.save_ig_config(cfg)
    apply_ig_schedule(cfg)
    return {"saved": True, "enabled": cfg["enabled"]}


@router.get("/vault")
def list_vault():
    items = vault.list_items()
    return {
        "items": [
            {
                "id": it["id"],
                "kind": it.get("kind"),
                "hint": it.get("hint", ""),
                "created_at": it.get("created_at"),
                "files": [f"/files/vault/{f}" for f in it.get("files", [])],
            }
            for it in items
        ],
        "counts": vault.counts(),
    }


@router.post("/vault")
async def upload_vault(
    files: List[UploadFile] = File(...),
    hint: str = Form(""),
):
    if not files:
        raise HTTPException(400, "Envie ao menos um arquivo")
    if len(files) > 10:
        raise HTTPException(400, "Máximo de 10 mídias por item (carrossel)")
    try:
        item = await vault.save_item(files, hint)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"item": item}


@router.delete("/vault/{item_id}")
def delete_vault(item_id: str):
    if not vault.delete_item(item_id):
        raise HTTPException(404, "Item não encontrado")
    return {"deleted": True}


@router.post("/post-now")
async def post_now(background_tasks: BackgroundTasks, slot: str = Form("feed")):
    if slot not in ("feed", "story"):
        raise HTTPException(400, "slot deve ser 'feed' ou 'story'")
    if instagram.is_running():
        raise HTTPException(409, "Já existe uma publicação em andamento. Aguarde.")
    cfg = storage.get_ig_config()
    if not cfg:
        raise HTTPException(400, "Configure a automação antes de publicar.")
    background_tasks.add_task(instagram.run_slot, slot, cfg)
    return {"started": True, "slot": slot}


@router.get("/status")
def status():
    sched = get_scheduler()
    feed = sched.get_job("ig_feed")
    story = sched.get_job("ig_story")
    return {
        "running": instagram.is_running(),
        "next_feed": feed.next_run_time.isoformat() if feed and feed.next_run_time else None,
        "next_story": story.next_run_time.isoformat() if story and story.next_run_time else None,
    }


@router.get("/history")
def history():
    return {"history": storage.get_ig_history()}
