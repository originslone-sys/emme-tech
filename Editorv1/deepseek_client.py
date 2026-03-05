"""
DeepSeek API Client — Geração de metadados YouTube para vídeos evergreen.

Usa apenas stdlib (urllib). Não requer pacotes externos.
Fallback automático para metadados padrão se a API falhar.
"""

import json
import urllib.error
import urllib.request
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Cliente DeepSeek
# ---------------------------------------------------------------------------

class DeepSeekClient:
    """
    Cliente para a API DeepSeek (compatível com OpenAI).
    Fallback automático para frases locais se API indisponível.
    """

    def __init__(self, api_key: str = "", model: str = "deepseek-chat",
                 base_url: str = "https://api.deepseek.com/v1", timeout_s: int = 30):
        self.api_key = api_key.strip()
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s
        self._available: Optional[bool] = None  # lazy check

    # ------------------------------------------------------------------
    # Verificação de disponibilidade
    # ------------------------------------------------------------------

    @property
    def available(self) -> bool:
        if self._available is None:
            self._available = bool(self.api_key)
        return self._available

    # ------------------------------------------------------------------
    # HTTP raw request (stdlib apenas)
    # ------------------------------------------------------------------

    def _post(self, endpoint: str, payload: dict) -> Optional[dict]:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body_err = e.read().decode("utf-8", errors="replace")[:300]
            print(f"  [DeepSeek] HTTP {e.code}: {body_err}")
        except Exception as e:
            print(f"  [DeepSeek] Erro de conexão: {e}")
        return None

    def _chat(self, system_prompt: str, user_prompt: str,
              max_tokens: int = 600, temperature: float = 0.92) -> Optional[str]:
        if not self.available:
            return None
        resp = self._post("chat/completions", {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        })
        if not resp:
            return None
        try:
            return resp["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError):
            return None

    # ------------------------------------------------------------------
    # Geração de metadados para YouTube
    # ------------------------------------------------------------------

    def generate_youtube_metadata(self, style: str, phrases: List[str],
                                  duration_min: int, language: str = "en-US") -> Dict:
        """
        Generates title, description and tags for YouTube upload.
        """
        default = self._default_metadata(style, duration_min)

        if not self.available:
            return default

        sample = phrases[:3] if phrases else ["relaxing music", "lo-fi", "study"]
        sample_str = " | ".join(sample)

        system = (
            "You are an SEO expert for YouTube channels in the lo-fi, "
            "relaxing and study music niche. You write attractive titles and "
            "descriptions that maximize clicks and watch time."
        )
        user = (
            f"Create YouTube metadata in English for this video:\n"
            f"- Style: {style}\n"
            f"- Duration: {duration_min} minutes\n"
            f"- Video phrases: {sample_str}\n\n"
            "Reply ONLY with valid JSON in this exact format:\n"
            '{"title": "...", "description": "...", "tags": ["tag1", "tag2", ...]}\n\n'
            "Rules: title 50-70 chars, description 400-600 chars in English, "
            "15-20 relevant tags in English."
        )

        text = self._chat(system, user, max_tokens=700, temperature=0.75)
        if not text:
            return default

        try:
            start = text.find("{")
            end = text.rfind("}") + 1
            data = json.loads(text[start:end])
            return {
                "title": str(data.get("title", default["title"]))[:100],
                "description": str(data.get("description", default["description"]))[:2000],
                "tags": [str(t) for t in data.get("tags", default["tags"])][:30],
            }
        except Exception:
            return default

    def _default_metadata(self, style: str, duration_min: int) -> Dict:
        titles = {
            "lofi": f"Lofi Hip Hop ☕ {duration_min} Minutes — Relax & Study",
            "relaxing": f"Relaxing Music 🌿 {duration_min} Min — Calm Your Mind",
            "study": f"Study Music 📚 {duration_min} Minutes — Deep Focus Session",
            "shorts": "Lofi Moment ✨ Take a Breath",
        }
        return {
            "title": titles.get(style, f"Lo-fi Vibes 🎵 {duration_min} Minutes"),
            "description": (
                f"🎵 {duration_min} minutes of {style} music to help you relax, "
                "study and find your focus.\n\n"
                "✨ Use headphones for the best experience.\n"
                "📌 Save this playlist for your next session.\n\n"
                "#lofi #relaxing #studymusic #chill #focus"
            ),
            "tags": [
                "lofi", "lo-fi", "relaxing music", "study music", "chill",
                "focus music", "musica relaxante", "musica para estudar",
                style, "ambient", "instrumental", "concentration", "calm",
                "sleep music", "meditation",
            ],
        }
