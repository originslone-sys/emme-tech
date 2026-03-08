"""
DeepSeek API Client — Geração de metadados YouTube para vídeos evergreen.

Usa apenas stdlib (urllib). Não requer pacotes externos.
Fallback automático para metadados padrão se a API falhar.
"""

import json
import random
import urllib.error
import urllib.request
from typing import Dict, List, Optional

# Ângulos criativos injetados no prompt para forçar variação de título a cada geração
_TITLE_ANGLES = [
    "a specific cozy scenario (late night rain, empty library at 3am, foggy morning coffee)",
    "an emotional transformation (scattered → laser-focused, anxious → completely calm)",
    "a vivid aesthetic reference (Studio Ghibli mood, Tokyo midnight, Parisian café corner)",
    "a bold promise or claim (the only playlist you'll need this week, your unfair focus advantage)",
    "a time or ritual anchor (Sunday reset session, golden hour deep work, pre-dawn grind)",
    "a contrast or paradox (loud world / silent mind, beautifully boring, productive solitude)",
    "a challenge or direct invitation (work to this for 60 min — no breaks, your brain will thank you)",
    "a sensory detail (the sound of rain on glass, warm lamp light, worn-out headphones on)",
    "a cultural or community nod (for the night owls, for the overthinkers, for the deep workers)",
    "an aspirational identity statement (this is what disciplined people listen to)",
]

# Hooks de abertura para variar o começo da descrição
_DESC_HOOKS = [
    "Close your eyes for one second. Feel that? That's your brain finally exhaling.",
    "Some playlists are just music. This one is a complete focus environment.",
    "Your most productive session starts right now.",
    "3AM. Just you, your work, and zero distractions.",
    "Tired of playlists that interrupt your flow? This one doesn't.",
    "Not background noise — a precision-crafted focus tool.",
    "The world is loud. Your work session doesn't have to be.",
    "Built for the ones who don't quit until it's done.",
    "Turn this on. Close every tab. Begin.",
    "Your brain is craving structure. This is it.",
]


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
        """Gera título, descrição e tags para upload no YouTube."""
        default = self._default_metadata(style, duration_min)

        if not self.available:
            return default

        angle = random.choice(_TITLE_ANGLES)
        hook  = random.choice(_DESC_HOOKS)
        _rem = duration_min % 60
        dur_h = (f"{duration_min // 60}h {_rem}min" if _rem else f"{duration_min // 60}h") if duration_min >= 60 else f"{duration_min} minutes"

        system = (
            "You are the creative director of one of YouTube's top lo-fi channels "
            "with 9 million subscribers. You have mastered YouTube SEO, CTR optimization, "
            "and emotional copywriting. Your titles consistently achieve 9-13% CTR. "
            "You NEVER write generic titles like 'Relax and Study Music'. "
            "Every title is specific, visual, emotionally resonant, and scroll-stopping. "
            "Your descriptions are structured to hold watch time and trigger the recommendation algorithm."
        )

        user = (
            f"Generate YouTube metadata for a {style} music video ({dur_h} long).\n\n"
            f"CREATIVE DIRECTION (mandatory — this makes each video unique):\n"
            f"- Title angle: {angle}\n"
            f"- Description must open with this hook (adapt slightly if needed): \"{hook}\"\n\n"
            f"STRICT RULES:\n"
            f"- Title: 52-68 characters. NO emojis. NO generic phrases. "
            f"Make it specific, atmospheric, and irresistible to click.\n"
            f"- Description: 520-680 characters structured as:\n"
            f"  1. Hook (1-2 punchy lines)\n"
            f"  2. What they'll experience (2-3 lines, vivid and specific)\n"
            f"  3. Best use cases + listening tip (2 lines)\n"
            f"  4. Subscribe CTA (1 line)\n"
            f"  5. 12-15 hashtags on the last line\n"
            f"- Tags: 22-27 tags. Mix: 8 high-volume broad tags + 10 long-tail specific tags "
            f"+ 4 trending/niche tags. No commas inside individual tags.\n"
            f"- Language: English (EN-US)\n\n"
            "Reply ONLY with valid JSON:\n"
            '{"title": "...", "description": "...", "tags": ["tag1", "tag2", ...]}'
        )

        text = self._chat(system, user, max_tokens=950, temperature=1.0)
        if not text:
            return default

        try:
            start = text.find("{")
            end   = text.rfind("}") + 1
            data  = json.loads(text[start:end])
            return {
                "title":       str(data.get("title",       default["title"]))[:100],
                "description": str(data.get("description", default["description"]))[:2000],
                "tags":        [str(t) for t in data.get("tags", default["tags"])][:30],
            }
        except Exception:
            return default

    def _default_metadata(self, style: str, duration_min: int) -> Dict:
        """Fallback com múltiplas variações — nunca retorna o mesmo título duas vezes."""
        _rem = duration_min % 60
        dur_h = (f"{duration_min // 60}h {_rem}min" if _rem else f"{duration_min // 60}h") if duration_min >= 60 else f"{duration_min} minutes"

        title_pool = {
            "lofi": [
                f"Late Night Lofi — {dur_h} of Uninterrupted Deep Focus",
                f"Coffee Shop Beats — {dur_h} to Study, Work & Disappear Into",
                f"Rainy Window Lofi — {dur_h} of Pure Concentration",
                f"3AM Study Session — Lofi Beats for the Night Owls ({dur_h})",
                f"Quiet Hours — {dur_h} of Lofi Hip Hop for Deep Work",
            ],
            "relaxing": [
                f"Still Water — {dur_h} of Healing Ambient Music",
                f"Breathe Slowly — {dur_h} of Pure Calm for an Overloaded Mind",
                f"Soft Light — {dur_h} of Restorative Music for Rest and Peace",
                f"The Quiet Room — {dur_h} of Ambient Sound for Deep Relaxation",
                f"Golden Hour Calm — {dur_h} of Peaceful Atmospheric Music",
            ],
            "study": [
                f"Locked In — {dur_h} of Deep Work Music for Maximum Output",
                f"Zero Distractions — {dur_h} of Pure Focus Frequency",
                f"The Study Room — {dur_h} of Concentration Music with No Breaks",
                f"Brain on Fire — {dur_h} of Instrumental Study Music",
                f"Flow State — {dur_h} of Music Engineered for Deep Thinking",
            ],
            "shorts": [
                "60 Seconds of Calm. Your Brain Needed This.",
                "Take One Breath. This is Your Reset.",
                "The Lofi Feeling — in 60 Seconds",
                "One Minute of Pure Focus. Ready?",
                "This is What Silence Sounds Like.",
            ],
        }

        desc_pool = [
            (
                f"Turn this on. Close every tab. Begin.\n\n"
                f"{dur_h} of {style} music with zero interruptions — built for deep work, "
                f"creative flow, and the kind of focus that makes hours feel like minutes.\n\n"
                f"Best with headphones in a quiet room. Bookmark this for your next session.\n\n"
                f"Subscribe for a new session every week.\n\n"
                f"#lofi #studymusic #focusmusic #deepwork #chillbeats #instrumental "
                f"#concentration #ambientmusic #{style} #lofihiphop #noads #workmusic "
                f"#productivitymusic #relaxingmusic #flowstate"
            ),
            (
                f"Your brain is craving structure. This is it.\n\n"
                f"{dur_h} of carefully crafted {style} music — no ads breaking your rhythm, "
                f"no jarring transitions, just one continuous stream of focus-ready sound.\n\n"
                f"Perfect for: studying, coding, writing, late-night work sessions.\n"
                f"Pro tip: start a timer. You'll be surprised how much you get done.\n\n"
                f"New sessions uploaded weekly — subscribe so you never run out.\n\n"
                f"#lofi #lofihiphop #{style} #studymusic #focusmusic #chillhop "
                f"#instrumentalmusic #concentration #deepfocus #ambientmusic "
                f"#backgroundmusic #workmusic #relaxingmusic #nolyrics #studysession"
            ),
        ]

        tags = [
            "lofi", "lo-fi hip hop", "study music", "focus music", "chill beats",
            "relaxing music", "instrumental music", "no lyrics", "lofi hip hop radio",
            "beats to study to", "concentration music", "deep focus music",
            "ambient music", "background music for studying", style, f"{style} music",
            "lofi beats", "chillhop", "music for coding", "work music",
            "productivity music", "lofi study session", "focus frequency",
        ]
        random.shuffle(tags)

        return {
            "title":       random.choice(title_pool.get(style, title_pool["lofi"])),
            "description": random.choice(desc_pool),
            "tags":        tags[:20],
        }
