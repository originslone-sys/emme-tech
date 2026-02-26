#!/usr/bin/env python3
"""
local_agent.py — Agente local do Video Downloader
Roda yt-dlp na sua máquina e expõe uma API REST para o app web.

Uso:
  python3 local_agent.py     (Mac / Linux)
  python  local_agent.py     (Windows)

Requisitos:
  pip install yt-dlp         (ou: pipx install yt-dlp / winget install yt-dlp)
"""

import json
import os
import subprocess
import sys
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse, unquote_plus, urlencode, urlunparse

PORT = 9999
DOWNLOAD_DIR = Path.home() / "Downloads" / "VideoDownloader"

# Populados em main() para evitar subprocess no hot path das requests
_YTDLP_BIN: str = ""
_YTDLP_VERSION: str = ""
_COOKIE_BROWSERS: list[str] = []  # browsers detectados em main(), em ordem de preferência


# ── Helpers ────────────────────────────────────────────────────────────────────

# ── URL helpers ────────────────────────────────────────────────────────────────

# Parâmetros de rastreamento que não fazem parte da URL real do conteúdo
_TRACKING_PARAMS = frozenset({
    "igsh", "igshid", "hl",                          # Instagram
    "fbclid", "mibextid", "__cft__", "__tn__",       # Facebook
    "rdid", "share_url",                              # Facebook share redirect
    "_rdc", "_rdr",
    "utm_source", "utm_medium", "utm_campaign",      # UTM genérico
    "utm_term", "utm_content",
})


def normalize_url(url: str) -> str:
    """Remove parâmetros de rastreamento e normaliza URLs para o yt-dlp."""
    try:
        p = urlparse(url)
        host = (p.hostname or "").lower()
        # Instagram: qualquer query string é rastreamento — remove tudo
        if "instagram.com" in host:
            return urlunparse(p._replace(query="", fragment=""))
        # Outros: remove apenas os params de rastreamento conhecidos
        if p.query:
            qs = {k: v[0] for k, v in parse_qs(p.query).items()
                  if k.lower() not in _TRACKING_PARAMS}
            return urlunparse(p._replace(query=urlencode(qs) if qs else "", fragment=""))
    except Exception:
        pass
    return url


def _canonicalize_facebook_url(url: str) -> str:
    """Converte URLs de perfil/página do Facebook para o formato de aba de vídeos
    suportado pelo yt-dlp (FacebookUserVideosIE).

    facebook.com/PAGE/              → facebook.com/PAGE/videos/
    facebook.com/profile.php?id=X   → facebook.com/X/videos/
    URLs que já têm /videos/ ou são de vídeo específico → sem alteração.
    """
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if "facebook.com" not in host and "fb.com" not in host:
        return url

    # URLs que já apontam para conteúdo específico — não mexer
    path = parsed.path
    specific = ("/videos", "/video", "/reel", "/reels", "/watch", "/posts", "/photos")
    if any(s in path for s in specific):
        return url
    if parse_qs(parsed.query).get("v"):  # watch?v=...
        return url

    # profile.php?id=XXXXX → /XXXXX/videos/ (format que o yt-dlp reconhece)
    if "profile.php" in path:
        qs = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        profile_id = qs.get("id", "")
        if profile_id:
            new_url = urlunparse(parsed._replace(path=f"/{profile_id}/videos/", query=""))
            print(f"[facebook] profile.php → aba de vídeos: {new_url}")
            return new_url
        return url

    # /PAGE ou /PAGE/ (único segmento) → /PAGE/videos/
    segments = [s for s in path.split("/") if s]
    if len(segments) == 1:
        new_url = urlunparse(parsed._replace(path=f"/{segments[0]}/videos/"))
        print(f"[facebook] Ajustado para aba de vídeos: {new_url}")
        return new_url

    return url


def _extra_args_for_url(url: str) -> list[str]:
    """Retorna flags extras do yt-dlp específicas por plataforma."""
    host = (urlparse(url).hostname or "").lower()
    if "instagram.com" in host:
        # Instagram exige este header para a Graph API — sem ele retorna
        # "Unable to extract data" mesmo com cookies válidos.
        return ["--add-headers", "X-IG-App-ID:936619743392459"]
    return []


def _resolve_facebook_share(url: str) -> str:
    """Resolve facebook.com/share/... seguindo o redirect HTTP para obter
    a URL real do conteúdo, depois limpa parâmetros de rastreamento."""
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if "facebook.com" not in host and "fb.com" not in host:
        return url
    if not parsed.path.startswith("/share"):
        return url
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) "
                "Gecko/20100101 Firefox/124.0"
            ),
            "Accept-Language": "pt-BR,pt;q=0.9",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            final = resp.url
        # Redirecionar para login significa conteúdo privado — retorna original
        if "/login" in final or "login.php" in final:
            print(f"[resolve] Redireciona para login — conteúdo privado: {url}")
            return url
        resolved = normalize_url(final)
        print(f"[resolve] {url}\n       → {resolved}")
        return resolved
    except Exception as exc:
        print(f"[resolve] Erro ao seguir redirect de {url}: {exc}")
        return url


def _needs_cookies(url: str) -> bool:
    """Facebook e Instagram exigem cookies de sessão para acessar conteúdo."""
    host = (urlparse(url).hostname or "").lower()
    return any(h in host for h in ("facebook.com", "fb.com", "instagram.com"))


def detect_cookie_browsers() -> list[str]:
    """Retorna todos os browsers instalados em ordem de preferência para cookies.

    No Windows o Firefox vem primeiro: Chrome 127+ usa App-Bound Encryption
    que impede leitura externa dos cookies mesmo com o browser fechado.
    """
    home = Path.home()
    if sys.platform == "win32":
        local   = Path(os.environ.get("LOCALAPPDATA", str(home)))
        roaming = Path(os.environ.get("APPDATA",      str(home)))
        candidates = [
            # Firefox primeiro no Windows — não tem App-Bound Encryption
            ("firefox",  roaming / "Mozilla/Firefox/Profiles"),
            ("chrome",   local   / "Google/Chrome/User Data"),
            ("edge",     local   / "Microsoft/Edge/User Data"),
            ("brave",    local   / "BraveSoftware/Brave-Browser/User Data"),
            ("opera",    roaming / "Opera Software/Opera Stable"),
            ("vivaldi",  local   / "Vivaldi/User Data"),
        ]
    elif sys.platform == "darwin":
        lib = home / "Library/Application Support"
        candidates = [
            ("chrome",  lib / "Google/Chrome"),
            ("brave",   lib / "BraveSoftware/Brave-Browser"),
            ("edge",    lib / "Microsoft Edge"),
            ("firefox", home / "Library/Application Support/Firefox/Profiles"),
            ("safari",  home / "Library/Safari"),
        ]
    else:  # Linux
        cfg = home / ".config"
        candidates = [
            ("chrome",    cfg / "google-chrome"),
            ("chromium",  cfg / "chromium"),
            ("brave",     cfg / "BraveSoftware/Brave-Browser"),
            ("edge",      cfg / "microsoft-edge"),
            ("firefox",   home / ".mozilla/firefox"),
            ("opera",     cfg / "opera"),
            ("vivaldi",   cfg / "vivaldi"),
        ]
    return [name for name, path in candidates if path.exists()]


def find_ytdlp() -> str:
    """Retorna o executável yt-dlp disponível ou '' se não encontrado."""
    candidates = ["yt-dlp", "yt-dlp.exe", "python3 -m yt_dlp", "python -m yt_dlp"]
    for cmd in candidates:
        try:
            parts = cmd.split()
            r = subprocess.run(parts + ["--version"], capture_output=True, timeout=5)
            if r.returncode == 0:
                return cmd
        except (FileNotFoundError, subprocess.TimeoutExpired, PermissionError):
            pass
    return ""


def ytdlp_cmd(base: str) -> list[str]:
    """Converte string de comando yt-dlp em lista de args."""
    return base.split()


# Marcadores que indicam falha de cookies do browser, não de conteúdo
_COOKIE_ERR_MARKERS = (
    "Could not copy Chrome cookie database",
    "Failed to decrypt with DPAPI",
    "App-Bound Encryption",
    "cookie database",
)


def _is_cookie_error(stderr: str) -> bool:
    return any(m in stderr for m in _COOKIE_ERR_MARKERS)


def _friendly_error(stderr: str, url: str) -> str:
    """Traduz erros do yt-dlp em mensagens acionáveis para o usuário."""
    host = (urlparse(url).hostname or "").lower()
    fb = "facebook.com" in host or "fb.com" in host
    ig = "instagram.com" in host

    if "Unsupported URL" in stderr:
        if fb:
            return (
                "O yt-dlp instalado não suporta listagem de vídeos de páginas/perfis do Facebook. "
                "Atualize para a versão mais recente: pip install -U yt-dlp  "
                "Ou cole a URL de um vídeo específico (ex: facebook.com/watch?v=ID)."
            )
        if ig:
            return (
                "URL do Instagram não reconhecida. Tente a URL do perfil direto "
                "(ex: instagram.com/usuario) e atualize o yt-dlp: pip install -U yt-dlp"
            )
        return f"URL não reconhecida pelo yt-dlp. Verifique se está correta."

    if ig and ("Unable to extract data" in stderr or "Failed to extract" in stderr):
        return (
            "Instagram bloqueou a extração de dados. Verifique:\n"
            "• Você está logado no Instagram pelo Firefox?\n"
            "• Atualize o yt-dlp: pip install -U yt-dlp\n"
            "• Tente novamente em alguns minutos (possível limite de requisições)."
        )

    if "Login required" in stderr or "login required" in stderr:
        return (
            "Conteúdo privado ou que exige login. "
            "Certifique-se de estar logado no Facebook/Instagram pelo Firefox."
        )

    return stderr[:400] if stderr else "Erro desconhecido."


def parse_body(raw: bytes, content_type: str) -> dict:
    """Parseia body como JSON ou application/x-www-form-urlencoded.
    Tenta JSON primeiro se o body começar com '{' para lidar com
    clientes que esquecem de setar o Content-Type corretamente."""
    stripped = raw.lstrip()
    if "application/json" in content_type or stripped.startswith(b"{"):
        try:
            return json.loads(raw)
        except Exception:
            if "application/json" in content_type:
                return {}  # era pra ser JSON mas falhou

    # URL-encoded
    decoded = raw.decode("utf-8", errors="replace")
    result: dict = {}
    for pair in decoded.split("&"):
        if "=" not in pair:
            continue
        k, v = pair.split("=", 1)
        k, v = unquote_plus(k), unquote_plus(v)
        if k.endswith("[]"):
            k = k[:-2]
            result.setdefault(k, []).append(v)
        else:
            result[k] = v
    return result


# ── Handler ────────────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass  # silencia logs do HTTP server

    # ── CORS ──────────────────────────────────────────────────────────────────

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    # ── Resposta JSON ─────────────────────────────────────────────────────────

    def _json(self, data: dict, status: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (ConnectionAbortedError, BrokenPipeError, OSError):
            # cliente fechou a conexão antes de receber — inofensivo
            pass

    # ── Leitura do body ───────────────────────────────────────────────────────

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        ct = self.headers.get("Content-Type", "")
        return parse_body(raw, ct)

    # ── GET ───────────────────────────────────────────────────────────────────

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/ping":
            # Usa valores cacheados em main() — sem subprocess no hot path
            self._json({
                "ok": True,
                "mode": "local",
                "ytdlp": bool(_YTDLP_BIN),
                "version": _YTDLP_VERSION,
                "download_dir": str(DOWNLOAD_DIR),
            })
        else:
            self._json({"ok": False, "error": "Not found"}, 404)

    # ── POST ──────────────────────────────────────────────────────────────────

    def do_POST(self):
        path = urlparse(self.path).path
        body = self._read_body()
        if path == "/fetch_videos":
            self._handle_fetch_videos(body)
        elif path == "/download":
            self._handle_download(body)
        else:
            self._json({"ok": False, "error": "Not found"}, 404)

    # ── fetch_videos ──────────────────────────────────────────────────────────

    def _handle_fetch_videos(self, body: dict):
        url   = str(body.get("url", "")).strip()
        start = max(1, int(body.get("start", 1)))
        count = min(100, max(1, int(body.get("count", 100))))

        if not url:
            return self._json({"ok": False, "error": "URL não informada"})

        if not _YTDLP_BIN:
            return self._json({"ok": False, "error": "yt-dlp não instalado"})

        url = normalize_url(url)
        url = _resolve_facebook_share(url)
        url = _canonicalize_facebook_url(url)

        # Facebook e Instagram exigem cookies de sessão.
        # Tenta cada browser detectado em sequência até um funcionar.
        browsers_to_try: list[str | None] = (
            _COOKIE_BROWSERS if _needs_cookies(url) else [None]
        )
        if _needs_cookies(url) and not _COOKIE_BROWSERS:
            return self._json({"ok": False,
                "error": "Facebook e Instagram requerem que você esteja logado "
                         "no browser. Nenhum browser foi detectado na sua máquina."})

        r = None
        last_stderr = ""
        first_real_error = ""   # primeiro erro que NÃO é falha de cookie de browser
        base_cmd = ytdlp_cmd(_YTDLP_BIN) + [
            "--flat-playlist", "--dump-single-json",
            "--no-warnings", "--ignore-errors",
            "--playlist-start", str(start),
            "--playlist-end",   str(start + count - 1),
        ] + _extra_args_for_url(url)
        for browser in browsers_to_try:
            cookie_args = ["--cookies-from-browser", browser] if browser else []
            print(f"[fetch] browser={browser or 'nenhum'}  url={url[:80]}")
            try:
                r = subprocess.run(base_cmd + cookie_args + [url],
                                   capture_output=True, text=True, timeout=120)
            except subprocess.TimeoutExpired:
                return self._json({"ok": False, "error": "Timeout ao buscar vídeos (>2 min)"})
            stderr = (r.stderr or "").strip()
            last_stderr = stderr
            # Preserva o primeiro erro de conteúdo — erros de cookie são ruído
            if stderr and not _is_cookie_error(stderr) and not first_real_error:
                first_real_error = stderr
            stdout_ok = bool(r.stdout.strip()) and r.stdout.strip() != "null"
            print(f"[fetch] rc={r.returncode}  stdout={len(r.stdout)} chars  stderr={stderr[:200] or '(vazio)'}")
            if stdout_ok:
                break  # sucesso — sai do loop

        if not r or not r.stdout.strip() or r.stdout.strip() == "null":
            best_err = first_real_error or last_stderr
            msg = _friendly_error(best_err, url) if best_err else "Verifique se a URL é válida e pública."
            return self._json({"ok": False, "error": msg})

        # yt-dlp pode retornar um JSON por linha (vários vídeos sem wrapper de playlist)
        # ou um único JSON de playlist, ou null. Tenta parsear todos os casos.
        data = None
        lines = [ln for ln in r.stdout.splitlines() if ln.strip()]
        if len(lines) == 1:
            try:
                data = json.loads(lines[0])
            except json.JSONDecodeError:
                pass
        else:
            # múltiplas linhas → tenta encontrar o objeto de playlist ou coleta todos
            parsed_lines = []
            for ln in lines:
                try:
                    obj = json.loads(ln)
                    if isinstance(obj, dict):
                        parsed_lines.append(obj)
                except json.JSONDecodeError:
                    pass
            # Se algum objeto tem 'entries', é o wrapper de playlist
            for obj in parsed_lines:
                if "entries" in obj:
                    data = obj
                    break
            # Caso contrário, monta um wrapper artificial com os objetos coletados
            if data is None and parsed_lines:
                data = {"entries": parsed_lines,
                        "title":    parsed_lines[0].get("uploader", ""),
                        "extractor": parsed_lines[0].get("extractor", "")}

        if not isinstance(data, dict):
            print(f"[fetch] JSON inválido. data={repr(data)[:100]}  stderr={last_stderr[:200] or '(vazio)'}")
            detail = f" Detalhe: {last_stderr[:400]}" if last_stderr else ""
            return self._json({"ok": False,
                               "error": f"Nenhum vídeo encontrado. Verifique se a URL é válida e pública.{detail}"})

        # Se o yt-dlp retornou um único vídeo (sem 'entries'), trata como lista de 1
        if "entries" not in data:
            entries = [data]
        else:
            entries = [e for e in (data.get("entries") or []) if e]

        def best_thumb(e: dict) -> str:
            t = e.get("thumbnail", "")
            if not t and e.get("thumbnails"):
                t = sorted(e["thumbnails"], key=lambda x: x.get("width", 0), reverse=True)[0].get("url", "")
            return t

        videos = [{
            "id":       e.get("id", ""),
            "title":    e.get("title") or e.get("id") or "Sem título",
            "url":      e.get("webpage_url") or e.get("url", ""),
            "thumb":    best_thumb(e),
            "duration": int(e.get("duration") or 0),
            "views":    int(e.get("view_count") or 0),
            "date":     e.get("upload_date", ""),
        } for e in entries]

        self._json({
            "ok":       True,
            "videos":   videos,
            "fetched":  len(videos),
            "start":    start,
            "has_more": len(videos) >= count,
            "profile":  data.get("title") or data.get("uploader", ""),
            "platform": (data.get("extractor") or data.get("extractor_key") or "").lower(),
        })

    # ── download (SSE) ────────────────────────────────────────────────────────

    def _handle_download(self, body: dict):
        urls_raw = body.get("urls", [])
        if isinstance(urls_raw, str):
            urls_raw = [urls_raw]
        urls = [u.strip() for u in urls_raw if str(u).strip().startswith("http")]

        if not urls:
            return self._json({"ok": False, "error": "Nenhuma URL válida recebida"})

        if not _YTDLP_BIN:
            return self._json({"ok": False, "error": "yt-dlp não instalado"})

        DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

        # Abre SSE
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        def emit(payload: dict):
            line = "data: " + json.dumps(payload, ensure_ascii=False) + "\n\n"
            try:
                self.wfile.write(line.encode())
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass

        total  = len(urls)
        done   = 0
        failed = 0

        emit({"type": "start", "total": total, "mode": "local",
              "download_dir": str(DOWNLOAD_DIR)})

        for i, url in enumerate(urls):
            n = i + 1
            url = normalize_url(url)
            emit({"type": "progress", "done": done, "total": total, "n": n,
                  "msg": f"Baixando vídeo {n} de {total}..."})

            out_tpl = str(DOWNLOAD_DIR / "%(title).80B.%(ext)s")
            # Escolhe o primeiro browser que funcionar (fallback automático)
            dl_browsers: list[str | None] = (
                _COOKIE_BROWSERS if _needs_cookies(url) and _COOKIE_BROWSERS else [None]
            )
            dl_browser = dl_browsers[0] if dl_browsers else None
            dl_cookie_args: list[str] = (
                ["--cookies-from-browser", dl_browser] if dl_browser else []
            )
            cmd = ytdlp_cmd(_YTDLP_BIN) + [
                "--no-playlist", "--no-warnings", "--ignore-errors",
                "--merge-output-format", "mp4",
                "-o", out_tpl,
            ] + _extra_args_for_url(url) + dl_cookie_args + [url]

            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
                if proc.returncode == 0:
                    done += 1
                    emit({"type": "done_one", "done": done, "total": total, "n": n})
                else:
                    failed += 1
                    stderr = proc.stdout + proc.stderr  # yt-dlp mixes stdout/stderr
                    err = next((l for l in reversed(stderr.splitlines()) if "ERROR" in l), "")
                    emit({"type": "error", "done": done, "total": total, "n": n,
                          "msg": f"Falha no vídeo {n}" + (f": {err[:120]}" if err else ".")})
            except subprocess.TimeoutExpired:
                failed += 1
                emit({"type": "error", "done": done, "total": total, "n": n,
                      "msg": f"Vídeo {n}: timeout (>10 min)"})

        if done > 0:
            emit({"type": "complete", "done": done, "total": total, "failed": failed,
                  "download_dir": str(DOWNLOAD_DIR)})
        else:
            emit({"type": "failed", "msg": "Nenhum vídeo foi baixado com sucesso."})


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    global _YTDLP_BIN, _YTDLP_VERSION, _COOKIE_BROWSERS
    _YTDLP_BIN = find_ytdlp()
    if _YTDLP_BIN:
        try:
            _YTDLP_VERSION = subprocess.run(
                ytdlp_cmd(_YTDLP_BIN) + ["--version"],
                capture_output=True, text=True, timeout=10
            ).stdout.strip()
        except Exception:
            _YTDLP_VERSION = ""
    _COOKIE_BROWSERS = detect_cookie_browsers()

    print("=" * 60)
    print("  Video Downloader — Agente Local")
    print("=" * 60)
    print(f"  Porta:           {PORT}")
    print(f"  yt-dlp:          {'encontrado ✓  ' + _YTDLP_VERSION if _YTDLP_BIN else 'NÃO encontrado ✗'}")
    print(f"  Browser cookies: {', '.join(_COOKIE_BROWSERS) if _COOKIE_BROWSERS else 'nenhum detectado'}")
    print(f"  Pasta downloads: {DOWNLOAD_DIR}")
    print()

    if not _YTDLP_BIN:
        print("ERRO: yt-dlp não encontrado. Instale com:")
        print("  pip install yt-dlp          (Mac / Linux / Windows)")
        print("  pipx install yt-dlp         (alternativa)")
        print("  winget install yt-dlp       (Windows)")
        sys.exit(1)

    print(f"Servidor rodando em http://localhost:{PORT}")
    print("Mantenha esta janela aberta enquanto usa o app.")
    print("Pressione Ctrl+C para encerrar.")
    print()

    class _QuietServer(HTTPServer):
        """Suprime tracebacks de conexões abortadas pelo cliente (inofensivos)."""
        def handle_error(self, request, client_address):
            exc = sys.exc_info()[1]
            if isinstance(exc, (ConnectionAbortedError, BrokenPipeError, OSError)):
                return
            super().handle_error(request, client_address)

    server = _QuietServer(("127.0.0.1", PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nAgente local encerrado.")


if __name__ == "__main__":
    main()
