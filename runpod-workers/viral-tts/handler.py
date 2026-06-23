"""
Worker serverless RunPod — narração por voz (TTS) com Coqui XTTS-v2.

Input:
{
  "input": {
    "texts": ["frase da cena 1", "frase da cena 2", ...],
    "language": "pt",          # pt | en | es
    "voice": "feminina"        # feminina | masculina
  }
}

Output:
{ "clips": [{"audio_base64": "<wav>", "duration": 3.42}, ...] }

XTTS-v2 é multilíngue e soa natural — bom pra retenção. Roda na GPU.
"""
import base64
import os
import tempfile
import wave

os.environ.setdefault("COQUI_TOS_AGREED", "1")

import runpod
import torch
from TTS.api import TTS

MODEL = "tts_models/multilingual/multi-dataset/xtts_v2"

# Falantes embutidos do XTTS-v2
_SPEAKER = {"feminina": "Ana Florence", "masculina": "Damien Black"}

_tts = None


def _model():
    global _tts
    if _tts is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        _tts = TTS(MODEL).to(device)
    return _tts


def _wav_duration(path: str) -> float:
    try:
        with wave.open(path) as w:
            return round(w.getnframes() / float(w.getframerate()), 3)
    except Exception:
        return 0.0


def handler(job):
    inp = job.get("input", {})
    texts = inp.get("texts", [])
    language = inp.get("language", "pt")
    voice = inp.get("voice", "feminina")
    speaker = _SPEAKER.get(voice, "Ana Florence")

    tts = _model()
    clips = []
    for text in texts:
        text = (text or "").strip()
        if not text:
            clips.append({"audio_base64": "", "duration": 0})
            continue
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            path = f.name
        try:
            tts.tts_to_file(text=text, file_path=path, speaker=speaker, language=language)
            dur = _wav_duration(path)
            with open(path, "rb") as fb:
                b64 = base64.b64encode(fb.read()).decode("utf-8")
            clips.append({"audio_base64": b64, "duration": dur})
        finally:
            if os.path.exists(path):
                os.remove(path)

    return {"clips": clips}


runpod.serverless.start({"handler": handler})
