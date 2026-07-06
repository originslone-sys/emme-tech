import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

log = logging.getLogger("scheduler")

_scheduler = AsyncIOScheduler(timezone="America/Sao_Paulo")


def get_scheduler() -> AsyncIOScheduler:
    return _scheduler


def apply_ig_schedule(config: dict):
    """(Re)agenda os slots de publicação do Instagram conforme a config.

    Distribui posts_per_day e stories_per_day ao longo do dia por intervalo.
    """
    for jid in ("ig_feed", "ig_story"):
        if _scheduler.get_job(jid):
            _scheduler.remove_job(jid)

    if not config.get("enabled"):
        log.info("Automação Instagram desativada — jobs removidos")
        return

    from services import instagram

    ppd = int(config.get("posts_per_day", 0) or 0)
    spd = int(config.get("stories_per_day", 0) or 0)

    if ppd > 0:
        minutes = max(5, round(24 * 60 / ppd))
        _scheduler.add_job(
            instagram.run_slot, "interval", args=["feed", config],
            minutes=minutes, id="ig_feed", replace_existing=True,
            misfire_grace_time=120,
        )
    if spd > 0:
        minutes = max(5, round(24 * 60 / spd))
        _scheduler.add_job(
            instagram.run_slot, "interval", args=["story", config],
            minutes=minutes, id="ig_story", replace_existing=True,
            misfire_grace_time=120,
        )
    log.info("Instagram agendado: %d posts/dia, %d stories/dia", ppd, spd)
