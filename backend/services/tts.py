import asyncio
import base64
import uuid

from services import storage, runpod, ffmpeg

_LANG = {"Português": "pt", "English": "en", "Español": "es"}

_TTS_TIMEOUT = 60 * 10  # 10 min
_POLL_INTERVAL = 4


def _lang_code(language: str) -> str:
    return _LANG.get(language, "pt")


async def synthesize_scenes(narrations: list[str], language: str,
                            voice: str) -> list[dict | None]:
    """Gera o áudio de narração de cada cena.

    Retorna uma lista alinhada às cenas com {path, duration} ou None (cena
    sem narração). Usa o worker RunPod (XTTS) se configurado; senão, gTTS.
    """
    lang = _lang_code(language)
    if runpod.TTS_ENDPOINT:
        return await _via_runpod(narrations, lang, voice)
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
