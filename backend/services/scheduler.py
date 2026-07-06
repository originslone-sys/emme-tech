import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

log = logging.getLogger("scheduler")

_scheduler = AsyncIOScheduler(timezone="America/Sao_Paulo")


def get_scheduler() -> AsyncIOScheduler:
    return _scheduler
