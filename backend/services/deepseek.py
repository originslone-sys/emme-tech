import httpx
import os
import json
import re
import math
import asyncio

_SYMBOL_RE = re.compile(r"[^\w\sÀ-ɏ]")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
BASE_URL = "https://api.deepseek.com/chat/completions"

# Análise de vídeos longos em blocos para não estourar o contexto da IA.
_BLOCK_CHAR_BUDGET = 14000   # ~ tamanho seguro de transcrição por chamada
_MAX_CONCURRENCY = 4         # chamadas simultâneas à API

_SYSTEM = (
    "Você é um editor especialista em conteúdo viral para TikTok, Reels e Shorts. "
    "Recebe a transcrição de um vídeo com timestamps e seleciona os melhores trechos "
    "para virarem cortes curtos e virais."
)


def _build_prompt(segments: list[dict], num_clips: int, min_dur: int = 15) -> str:
    lines = [f"[{s['start']:.1f}-{s['end']:.1f}] {s['text']}" for s in segments]
    transcript = "\n".join(lines)
    total_dur = segments[-1]["end"] if segments else 0
    max_dur = max(min_dur + 30, 90)
    return (
        f"Transcrição do vídeo (em segundos, duração total ~{total_dur:.0f}s):\n\n{transcript}\n\n"
        f"Selecione os {num_clips} melhores trechos para cortes virais. "
        f"Cada corte deve ter NO MÍNIMO {min_dur} segundos e no máximo {max_dur} segundos, "
        "ser autocontido (começo, meio e fim), "
        "e ter alto potencial de engajamento (gancho forte, emoção, curiosidade ou valor).\n"
        f"IMPORTANTE: respeite a duração mínima de {min_dur} segundos por corte. "
        f"Se o vídeo for longo (ex: um filme ou episódio), distribua os {num_clips} "
        "cortes ao longo de TODO o vídeo (começo, meio e fim) — não concentre tudo num só ponto. "
        "Os trechos NÃO podem se sobrepor.\n\n"
        "Responda APENAS em JSON válido neste formato:\n"
        '{"clips": [{"start": número_segundos, "end": número_segundos, '
        '"title": "título chamativo até 60 caracteres", '
        '"description": "legenda pronta pra postar com emojis e hashtags", '
        '"tags": ["tag1", "tag2", "tag3"], '
        '"score": número_de_0_a_100}]}'
    )


def _split_segments(segments: list[dict],
                    char_budget: int = _BLOCK_CHAR_BUDGET) -> list[list[dict]]:
    """Divide a transcrição em blocos sequenciais que cabem no contexto da IA."""
    blocks: list[list[dict]] = []
    cur: list[dict] = []
    cur_len = 0
    for s in segments:
        line_len = len(str(s.get("text", ""))) + 20  # texto + timestamp aprox.
        if cur and cur_len + line_len > char_budget:
            blocks.append(cur)
            cur = []
            cur_len = 0
        cur.append(s)
        cur_len += line_len
    if cur:
        blocks.append(cur)
    return blocks


async def _select_from_segments(segments: list[dict], num_clips: int,
                                min_dur: int = 15) -> list[dict]:
    """Uma única chamada à IA para um conjunto de segmentos."""
    block_end = segments[-1]["end"] if segments else 0
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": _build_prompt(segments, num_clips, min_dur)},
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
        # Garante a duração mínima: estende o fim (sem ultrapassar o fim do bloco)
        # e, se faltar, recua o início.
        if end - start < min_dur:
            end = min(start + min_dur, block_end) if block_end else start + min_dur
            if end - start < min_dur:
                start = max(0.0, end - min_dur)
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


async def select_clips(segments: list[dict], num_clips: int = 3,
                       on_progress=None, min_dur: int = 15) -> list[dict]:
    """Seleciona os melhores cortes.

    on_progress(done, total): callback opcional chamado conforme os blocos
    de análise são concluídos (para mostrar progresso ao usuário).
    min_dur: duração mínima (em segundos) que cada corte deve ter.
    """
    if not segments:
        return []

    blocks = _split_segments(segments)
    total = len(blocks)

    # Vídeo curto: uma única análise resolve.
    if total <= 1:
        if on_progress:
            on_progress(0, 1)
        clips = await _select_from_segments(segments, num_clips, min_dur)
        if on_progress:
            on_progress(1, 1)
        return clips[:num_clips]

    # Vídeo longo (filme, podcast, aula): analisa cada bloco em paralelo e
    # depois junta os candidatos, distribuindo os cortes ao longo de todo o vídeo.
    per_block = max(2, math.ceil(num_clips / total) + 1)
    sem = asyncio.Semaphore(_MAX_CONCURRENCY)
    lock = asyncio.Lock()
    done_count = 0
    if on_progress:
        on_progress(0, total)

    async def _run(block: list[dict]) -> list[dict]:
        nonlocal done_count
        async with sem:
            try:
                res = await _select_from_segments(block, per_block, min_dur)
            except Exception:
                res = []
        async with lock:
            done_count += 1
            if on_progress:
                on_progress(done_count, total)
        return res

    results = await asyncio.gather(*[_run(b) for b in blocks])
    for r in results:
        r.sort(key=lambda x: x["score"], reverse=True)

    # Round-robin entre os blocos: garante cortes espalhados do começo ao fim,
    # pegando primeiro o melhor de cada bloco, depois o segundo melhor, etc.
    merged: list[dict] = []
    idx = 0
    while len(merged) < num_clips and any(idx < len(r) for r in results):
        for r in results:
            if idx < len(r):
                merged.append(r[idx])
                if len(merged) >= num_clips:
                    break
        idx += 1

    merged.sort(key=lambda x: x["score"], reverse=True)
    return merged[:num_clips]



# ---------- Character Sheet para personagem de IA generativa ----------

_SYSTEM_CHARACTER = (
    "You are an expert at writing precise, detailed prompts for photorealistic "
    "AI image generation models (FLUX). Your character sheets must be extremely "
    "specific about physical features so the model generates the exact same face "
    "consistently across all scenes. Write only in English."
)


def _build_character_prompt(fields: dict) -> str:
    return (
        "Create a character sheet prompt for a photorealistic AI image generation model.\n\n"
        f"Character details provided by the user:\n"
        f"- Sex: {fields.get('sex', '')}\n"
        f"- Age: {fields.get('age', '')}\n"
        f"- Ethnicity/skin tone: {fields.get('ethnicity', '')}\n"
        f"- Hair (color + style): {fields.get('hair', '')}\n"
        f"- Eyes (color + shape): {fields.get('eyes', '')}\n"
        f"- Distinctive traits: {fields.get('traits', '')}\n"
        f"- Visual personality tone: {fields.get('tone', '')}\n\n"
        "Rules:\n"
        "1. The anchor_prompt must be a single dense paragraph in English describing ONLY "
        "the person's permanent physical features (face shape, skin, eyes, nose, lips, "
        "jawline, hair). No clothing, no background, no pose.\n"
        "2. Be hyper-specific: avoid vague words like 'beautiful' or 'attractive'. "
        "Use precise descriptors like 'almond-shaped dark brown eyes', "
        "'heart-shaped face with high cheekbones', 'straight black hair cut at collarbone'.\n"
        "3. End the anchor_prompt with quality tags: "
        "'photorealistic, 8K resolution, sharp focus, natural skin texture, "
        "Canon EOS R5, 85mm portrait lens, f/1.8, studio lighting'.\n"
        "4. Also write a short foundation_scene: neutral portrait setup for generating "
        "the 6 reference photos (front-facing, neutral expression, white background, "
        "soft even lighting). This is appended to anchor_prompt only for the initial batch.\n\n"
        "Respond ONLY in valid JSON:\n"
        '{"anchor_prompt": "...", "foundation_scene": "...", "display_summary": "one sentence describing the character in Portuguese"}'
    )


async def generate_character_sheet(fields: dict) -> dict:
    """Gera o prompt-âncora do personagem a partir dos campos do usuário."""
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": _SYSTEM_CHARACTER},
            {"role": "user", "content": _build_character_prompt(fields)},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.3,
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            BASE_URL,
            json=payload,
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            timeout=60,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]

    data = json.loads(content, strict=False)
    anchor = str(data.get("anchor_prompt", "")).strip()
    foundation = str(data.get("foundation_scene", "")).strip()
    summary = str(data.get("display_summary", "")).strip()
    if not anchor:
        raise RuntimeError("A IA não conseguiu gerar o prompt do personagem")
    return {"anchor_prompt": anchor, "foundation_scene": foundation, "display_summary": summary}


def build_scene_prompt(anchor_prompt: str, scene_fields: dict) -> str:
    """Monta o prompt final para geração de uma cena com o personagem."""
    parts = [anchor_prompt]
    if scene_fields.get("scenario"):
        parts.append(scene_fields["scenario"])
    if scene_fields.get("outfit"):
        parts.append(f"wearing {scene_fields['outfit']}")
    if scene_fields.get("pose"):
        parts.append(scene_fields["pose"])
    if scene_fields.get("expression"):
        parts.append(f"{scene_fields['expression']} expression")
    if scene_fields.get("lighting"):
        parts.append(f"{scene_fields['lighting']} lighting")
    return ", ".join(parts)


_SYSTEM_VIRAL = (
    "Você é um roteirista de vídeos virais para TikTok, Reels e YouTube Shorts. "
    "Você escreve como um influencer real: linguagem do dia a dia, direta, sem enrolação. "
    "PROIBIDO: palavras difíceis ou pouco usadas (ex: 'protagonizar', 'perpasse', 'alavancar', "
    "'fomentar', 'imprescindível', 'outrossim'), clichês de marketing, frases genéricas que "
    "servem pra qualquer assunto. "
    "OBRIGATÓRIO: cada vídeo é uma criação única — gancho diferente, ângulo diferente, "
    "ritmo diferente. Escreva como se estivesse conversando com um amigo. "
    "Sem símbolos no texto da tela: sem '...', '!?', '*', '#', '@', '—', '→'. "
    "O texto da tela tem no máximo 5 palavras e é tão direto que dá pra ler em meio segundo."
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
        "Regras OBRIGATÓRIAS:\n"
        "1. GANCHO na primeira cena — uma frase de impacto que faz parar de rolar o feed. "
        "Sem 'Olá', sem apresentação. Direto ao ponto. Exemplo de ângulo: revelar algo "
        "surpreendente, contradizer o senso comum, ou prometer algo valioso em segundos.\n"
        "2. O campo 'text' (texto da tela) tem NO MÁXIMO 5 palavras. Sem pontuação elaborada, "
        "sem reticências, sem símbolos. Letras e espaços apenas. Tem que dar pra ler em 0,5 segundo.\n"
        "3. O campo 'narration' é a fala do narrador: 1 frase curta, linguagem casual, "
        "como você diria pra um amigo. Sem palavras difíceis. Sem repetir o texto da tela.\n"
        "4. Cada cena leva a próxima — o espectador não pode achar que acabou antes da última cena.\n"
        "5. A ÚLTIMA cena tem uma chamada pra ação concreta (ex: 'segue pra ver mais', "
        "'comenta aqui embaixo', 'salva esse video').\n"
        "6. 'visual_query' em inglês, concreta, filmável, existente em banco de vídeo "
        "(ex: 'slow motion coffee being poured', 'woman laughing on phone closeup', "
        "'city traffic aerial view night'). Sem conceitos abstratos.\n"
        "7. Duração de cada cena: entre 2 e 5 segundos, soma total ~"
        f"{duration} segundos.\n"
        "8. Escolha 'music_mood' entre: energetic, upbeat, inspirational, calm, dramatic, epic.\n\n"
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


def _sanitize_screen_text(text: str) -> str:
    """Remove símbolos e limita o texto da tela a 6 palavras."""
    text = text.strip()
    text = _SYMBOL_RE.sub("", text)   # remove tudo que não é letra/número/espaço
    text = " ".join(text.split())     # normaliza espaços
    words = text.split()
    if len(words) > 6:
        text = " ".join(words[:6])
    return text


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
        text = _sanitize_screen_text(str(s.get("text", "")))
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
