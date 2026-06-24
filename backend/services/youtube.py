import os
import tempfile
import uuid
from pathlib import Path

import yt_dlp

from services import storage

_COOKIES_FILE = os.getenv("YOUTUBE_COOKIES_FILE", "").strip()
_PROXY = os.getenv("YOUTUBE_PROXY", "").strip()


def _resolve_cookies_file() -> str:
    """Resolve o arquivo de cookies a ser usado pelo yt-dlp.

    Prioridade:
    1. YOUTUBE_COOKIES_FILE — caminho de um arquivo já existente no disco.
    2. YOUTUBE_COOKIES — conteúdo do cookies.txt colado direto na env var
       (prático no Railway, que tem disco efêmero). Gravamos num arquivo
       temporário no boot e usamos ele.
    """
    if _COOKIES_FILE and Path(_COOKIES_FILE).exists():
        return _COOKIES_FILE

    raw = os.getenv("YOUTUBE_COOKIES", "")
    if raw.strip():
        # \n literais coladas no painel viram quebras de linha reais
        content = raw.replace("\\n", "\n")
        path = Path(tempfile.gettempdir()) / "yt_cookies.txt"
        path.write_text(content)
        return str(path)

    return ""


# Resolvido uma vez no import (env vars não mudam em runtime).
_COOKIES_RESOLVED = _resolve_cookies_file()

# Clientes do YouTube a tentar em ordem (android/ios são menos bloqueados em
# IPs de datacenter do que o client "web").
_CLIENT_ATTEMPTS = [
    ["android", "ios", "web"],
    ["ios"],
    ["web"],
]

# IPs públicos brasileiros usados no X-Forwarded-For para tentar contornar
# restrição geográfica a nível de header (não funciona quando o YouTube
# verifica o IP real da conexão — nesse caso só proxy/VPN resolve).
_BR_IPS = ["189.40.0.1", "177.71.0.1", "200.160.0.1", "186.192.0.1"]


def _base_opts(out_tmpl: str, clients: list[str], xff_ip: str | None = None) -> dict:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
    }
    if xff_ip:
        headers["X-Forwarded-For"] = xff_ip

    opts = {
        # Seletor tolerante: tenta vídeo+áudio até 1080p, mas cai para
        # qualquer combinação ou formato único disponível. O último "/b"
        # garante que sempre pega algo, mesmo quando o client expõe poucos
        # formatos (evita "Requested format is not available").
        "format": (
            "bv*[height<=1080]+ba/b[height<=1080]/"
            "bv*+ba/b/bestvideo+bestaudio/best"
        ),
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
        "http_headers": headers,
    }
    if _COOKIES_RESOLVED:
        opts["cookiefile"] = _COOKIES_RESOLVED
    if _PROXY:
        opts["proxy"] = _PROXY
    return opts


def _is_bot_error(msg: str) -> bool:
    m = msg.lower()
    return (
        "sign in to confirm" in m
        or "not a bot" in m
        or "confirm you're not a bot" in m
        or ("cookies" in m and "bot" in m)
    )


def _is_geo_error(msg: str) -> bool:
    m = msg.lower()
    return (
        "not available in your country" in m
        or "uploader has not made this video available" in m
        or "geo" in m and ("restrict" in m or "block" in m)
    )


def download(url: str) -> str:
    """Baixa um vídeo do YouTube e retorna o caminho local.

    Quando cookies estão configurados usa o client "web" (único que aceita
    cookies de navegador). Sem cookies tenta android/ios/web com geo_bypass.
    """
    vid = str(uuid.uuid4())
    out_tmpl = str(storage.DIRS["uploads"] / f"{vid}.%(ext)s")

    # Cookies de navegador só funcionam com o client web.
    # android/ios usam OAuth — misturar com cookies de browser causa rejeição.
    if _COOKIES_RESOLVED:
        attempts = [(["web"], None)]
    else:
        attempts = [(clients, ip)
                    for clients in _CLIENT_ATTEMPTS
                    for ip in ([None] + _BR_IPS)]

    errors: list[str] = []
    bot_blocked = False
    geo_blocked = False

    for clients, xff in attempts:
        try:
            with yt_dlp.YoutubeDL(_base_opts(out_tmpl, clients, xff)) as ydl:
                ydl.extract_info(url, download=True)
            matches = list(storage.DIRS["uploads"].glob(f"{vid}.*"))
            if matches:
                return str(matches[0])
        except yt_dlp.utils.DownloadError as e:
            msg = str(e)
            errors.append(msg)
            if _is_bot_error(msg):
                bot_blocked = True
            if _is_geo_error(msg):
                geo_blocked = True
                # Restrição geográfica real — X-Forwarded-For não vai resolver,
                # não adianta continuar tentando com outros IPs.
                break
            for p in storage.DIRS["uploads"].glob(f"{vid}.*"):
                p.unlink(missing_ok=True)
        except Exception as e:  # noqa: BLE001
            errors.append(str(e))
            for p in storage.DIRS["uploads"].glob(f"{vid}.*"):
                p.unlink(missing_ok=True)

    if geo_blocked:
        proxy_hint = (
            " Configure a variável YOUTUBE_PROXY no Railway com um proxy brasileiro "
            "(ex: socks5://user:pass@host:port) para baixar este vídeo."
            if not _PROXY else
            " O proxy configurado (YOUTUBE_PROXY) também não está funcionando — "
            "verifique se é um proxy com IP do Brasil."
        )
        raise RuntimeError(
            "Este vídeo está bloqueado para o país onde o servidor está hospedado. "
            "O YouTube restringe o acesso com base no IP real do servidor, e "
            "contornar com X-Forwarded-For não funciona aqui." + proxy_hint
        )

    if bot_blocked:
        hint = (
            " Cole o conteúdo do cookies.txt na variável YOUTUBE_COOKIES no Railway "
            "(exporte com a extensão 'Get cookies.txt' do seu navegador logado no YouTube)."
            if not _COOKIES_RESOLVED else
            " Os cookies configurados não foram aceitos — exporte cookies novos "
            "(logado no YouTube) e atualize a variável YOUTUBE_COOKIES."
        )
        raise RuntimeError(
            "O YouTube exigiu verificação anti-bot." + hint
        )

    last = errors[-1] if errors else "erro desconhecido"
    raise RuntimeError(f"Não foi possível baixar o vídeo do YouTube: {last}")
