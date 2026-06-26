from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from services import automation, storage
from services.scheduler import update_job

router = APIRouter()


class AutomationConfig(BaseModel):
    enabled: bool = False
    interval_minutes: int = 30
    voice: str = "feminina"
    tiktok_account_id: str = ""
    auto_publish: bool = False


@router.get("/config")
def get_config():
    cfg = storage.get_automation_config()
    return cfg if cfg else AutomationConfig().model_dump()


@router.post("/config")
def save_config(config: AutomationConfig):
    cfg = config.model_dump()
    storage.save_automation_config(cfg)
    update_job(cfg)
    return {"saved": True, "enabled": cfg["enabled"]}


@router.post("/run")
async def run_now(background_tasks: BackgroundTasks):
    if automation.is_running():
        raise HTTPException(409, "Já existe um ciclo em execução. Aguarde.")
    config = storage.get_automation_config()
    if not config:
        raise HTTPException(400, "Configure a automação antes de executar.")
    background_tasks.add_task(automation.run_once, config)
    return {"started": True}


@router.get("/status")
def get_status():
    from services.scheduler import get_scheduler
    sched = get_scheduler()
    job = sched.get_job("tiktok_auto")
    next_run = job.next_run_time.isoformat() if job and job.next_run_time else None
    return {
        "running": automation.is_running(),
        "scheduler_active": job is not None,
        "next_run": next_run,
    }


@router.get("/history")
def get_history():
    return {"history": storage.get_automation_history()}


@router.delete("/history")
def clear_history():
    from services.storage import write_db, read_db
    db = read_db()
    db["automation_history"] = []
    write_db(db)
    return {"cleared": True}
