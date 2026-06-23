import os
import random
from pathlib import Path

# Biblioteca de músicas livres de direitos. Estrutura esperada:
#   assets/music/<mood>/*.mp3   (energetic, upbeat, inspirational, calm, dramatic, epic)
# Pode ser sobrescrita pela env MUSIC_DIR (ex: um volume montado).
_DEFAULT_DIR = Path(__file__).resolve().parent.parent / "assets" / "music"
MUSIC_DIR = Path(os.getenv("MUSIC_DIR", str(_DEFAULT_DIR)))

_EXTS = {".mp3", ".m4a", ".aac", ".wav", ".ogg"}


def _tracks_in(folder: Path) -> list[Path]:
    if not folder.exists():
        return []
    return [p for p in folder.iterdir() if p.suffix.lower() in _EXTS]


def pick(mood: str) -> str | None:
    """Retorna o caminho de uma trilha do mood pedido, ou de qualquer trilha
    disponível. Se a biblioteca estiver vazia, retorna None (renderiza sem música)."""
    candidates = _tracks_in(MUSIC_DIR / mood)
    if not candidates:
        # tenta qualquer subpasta de mood, depois a raiz
        for sub in MUSIC_DIR.glob("*"):
            if sub.is_dir():
                candidates += _tracks_in(sub)
        candidates += _tracks_in(MUSIC_DIR)
    if not candidates:
        return None
    return str(random.choice(candidates))
