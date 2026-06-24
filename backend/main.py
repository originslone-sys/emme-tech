from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from routers import editor, library, clips, viral
from services.storage import init_storage, DIRS

# Garante que os diretórios existem antes de montar os estáticos
init_storage()

app = FastAPI(title="Emme Video Editor API")

# Libera CORS para qualquer origem. O app não usa autenticação por cookie,
# então não precisamos de credenciais — e com allow_credentials=False o
# wildcard "*" é válido para origem, métodos e headers (inclusive nos
# preflights OPTIONS dos uploads em chunks).
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

# Serve os uploads para o RunPod baixar via URL pública
app.mount("/files/uploads", StaticFiles(directory=str(DIRS["uploads"])), name="uploads")
# Serve os vídeos como estáticos: o StaticFiles do Starlette faz streaming
# assíncrono com suporte nativo a Range, bem mais eficiente que servir o
# arquivo por uma rota Python (usado para o player da Biblioteca).
app.mount("/files/videos", StaticFiles(directory=str(DIRS["videos"])), name="videos")


@app.get("/health")
def health():
    return {"status": "ok"}
