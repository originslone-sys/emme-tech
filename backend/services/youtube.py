import uuid
from pathlib import Path

import yt_dlp

from services import storage


def download(url: str) -> str:
    """Baixa um vídeo do YouTube (ou outra fonte suportada) para uploads e retorna o caminho."""
    vid = str(uuid.uuid4())
    out_tmpl = str(storage.DIRS["uploads"] / f"{vid}.%(ext)s")
    opts = {
        "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
        "outtmpl": out_tmpl,
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.extract_info(url, download=True)

    # O arquivo final pode ter extensão diferente; pega o que foi criado.
    matches = list(storage.DIRS["uploads"].glob(f"{vid}.*"))
    if not matches:
        raise RuntimeError("Falha ao baixar o vídeo")
    return str(matches[0])
