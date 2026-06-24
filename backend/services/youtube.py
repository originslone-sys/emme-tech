import os
import uuid
from pathlib import Path

import yt_dlp

from services import storage

# Em servidores de datacenter (fora do Brasil), o YouTube costuma exigir
# verificação anti-bot. Estas estratégias ajudam a contornar:
#  - tentar diferentes "player clients" (android/ios costumam ser menos
#    bloqueados que o web em IPs de nuvem);
#  - usar cookies se fornecidos via env (YOUTUBE_COOKIES_FILE);
#  - tentar de novo automaticamente.
_COOKIES_FILE = os.getenv("YOUTUBE_COOKIES_FILE", "").strip()
_PROXY = os.getenv("YOUTUBE_PROXY", "").strip()

# Ordem de tentativa dos clients do YouTube. android/ios passam por checagens
# anti-bot que bloqueiam o client "web" em IPs de datacenter.
_CLIENT_ATTEMPTS = [
    ["android", "ios", "web"],
    ["ios"],
    ["web"],
]


def _base_opts(out_tmpl: str, clients: list[str]) -> dict:
    opts = {
        "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
        "outtmpl": out_tmpl,
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "geo_bypass": True,
        "geo_bypass_country": "BR",
        "retries": 5,
        "fragment_retries": 5,
        "concurrent_fragment_downloads": 4,
        "socket_timeout": 30,
        "extractor_args": {"youtube": {"player_client": clients}},
        # Finge ser um navegador real para reduzir bloqueios.
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        },
    }
    if _COOKIES_FILE and Path(_COOKIES_FILE).exists():
        opts["cookiefile"] = _COOKIES_FILE
    if _PROXY:
        opts["proxy"] = _PROXY
    return opts


def _is_bot_error(msg: str) -> bool:
    m = msg.lower()
    return (
        "sign in to confirm" in m
        or "not a bot" in m
        or "confirm you're not a bot" in m
        or "cookies" in m and "bot" in m
    )


def download(url: str) -> str:
    """Baixa um vídeo do YouTube (ou outra fonte suportada) e retorna o caminho.

    Tenta múltiplos clients do YouTube para contornar a verificação anti-bot
    comum em servidores de nuvem fora do Brasil.
    """
    vid = str(uuid.uuid4())
    out_tmpl = str(storage.DIRS["uploads"] / f"{vid}.%(ext)s")

    last_err: Exception | None = None
    bot_blocked = False
    for clients in _CLIENT_ATTEMPTS:
        try:
            with yt_dlp.YoutubeDL(_base_opts(out_tmpl, clients)) as ydl:
                ydl.extract_info(url, download=True)
            matches = list(storage.DIRS["uploads"].glob(f"{vid}.*"))
            if matches:
                return str(matches[0])
            last_err = RuntimeError("Falha ao baixar o vídeo")
        except yt_dlp.utils.DownloadError as e:
            last_err = e
            if _is_bot_error(str(e)):
                bot_blocked = True
            # limpa qualquer arquivo parcial antes da próxima tentativa
            for p in storage.DIRS["uploads"].glob(f"{vid}.*"):
                p.unlink(missing_ok=True)
            continue
        except Exception as e:  # noqa: BLE001
            last_err = e
            continue

    if bot_blocked:
        raise RuntimeError(
            "O YouTube bloqueou o download neste servidor (verificação anti-bot). "
            "Configure a variável YOUTUBE_COOKIES_FILE com um arquivo de cookies "
            "exportado do navegador para liberar."
        )
    raise RuntimeError(f"Não foi possível baixar o vídeo do YouTube: {last_err}")
