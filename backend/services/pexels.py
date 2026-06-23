import os
import httpx

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
SEARCH_URL = "https://api.pexels.com/videos/search"

# 9:16 -> portrait, 1:1 -> square, 16:9 -> landscape
ORIENTATION = {"9:16": "portrait", "1:1": "square", "16:9": "landscape"}


def _best_file(video: dict, want_w: int, want_h: int) -> str | None:
    """Escolhe o melhor arquivo .mp4: o menor com resolução >= alvo (economiza
    banda mantendo qualidade); se nenhum servir, pega o de maior resolução."""
    files = [f for f in video.get("video_files", []) if f.get("link")]
    if not files:
        return None
    mp4 = [f for f in files if (f.get("file_type") or "").endswith("mp4")] or files

    def res(f):
        return (f.get("width") or 0, f.get("height") or 0)

    big_enough = [f for f in mp4 if res(f)[0] >= want_w and res(f)[1] >= want_h]
    if big_enough:
        big_enough.sort(key=lambda f: res(f)[0] * res(f)[1])
        return big_enough[0]["link"]
    mp4.sort(key=lambda f: res(f)[0] * res(f)[1], reverse=True)
    return mp4[0]["link"]


async def find_clip_url(query: str, fmt: str, want_w: int, want_h: int,
                        used_ids: set | None = None) -> str | None:
    """Busca no Pexels e retorna a URL de um vídeo adequado (ou None)."""
    if not PEXELS_API_KEY:
        raise RuntimeError("PEXELS_API_KEY não configurada no backend")

    orientation = ORIENTATION.get(fmt, "portrait")
    params = {"query": query, "orientation": orientation, "per_page": 15, "size": "medium"}
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            SEARCH_URL, params=params,
            headers={"Authorization": PEXELS_API_KEY}, timeout=30,
        )
        resp.raise_for_status()
        videos = resp.json().get("videos", [])

    if not videos:
        return None

    # Evita repetir o mesmo clipe entre cenas
    for v in videos:
        if used_ids is not None and v.get("id") in used_ids:
            continue
        link = _best_file(v, want_w, want_h)
        if link:
            if used_ids is not None:
                used_ids.add(v.get("id"))
            return link
    # Se todos já foram usados, libera o primeiro disponível
    return _best_file(videos[0], want_w, want_h)


async def download(url: str, dest_path: str):
    """Baixa um vídeo do Pexels para o caminho local."""
    async with httpx.AsyncClient(follow_redirects=True) as client:
        async with client.stream("GET", url, timeout=120) as resp:
            resp.raise_for_status()
            with open(dest_path, "wb") as f:
                async for chunk in resp.aiter_bytes(1 << 16):
                    f.write(chunk)
