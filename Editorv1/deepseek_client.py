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
    "reflexao": [
        "O silêncio é a música da alma.",
        "Quem olha para fora, sonha. Quem olha para dentro, desperta.",
        "A vida é um eco: o que você envia, volta para você.",
        "Conhece-te a ti mesmo e conhecerás o universo.",
        "O tempo que perdemos é o tempo que não vivemos.",
        "Cada amanhecer é um convite para recomeçar.",
        "A profundidade de uma mente se mede pelo seu silêncio.",
        "Somos feitos do mesmo material que os sonhos.",
        "A água que passa não move o moinho.",
        "Viver é a coisa mais rara do mundo. A maioria apenas existe.",
        "O caminho se faz caminhando.",
        "Nada é permanente exceto a mudança.",
        "A alma que contempla é a alma que transforma.",
        "Nas pequenas coisas reside a grandeza.",
        "O universo é infinito dentro de nós.",
    ],
    "motivacao": [
        "Um passo de cada vez constrói a jornada de mil milhas.",
        "A persistência é o caminho do êxito.",
        "Não espere o momento perfeito. Tome o momento e torne-o perfeito.",
        "O segredo para avançar é começar.",
        "Sua única limitação é a que você aceita.",
        "Grandes conquistas nascem de pequenas ações diárias.",
        "Acredite que você pode e você já está na metade do caminho.",
        "O fracasso é apenas a oportunidade de recomeçar com mais sabedoria.",
        "Você é mais forte do que imagina.",
        "A coragem não é ausência de medo, é agir apesar dele.",
        "Faça o que você pode, com o que você tem, onde você está.",
        "O futuro pertence a quem acredita na beleza de seus sonhos.",
        "Cada dia é uma nova chance de crescer.",
        "Não desista. Grandes coisas levam tempo.",
        "O esforço de hoje é o resultado de amanhã.",
    ],
    "mindfulness": [
        "Respire. Este momento é tudo que existe.",
        "Esteja presente. A vida acontece agora.",
        "A paz não é a ausência de caos, é a calma dentro dele.",
        "Cada respiração é um recomeço.",
        "Solte o que não pode mudar. Abrace o que pode.",
        "A atenção plena transforma o ordinário em extraordinário.",
        "Observe seus pensamentos como nuvens passando.",
        "O presente é o único tempo em que você tem poder.",
        "Você não precisa de mais tempo, apenas de mais presença.",
        "Quando você desacelera, a vida se expande.",
        "Pare. Sinta. Agradeça.",
        "O corpo sabe o que a mente esqueceu.",
        "Em cada momento há uma escolha: reagir ou responder.",
        "A calma é um superpoder.",
        "Simplifique. O suficiente é abundante.",
    ],
    "positividade": [
        "A gratidão transforma o que temos em suficiente.",
        "Pequenas alegrias constroem uma vida grande.",
        "Você irradia o que cultiva por dentro.",
        "A bondade é uma linguagem que todos entendem.",
        "Sorrir é a maneira mais curta de conectar dois corações.",
        "O amanhã será melhor porque você está aqui hoje.",
        "Há beleza esperando ser notada em cada detalhe.",
        "A energia que você oferece é a energia que você recebe.",
        "Cada dia tem vinte e quatro horas de possibilidades.",
        "Você é um milagre em movimento.",
        "A vida é curta demais para não ser gentil.",
        "Celebre o caminho, não apenas o destino.",
        "Há sempre algo pelo qual ser grato.",
        "Você é exatamente onde precisa estar.",
        "A felicidade é uma prática diária, não um destino.",
    ],
    "estoicismo": [
        "Não procures que os acontecimentos sejam como desejas. Aceita-os como são.",
        "O homem sábio não sente falta do que não tem.",
        "A tranquilidade é encontrada em quem não deseja nem teme nada.",
        "Não é o que acontece com você, mas como você responde.",
        "Controla o que é teu: a tua mente, os teus valores, a tua ação.",
        "A virtude é a única riqueza verdadeira.",
        "Suporta e abstém-te.",
        "A vida não é longa ou curta por si só, mas como a preenchemos.",
        "O sábio carrega seu próprio lar dentro de si.",
        "Que isso não te perturbe: tudo passa.",
        "Age bem agora. O resto é vaidade.",
        "O obstáculo é o caminho.",
        "Prefere estar errado com a razão a estar certo por acaso.",
        "A morte lembra-nos de viver com propósito.",
        "Apenas o presente é nosso. O passado e o futuro, não.",
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
                         language: str = "pt-BR") -> List[str]:
        """
        Gera `count` frases de reflexão/motivação via DeepSeek.
        Fallback para banco local se API falhar.
        """
        categories = categories or list(FALLBACK_PHRASES.keys())

        if not self.available:
            return self._fallback_phrases(categories, count)

        cats_str = ", ".join(categories)
        system = (
            "Você é um escritor de frases inspiradoras para canais de YouTube "
            "no estilo lo-fi e relaxing. Suas frases são profundas, poéticas e "
            "adequadas para aparecer em vídeos de estudo e relaxamento."
        )
        user = (
            f"Gere exatamente {count} frases inspiradoras em {language}. "
            f"Categorias (misture): {cats_str}. "
            "Regras: cada frase com no máximo 60 caracteres, uma por linha, "
            "sem numeração, sem aspas, sem emojis. "
            "Prefira frases curtas e impactantes."
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
                                  duration_min: int, language: str = "pt-BR") -> Dict:
        """
        Gera título, descrição e tags para o vídeo no YouTube.
        """
        default = self._default_metadata(style, duration_min)

        if not self.available:
            return default

        sample = phrases[:3] if phrases else ["música relaxante", "lo-fi", "estudo"]
        sample_str = " | ".join(sample)

        system = (
            "Você é especialista em SEO para canais de YouTube no nicho lo-fi, "
            "relaxing e study music. Cria títulos atrativos e descrições que geram "
            "cliques e retenção."
        )
        user = (
            f"Crie metadados para um vídeo YouTube em {language}:\n"
            f"- Estilo: {style}\n"
            f"- Duração: {duration_min} minutos\n"
            f"- Frases do vídeo: {sample_str}\n\n"
            "Responda APENAS em JSON válido com este formato:\n"
            '{"title": "...", "description": "...", "tags": ["tag1", "tag2", ...]}\n\n'
            "Regras: título com 50-70 chars, descrição com 400-600 chars "
            f"em {language}, 15-20 tags relevantes em inglês e {language}."
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
