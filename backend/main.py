from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from routers import editor, library, clips
from services.storage import init_storage, DIRS

# Garante que os diretórios existem antes de montar os estáticos
init_storage()

app = FastAPI(title="Emme Video Editor API")

_frontend_url = os.getenv("FRONTEND_URL", "")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[_frontend_url] if _frontend_url else ["*"],
    allow_credentials=bool(_frontend_url),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(editor.router, prefix="/api/editor", tags=["editor"])
app.include_router(clips.router, prefix="/api/clips", tags=["clips"])
app.include_router(library.router, prefix="/api/library", tags=["library"])

# Serve os uploads para o RunPod baixar via URL pública
app.mount("/files/uploads", StaticFiles(directory=str(DIRS["uploads"])), name="uploads")


@app.get("/health")
def health():
    return {"status": "ok"}
