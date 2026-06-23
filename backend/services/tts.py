import asyncio
import base64
import os
import uuid

import httpx

from services import storage, runpod, ffmpeg

_LANG = {"Português": "pt", "English": "en", "Español": "es"}

_TTS_TIMEOUT = 60 * 10  # 10 min
_POLL_INTERVAL = 4

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")

# Vozes do ElevenLabs em português brasileiro (modelo eleven_multilingual_v2)
_EL_VOICE = {
    "feminina": "ORgG8rwdAiMYRug8RJwR",   # Ana Alice — Friendly & Clear (PT-BR)
    "masculina": "7lu3ze7orhWaNeSPowWx",  # Lucas — Engaging & Captivating (PT-BR)
}
_EL_MODEL = "eleven_multilingual_v2"


def _lang_code(language: str) -> str:
    return _LANG.get(language, "pt")


async def synthesize_scenes(narrations: list[str], language: str,
                            voice: str) -> list[dict | None]:
    """Gera o áudio de narração de cada cena.

    Prioridade: RunPod XTTS → ElevenLabs → gTTS.
    """
    lang = _lang_code(language)
    if runpod.TTS_ENDPOINT:
        return await _via_runpod(narrations, lang, voice)
    if ELEVENLABS_API_KEY:
        return await _via_elevenlabs(narrations, voice)
    return await asyncio.to_thread(_via_gtts, narrations, lang)


async def _via_runpod(narrations: list[str], lang: str, voice: str) -> list[dict | None]:
    job_id = await runpod.submit_tts_job(narrations, lang, voice)
    waited = 0
    while waited < _TTS_TIMEOUT:
        data = await runpod.get_job_status(job_id, runpod.TTS_ENDPOINT)
        status = data.get("status")
        if status == "COMPLETED":
            return _save_runpod_clips(data)
        if status in ("FAILED", "CANCELLED", "TIMED_OUT"):
            raise RuntimeError(data.get("error") or "TTS falhou")
        await asyncio.sleep(_POLL_INTERVAL)
        waited += _POLL_INTERVAL
    raise RuntimeError("Tempo esgotado na narração")


def _save_runpod_clips(data: dict) -> list[dict | None]:
    output = data.get("output") or {}
    if isinstance(output, list):
        output = output[0] if output else {}
    clips = output.get("clips", [])
    result: list[dict | None] = []
    for c in clips:
        b64 = c.get("audio_base64") or ""
        if not b64:
            result.append(None)
            continue
        path = str(storage.DIRS["uploads"] / f"narr_{uuid.uuid4()}.wav")
        with open(path, "wb") as f:
            f.write(base64.b64decode(b64))
        dur = float(c.get("duration") or 0) or ffmpeg.probe_duration(path)
        result.append({"path": path, "duration": dur})
    return result


async def _via_elevenlabs(narrations: list[str], voice: str) -> list[dict | None]:
    voice_id = _EL_VOICE.get(voice, _EL_VOICE["feminina"])
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }
    result: list[dict | None] = []
    async with httpx.AsyncClient(timeout=60) as client:
        for text in narrations:
            text = (text or "").strip()
            if not text:
                result.append(None)
                continue
            payload = {
                "text": text,
                "model_id": _EL_MODEL,
                "voice_settings": {
                    "stability": 0.40,
                    "similarity_boost": 0.85,
                    "style": 0.35,
                    "use_speaker_boost": True,
                },
            }
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            path = str(storage.DIRS["uploads"] / f"narr_{uuid.uuid4()}.mp3")
            with open(path, "wb") as f:
                f.write(resp.content)
            dur = ffmpeg.probe_duration(path)
            result.append({"path": path, "duration": dur})
    return result


def _via_gtts(narrations: list[str], lang: str) -> list[dict | None]:
    from gtts import gTTS
    result: list[dict | None] = []
    for text in narrations:
        if not text.strip():
            result.append(None)
            continue
        path = str(storage.DIRS["uploads"] / f"narr_{uuid.uuid4()}.mp3")
        gTTS(text=text, lang=lang).save(path)
        result.append({"path": path, "duration": ffmpeg.probe_duration(path)})
    return result

