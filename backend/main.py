from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from routers import editor, generative, instagram, library, clips, viral
from services.storage import init_storage, DIRS, get_ig_config
from services.scheduler import get_scheduler, apply_ig_schedule


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_storage()
    scheduler = get_scheduler()
    scheduler.start()
    cfg = get_ig_config()
    if cfg:
        apply_ig_schedule(cfg)
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="Emme Video Editor API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(editor.router, prefix="/api/editor", tags=["editor"])
app.include_router(clips.router, prefix="/api/clips", tags=["clips"])
app.include_router(viral.router, prefix="/api/viral", tags=["viral"])
app.include_router(library.router, prefix="/api/library", tags=["library"])
app.include_router(generative.router, prefix="/api/generative", tags=["generative"])
app.include_router(instagram.router, prefix="/api/instagram", tags=["instagram"])

app.mount("/files/uploads", StaticFiles(directory=str(DIRS["uploads"])), name="uploads")
app.mount("/files/videos", StaticFiles(directory=str(DIRS["videos"])), name="videos")
app.mount("/files/images", StaticFiles(directory=str(DIRS["images"])), name="images")
app.mount("/files/vault", StaticFiles(directory=str(DIRS["vault"])), name="vault")


@app.get("/health")
def health():
    return {"status": "ok"}
