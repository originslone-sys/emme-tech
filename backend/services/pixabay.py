import os
import httpx

PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY", "")
_VIDEO_URL = "https://pixabay.com/api/videos/"

_ORIENTATION = {"9:16": "vertical", "1:1": "horizontal", "16:9": "horizontal"}


async def find_clip_url(query: str, fmt: str, used_ids: set | None = None) -> str | None:
    if not PIXABAY_API_KEY:
        return None
    orientation = _ORIENTATION.get(fmt, "vertical")
    params = {
        "key": PIXABAY_API_KEY,
        "q": query,
        "video_type": "film",
        "orientation": orientation,
        "per_page": 15,
        "safesearch": "true",
    }
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(_VIDEO_URL, params=params)
        if not resp.is_success:
            return None
        hits = resp.json().get("hits", [])

    for hit in hits:
        if used_ids is not None and hit.get("id") in used_ids:
            continue
        vids = hit.get("videos", {})
        for quality in ("large", "medium", "small", "tiny"):
            link = vids.get(quality, {}).get("url")
            if link:
                if used_ids is not None:
                    used_ids.add(hit.get("id"))
                return link

    # Fallback: primeiro disponível mesmo que já usado
    if hits:
        vids = hits[0].get("videos", {})
        for quality in ("large", "medium", "small", "tiny"):
            link = vids.get(quality, {}).get("url")
            if link:
                return link
    return None


async def download(url: str, dest_path: str):
    async with httpx.AsyncClient(follow_redirects=True) as client:
        async with client.stream("GET", url, timeout=120) as resp:
            resp.raise_for_status()
            with open(dest_path, "wb") as f:
                async for chunk in resp.aiter_bytes(1 << 16):
                    f.write(chunk)
