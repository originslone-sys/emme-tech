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

    data = json.loads(content, strict=False)
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


# ---------- Roteiro de vídeo viral (do zero) ----------

_SYSTEM_VIRAL = (
    "Você é um roteirista especialista em vídeos virais para TikTok, Reels e YouTube Shorts. "
    "Domina as técnicas que prendem atenção: gancho irresistível nos 3 primeiros segundos, "
    "quebras de padrão, loops de curiosidade (open loops), ritmo acelerado, tensão emocional "
    "e uma chamada pra ação no final. Seus roteiros NUNCA são genéricos: cada frase tem função, "
    "cada cena empurra o espectador pra próxima. Você escreve para reter o espectador até o fim "
    "(retenção = viralização)."
)


def _build_viral_prompt(topic: str, duration: int, language: str, fmt: str) -> str:
    # nº aproximado de cenas: ~2.5–4s por cena dá um ritmo dinâmico
    n_scenes = max(4, min(16, round(duration / 3)))
    return (
        f"Crie um roteiro de vídeo viral sobre: \"{topic}\".\n\n"
        f"Especificações:\n"
        f"- Duração total: ~{duration} segundos\n"
        f"- Formato: {fmt}\n"
        f"- Idioma do texto na tela e legendas: {language}\n"
        f"- Aproximadamente {n_scenes} cenas (ritmo rápido).\n\n"
        "Regras OBRIGATÓRIAS para viralizar:\n"
        "1. A PRIMEIRA cena é o GANCHO — uma frase de choque/curiosidade que faz parar de rolar o feed "
        "(ex: 'Você está fazendo isso errado a vida toda', 'Ninguém te conta isso sobre...'). Nada de introdução.\n"
        "2. Cada cena tem um texto CURTO de tela (no máximo ~8 palavras), de altíssimo impacto, no idioma pedido. "
        "Sem frases longas — o olho precisa ler em 1 segundo.\n"
        "3. Cada cena tem também uma 'narration': a frase FALADA pelo narrador (1 frase natural, fluida, "
        "no idioma pedido), que expande o texto da tela e mantém o ritmo da fala. É o que será dito em voz alta.\n"
        "4. Mantenha um loop de curiosidade: cada cena cria vontade de ver a próxima.\n"
        "5. A ÚLTIMA cena é uma chamada pra ação (seguir, comentar, salvar, ou uma virada final).\n"
        "6. Para cada cena, defina uma 'visual_query' EM INGLÊS, concreta e filmável, que exista como vídeo "
        "de banco de imagens (ex: 'slow motion ocean waves at sunset', 'person typing on laptop close up', "
        "'busy city street timelapse night'). Evite conceitos abstratos que não rendem vídeo.\n"
        "7. Defina a duração de cada cena (entre 2 e 5 segundos) somando ~"
        f"{duration} segundos no total. A narração de cada cena deve caber nesse tempo falando num ritmo natural.\n"
        "8. Escolha um 'music_mood' para a trilha entre: energetic, upbeat, inspirational, calm, dramatic, epic.\n\n"
        "Responda APENAS em JSON válido neste formato exato:\n"
        '{"title": "título chamativo até 60 caracteres", '
        '"description": "legenda pronta pra postar com emojis e hashtags", '
        '"tags": ["tag1", "tag2", "tag3"], '
        '"music_mood": "energetic", '
        '"scenes": [{"text": "texto curto na tela", '
        '"narration": "frase falada pelo narrador", '
        '"visual_query": "concrete english search query", '
        '"duration": número_segundos}]}'
    )


_VALID_MOODS = {"energetic", "upbeat", "inspirational", "calm", "dramatic", "epic"}


async def generate_viral_script(topic: str, duration: int = 30,
                                language: str = "Português", fmt: str = "9:16") -> dict:
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": _SYSTEM_VIRAL},
            {"role": "user", "content": _build_viral_prompt(topic, duration, language, fmt)},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.9,
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

    data = json.loads(content, strict=False)
    raw_scenes = data.get("scenes", [])

    scenes = []
    for s in raw_scenes:
        text = str(s.get("text", "")).strip()
        narration = str(s.get("narration", "")).strip()
        query = str(s.get("visual_query", "")).strip()
        if not query:
            continue
        try:
            dur = float(s.get("duration", 3))
        except (ValueError, TypeError):
            dur = 3.0
        dur = max(1.5, min(6.0, dur))
        scenes.append({
            "text": text,
            "narration": narration or text,
            "visual_query": query,
            "duration": dur,
        })

    if not scenes:
        raise RuntimeError("A IA não conseguiu gerar um roteiro válido")
    scenes = scenes[:18]

    # Reescala as durações para baterem com o alvo pedido
    total = sum(s["duration"] for s in scenes)
    if total > 0 and duration > 0:
        factor = duration / total
        for s in scenes:
            s["duration"] = round(max(1.5, min(6.0, s["duration"] * factor)), 2)

    mood = str(data.get("music_mood", "")).strip().lower()
    if mood not in _VALID_MOODS:
        mood = "energetic"

    return {
        "title": str(data.get("title", topic)).strip()[:80] or topic,
        "description": str(data.get("description", "")).strip(),
        "tags": [str(t).strip() for t in data.get("tags", []) if str(t).strip()][:10],
        "music_mood": mood,
        "scenes": scenes,
    }
