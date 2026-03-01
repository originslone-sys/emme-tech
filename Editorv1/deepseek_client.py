"""
DeepSeek API Client — Geração de frases motivacionais/reflexivas para vídeos evergreen.

Usa apenas stdlib (urllib). Não requer pacotes externos.
Fallback automático para banco local de frases se a API falhar.
"""

import json
import random
import urllib.error
import urllib.request
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Banco de frases fallback (usado se a API falhar ou não estiver configurada)
# ---------------------------------------------------------------------------

FALLBACK_PHRASES: Dict[str, List[str]] = {
    "reflection": [
        "Silence is the music of the soul.",
        "Who looks outside dreams. Who looks inside awakes.",
        "Life is an echo — what you send out comes back.",
        "Know thyself and you shall know the universe.",
        "Time we lose is time we never lived.",
        "Every sunrise is an invitation to begin again.",
        "The depth of a mind is measured by its silence.",
        "We are made of the same stuff that dreams are made on.",
        "Still waters run deep.",
        "To live is the rarest thing. Most people just exist.",
        "The path is made by walking.",
        "Nothing is permanent except change.",
        "The contemplating soul is the transforming soul.",
        "In small things lies greatness.",
        "The universe is infinite within us.",
    ],
    "motivation": [
        "One step at a time builds the journey of a thousand miles.",
        "Persistence is the path to achievement.",
        "Don't wait for the perfect moment. Make the moment perfect.",
        "The secret of getting ahead is getting started.",
        "Your only limitation is the one you accept.",
        "Great achievements are born from small daily actions.",
        "Believe you can and you're already halfway there.",
        "Failure is simply the chance to begin again with more wisdom.",
        "You are stronger than you think.",
        "Courage is not the absence of fear — it's acting despite it.",
        "Do what you can, with what you have, where you are.",
        "The future belongs to those who believe in their dreams.",
        "Every day is a new chance to grow.",
        "Don't give up. Great things take time.",
        "Today's effort is tomorrow's result.",
    ],
    "mindfulness": [
        "Breathe. This moment is all there is.",
        "Be present. Life happens now.",
        "Peace is not the absence of chaos — it's calm within it.",
        "Each breath is a new beginning.",
        "Release what you cannot change. Embrace what you can.",
        "Mindfulness turns the ordinary into the extraordinary.",
        "Observe your thoughts like clouds passing by.",
        "The present is the only time where you have power.",
        "You don't need more time — just more presence.",
        "When you slow down, life expands.",
        "Stop. Feel. Be grateful.",
        "The body knows what the mind has forgotten.",
        "In every moment there's a choice: react or respond.",
        "Calmness is a superpower.",
        "Simplify. Enough is abundant.",
    ],
    "positivity": [
        "Gratitude turns what we have into enough.",
        "Small joys build a great life.",
        "You radiate what you cultivate within.",
        "Kindness is a language everyone understands.",
        "A smile is the shortest distance between two hearts.",
        "Tomorrow will be better because you are here today.",
        "Beauty is waiting to be noticed in every detail.",
        "The energy you offer is the energy you receive.",
        "Every day holds twenty-four hours of possibility.",
        "You are a miracle in motion.",
        "Life is too short not to be kind.",
        "Celebrate the journey, not just the destination.",
        "There is always something to be grateful for.",
        "You are exactly where you need to be.",
        "Happiness is a daily practice, not a destination.",
    ],
    "stoicism": [
        "Wish for things to happen as they are, not as you desire.",
        "The wise man wants for nothing he does not have.",
        "Tranquility belongs to one who neither desires nor fears.",
        "It's not what happens to you — it's how you respond.",
        "Control what is yours: your mind, your values, your actions.",
        "Virtue is the only true wealth.",
        "Endure and abstain.",
        "Life is not long or short — it depends on how we fill it.",
        "The wise man carries his home within himself.",
        "Let this not disturb you: everything passes.",
        "Act well now. The rest is vanity.",
        "The obstacle is the way.",
        "Prefer to be wrong with reason than right by chance.",
        "Death reminds us to live with purpose.",
        "Only the present is ours. The past and future are not.",
    ],
}


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
    # Geração de frases
    # ------------------------------------------------------------------

    def generate_phrases(self, categories: List[str] = None, count: int = 6,
                         language: str = "en-US") -> List[str]:
        """
        Generates `count` reflection/motivation phrases via DeepSeek.
        Falls back to local bank if API is unavailable.
        """
        categories = categories or list(FALLBACK_PHRASES.keys())

        if not self.available:
            return self._fallback_phrases(categories, count)

        cats_str = ", ".join(categories)
        system = (
            "You are a writer of inspirational phrases for lo-fi and relaxing "
            "YouTube channels. Your phrases are deep, poetic, and suitable "
            "for study and relaxation videos."
        )
        user = (
            f"Generate exactly {count} inspirational phrases in English. "
            f"Mix these categories: {cats_str}. "
            "Rules: max 60 characters each, one per line, "
            "no numbering, no quotes, no emojis. "
            "Prefer short and impactful phrases."
        )

        text = self._chat(system, user, max_tokens=count * 80, temperature=0.92)
        if not text:
            print("  [DeepSeek] Fallback para frases locais.")
            return self._fallback_phrases(categories, count)

        phrases = [line.strip() for line in text.splitlines() if line.strip()]
        phrases = [p for p in phrases if 5 < len(p) <= 80][:count]

        if len(phrases) < count:
            extra = self._fallback_phrases(categories, count - len(phrases))
            phrases.extend(extra)

        random.shuffle(phrases)
        return phrases[:count]

    def _fallback_phrases(self, categories: List[str], count: int) -> List[str]:
        pool: List[str] = []
        for cat in categories:
            pool.extend(FALLBACK_PHRASES.get(cat, []))
        if not pool:
            pool = [p for phrases in FALLBACK_PHRASES.values() for p in phrases]
        random.shuffle(pool)
        # Cycle if we need more than the pool has
        result: List[str] = []
        while len(result) < count:
            result.extend(pool)
        return result[:count]

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
