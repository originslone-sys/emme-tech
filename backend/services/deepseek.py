import httpx
import os
import json

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
BASE_URL = "https://api.deepseek.com/chat/completions"

_SYSTEM = (
    "Você é um editor especialista em conteúdo viral para TikTok, Reels e Shorts. "
    "Recebe a transcrição de um vídeo com timestamps e seleciona os melhores trechos "
    "para virarem cortes curtos e virais."
)


def _build_prompt(segments: list[dict], num_clips: int) -> str:
    lines = [f"[{s['start']:.1f}-{s['end']:.1f}] {s['text']}" for s in segments]
    transcript = "\n".join(lines)
    return (
        f"Transcrição do vídeo (em segundos):\n\n{transcript}\n\n"
        f"Selecione os {num_clips} melhores trechos para cortes virais. "
        "Cada corte deve ter entre 15 e 60 segundos, ser autocontido (começo, meio e fim), "
        "e ter alto potencial de engajamento (gancho forte, emoção, curiosidade ou valor).\n\n"
        "Responda APENAS em JSON válido neste formato:\n"
        '{"clips": [{"start": número_segundos, "end": número_segundos, '
        '"title": "título chamativo até 60 caracteres", '
        '"description": "legenda pronta pra postar com emojis e hashtags", '
        '"tags": ["tag1", "tag2", "tag3"], '
        '"score": número_de_0_a_100}]}'
    )


async def select_clips(segments: list[dict], num_clips: int = 3) -> list[dict]:
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": _build_prompt(segments, num_clips)},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.7,
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            BASE_URL,
            json=payload,
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            timeout=120,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]

    data = json.loads(content)
    clips = data.get("clips", [])
    # Sanitiza e ordena pela nota
    valid = []
    for c in clips:
        try:
            start = float(c["start"])
            end = float(c["end"])
        except (KeyError, ValueError, TypeError):
            continue
        if end <= start:
            continue
        valid.append({
            "start": start,
            "end": end,
            "title": str(c.get("title", "Corte")).strip()[:80],
            "description": str(c.get("description", "")).strip(),
            "tags": [str(t).strip() for t in c.get("tags", []) if str(t).strip()][:10],
            "score": int(c.get("score", 0)) if str(c.get("score", "")).isdigit() else 0,
        })
    valid.sort(key=lambda x: x["score"], reverse=True)
    return valid
