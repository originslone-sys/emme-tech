import os
import random
import uuid
from pathlib import Path

import httpx

# Biblioteca de músicas livres de direitos. Estrutura esperada:
#   assets/music/<mood>/*.mp3   (energetic, upbeat, inspirational, calm, dramatic, epic)
# Pode ser sobrescrita pela env MUSIC_DIR (ex: um volume montado).
_DEFAULT_DIR = Path(__file__).resolve().parent.parent / "assets" / "music"
MUSIC_DIR = Path(os.getenv("MUSIC_DIR", str(_DEFAULT_DIR)))

_EXTS = {".mp3", ".m4a", ".aac", ".wav", ".ogg"}

# ---------- Eleven Music (geração de trilha por IA) ----------
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
_EL_MUSIC_URL = "https://api.elevenlabs.io/v1/music"
_EL_MUSIC_MODEL = "music_v2"

# Prompt instrumental por clima — sem vocais, pensado para fundo de vídeo curto.
_MOOD_PROMPT = {
    "energetic": "An energetic, high-tempo instrumental with driving drums and bright "
                 "synths, perfect for a fast-paced social media video. Instrumental only, no vocals.",
    "upbeat": "An upbeat, happy and positive instrumental with a catchy groove, light "
              "percussion and warm chords. Instrumental only, no vocals.",
    "inspirational": "An inspirational, uplifting instrumental with emotional piano, "
                     "swelling strings and a hopeful build. Instrumental only, no vocals.",
    "calm": "A calm, relaxing ambient instrumental with soft pads, gentle piano and a "
            "slow soothing tempo. Instrumental only, no vocals.",
    "dramatic": "A dramatic, tense cinematic instrumental with deep strings, building "
                "percussion and emotional intensity. Instrumental only, no vocals.",
    "epic": "An epic, powerful cinematic instrumental with huge orchestral drums, brass "
            "and a triumphant feel. Instrumental only, no vocals.",
}


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


def has_library() -> bool:
    """True se existe ao menos uma trilha em qualquer mood."""
    for sub in MUSIC_DIR.glob("*"):
        if sub.is_dir() and _tracks_in(sub):
            return True
    return bool(_tracks_in(MUSIC_DIR))


async def generate(mood: str, length_ms: int = 30000) -> str | None:
    """Gera uma trilha via Eleven Music e SALVA na biblioteca local (MUSIC_DIR/<mood>/),
    para poder ser reaproveitada em outros vídeos. Retorna o caminho ou None."""
    if not ELEVENLABS_API_KEY:
        return None
    prompt = _MOOD_PROMPT.get(mood, _MOOD_PROMPT["energetic"])
    length_ms = max(3000, min(length_ms, 300000))
    payload = {
        "prompt": prompt,
        "music_length_ms": length_ms,
        "model_id": _EL_MUSIC_MODEL,
        "force_instrumental": True,
    }
    headers = {"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=180) as client:
        resp = await client.post(_EL_MUSIC_URL, json=payload, headers=headers)
        if resp.status_code == 404:  # alguns deploys expõem /compose
            resp = await client.post(_EL_MUSIC_URL + "/compose", json=payload, headers=headers)
        if resp.status_code >= 400:
            raise RuntimeError(f"Eleven Music {resp.status_code}: {resp.text[:300]}")
        dest_dir = MUSIC_DIR / mood
        dest_dir.mkdir(parents=True, exist_ok=True)
        path = dest_dir / f"gen_{uuid.uuid4()}.mp3"
        path.write_bytes(resp.content)
        return str(path)
