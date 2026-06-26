import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

log = logging.getLogger("scheduler")

_scheduler = AsyncIOScheduler(timezone="America/Sao_Paulo")


def get_scheduler() -> AsyncIOScheduler:
    return _scheduler


def update_job(config: dict):
    """Atualiza ou remove o job de automação com base na config."""
    if _scheduler.get_job("tiktok_auto"):
        _scheduler.remove_job("tiktok_auto")

    if not config.get("enabled"):
        log.info("Automação desativada — job removido")
        return

    from services import automation

    interval = max(5, int(config.get("interval_minutes", 30)))

    # AsyncIOScheduler executa coroutines async nativamente — não usar create_task
    _scheduler.add_job(
        automation.run_once,
        "interval",
        args=[config],
        minutes=interval,
        id="tiktok_auto",
        replace_existing=True,
        misfire_grace_time=60,
    )
    log.info("Automação ativada: a cada %d min", interval)
