"""
Text Animator — Gera filtros FFmpeg drawtext para animações de frases em vídeos lo-fi.

5 estilos de animação profissionais:
  1. fade_center    — frase aparece/some no centro inferior com fade suave
  2. slide_left     — desliza da esquerda para o centro
  3. slide_bottom   — sobe do rodapé com fade
  4. glow_pulse     — pulsa em opacidade (efeito hipnótico, ideal lo-fi)
  5. cinematic      — barras cinemáticas + texto centralizado com fade

Extras:
  - progress_bar    — barra de progresso no rodapé (geq, compatível com qualquer FFmpeg)
  - track_display   — nome da faixa no canto inferior esquerdo
"""

import random
from pathlib import Path
from typing import List, Optional

# ---------------------------------------------------------------------------
# Detecção de fonte do sistema
# ---------------------------------------------------------------------------

_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
    "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    "/usr/share/fonts/opentype/cantarell/Cantarell-Bold.otf",
    "/usr/share/fonts/opentype/cantarell/Cantarell-Regular.otf",
    # macOS
    "/System/Library/Fonts/Helvetica.ttc",
    "/Library/Fonts/Arial Bold.ttf",
    # Windows
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
]


def find_system_font(override: str = "") -> str:
    """Retorna caminho da melhor fonte disponível."""
    if override and Path(override).exists():
        return override
    for f in _FONT_CANDIDATES:
        if Path(f).exists():
            return f
    return ""   # FFmpeg usa fonte embutida como fallback


# ---------------------------------------------------------------------------
# Utilitários de escape para drawtext
# ---------------------------------------------------------------------------

def _esc(text: str) -> str:
    """
    Escapa texto para uso no parâmetro `text=` do filtro drawtext do FFmpeg.
    Ordem importa: escape de backslash primeiro.
    """
    text = text.replace("\\", "\\\\")
    text = text.replace("'",  "\\'")
    text = text.replace(":",  "\\:")
    text = text.replace(",",  "\\,")
    text = text.replace(";",  "\\;")
    text = text.replace("%",  "%%")
    return text


def _font_arg(font_path: str) -> str:
    """Constrói o fragmento fontfile= ou string vazia."""
    if font_path and Path(font_path).exists():
        safe = font_path.replace("\\", "/").replace("'", "\\'").replace(":", "\\:")
        return f"fontfile='{safe}':"
    return ""


# ---------------------------------------------------------------------------
# Divisão de frase em linhas (max_chars por linha)
# ---------------------------------------------------------------------------

def _wrap_lines(text: str, max_chars: int = 42) -> List[str]:
    """Quebra texto longo em múltiplas linhas para caber na tela."""
    words = text.split()
    lines: List[str] = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        if len(test) <= max_chars:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [text]


# ---------------------------------------------------------------------------
# TextAnimator
# ---------------------------------------------------------------------------

class TextAnimator:
    """Constrói filtros FFmpeg drawtext para animações de texto profissionais."""

    def __init__(self, font_path: str = "", font_size: int = 54,
                 palette: Optional[dict] = None, max_chars: int = 42):
        self.font_path = find_system_font(font_path)
        self.base_font_size = font_size
        self.max_chars = max_chars
        self.palette = palette or {
            "text_primary": "0xFFF8E7",
            "text_shadow":  "0x1A0800@0.85",
            "accent":       "0xF5CBA7",
            "bar":          "0xF0B27A@0.60",
            "waves":        "0xF5CBA7@0.45",
            "box_bg":       "0x1A0A00@0.70",
        }

    # ------------------------------------------------------------------ #
    # Tamanho de fonte adaptado à resolução                               #
    # ------------------------------------------------------------------ #

    def _font_size(self, video_h: int) -> int:
        """Escala o tamanho da fonte proporcionalmente à altura do vídeo."""
        return max(24, int(self.base_font_size * video_h / 1080))

    def _small_font(self, video_h: int) -> int:
        return max(18, int(self.base_font_size * 0.55 * video_h / 1080))

    # ------------------------------------------------------------------ #
    # Filtros de frase (um por frase)                                     #
    # ------------------------------------------------------------------ #

    def build_phrase_filters(
        self,
        phrases: List[str],
        duration: float,
        video_w: int = 1920,
        video_h: int = 1080,
        display_duration: float = 9.0,
        fade_in: float = 0.9,
        fade_out: float = 0.9,
        styles: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Retorna lista de filtros drawtext (e drawbox para cinematic).
        Distribui as frases uniformemente ao longo do vídeo.
        """
        if not phrases:
            return []

        available_styles = styles or [
            "fade_center", "slide_left", "slide_bottom", "glow_pulse", "cinematic"
        ]

        # Distribui frases uniformemente, com margem de 15s no início/fim
        margin = min(15.0, duration * 0.05)
        usable = max(0.0, duration - 2 * margin)
        n = len(phrases)
        interval = usable / max(n, 1)

        filters: List[str] = []

        for i, phrase in enumerate(phrases):
            start = margin + i * interval + interval * 0.15
            end   = start + display_duration
            # Garante que não ultrapassa a duração do vídeo
            if start + fade_in >= duration - fade_out - 1:
                break
            end = min(end, duration - 1.0)
            if end <= start + fade_in + fade_out:
                continue

            style = random.choice(available_styles)
            fs = self._build_phrase(
                phrase, start, end, video_w, video_h, style, fade_in, fade_out
            )
            filters.extend(fs)

        return filters

    def _build_phrase(
        self,
        phrase: str,
        start: float,
        end: float,
        video_w: int,
        video_h: int,
        style: str,
        fade_in: float,
        fade_out: float,
    ) -> List[str]:
        """Constrói filtro(s) para uma única frase, no estilo dado."""
        dispatch = {
            "fade_center":  self._style_fade_center,
            "slide_left":   self._style_slide_left,
            "slide_bottom": self._style_slide_bottom,
            "glow_pulse":   self._style_glow_pulse,
            "cinematic":    self._style_cinematic,
        }
        fn = dispatch.get(style, self._style_fade_center)
        return fn(phrase, start, end, video_w, video_h, fade_in, fade_out)

    # ------------------------------------------------------------------ #
    # Expressão de alpha (fade in + fade out)                             #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _alpha_expr(start: float, end: float, fi: float, fo: float) -> str:
        """
        Alpha com fade in e fade out suaves.
        Clampado entre 0 e 1 para segurança.
        """
        fi = max(fi, 0.01)
        fo = max(fo, 0.01)
        return (
            f"if(lt(t-{start:.3f},{fi})"
            f",(t-{start:.3f})/{fi:.3f}"
            f",if(lt({end:.3f}-t,{fo})"
            f",({end:.3f}-t)/{fo:.3f}"
            f",1))"
        )

    # ------------------------------------------------------------------ #
    # Estilo 1: fade_center — fade simples no centro inferior             #
    # ------------------------------------------------------------------ #

    def _style_fade_center(self, phrase, start, end, w, h, fi, fo) -> List[str]:
        lines = _wrap_lines(phrase, self.max_chars)
        fs    = self._font_size(h)
        line_h = int(fs * 1.35)
        total_h = line_h * len(lines)
        base_y = int(h * 0.76) - total_h // 2
        fa    = _font_arg(self.font_path)
        color = self.palette["text_primary"]
        shadow = self.palette["text_shadow"]
        alpha = self._alpha_expr(start, end, fi, fo)

        filts = []
        for idx, line in enumerate(lines):
            y_pos = base_y + idx * line_h
            filts.append(
                f"drawtext={fa}"
                f"text='{_esc(line)}':"
                f"fontsize={fs}:fontcolor={color}:"
                f"x=(W-tw)/2:y={y_pos}:"
                f"shadowx=2:shadowy=2:shadowcolor={shadow}:"
                f"alpha='{alpha}':"
                f"enable='between(t,{start:.3f},{end:.3f})'"
            )
        return filts

    # ------------------------------------------------------------------ #
    # Estilo 2: slide_left — desliza da esquerda                          #
    # ------------------------------------------------------------------ #

    def _style_slide_left(self, phrase, start, end, w, h, fi, fo) -> List[str]:
        lines = _wrap_lines(phrase, self.max_chars)
        fs    = self._font_size(h)
        line_h = int(fs * 1.35)
        total_h = line_h * len(lines)
        base_y = int(h * 0.76) - total_h // 2
        fa    = _font_arg(self.font_path)
        color = self.palette["text_primary"]
        shadow = self.palette["text_shadow"]
        alpha = self._alpha_expr(start, end, fi, fo)
        slide_dur = min(fi + 0.4, (end - start) * 0.3)

        # x: parte de -tw (fora da tela) até (W-tw)/2 em slide_dur segundos
        x_expr = (
            f"if(lt(t-{start:.3f},{slide_dur:.3f})"
            f",-tw+((t-{start:.3f})/{slide_dur:.3f})*(W/2+tw/2)"
            f",W/2-tw/2)"
        )

        filts = []
        for idx, line in enumerate(lines):
            y_pos = base_y + idx * line_h
            filts.append(
                f"drawtext={fa}"
                f"text='{_esc(line)}':"
                f"fontsize={fs}:fontcolor={color}:"
                f"x='{x_expr}':y={y_pos}:"
                f"shadowx=2:shadowy=2:shadowcolor={shadow}:"
                f"alpha='{alpha}':"
                f"enable='between(t,{start:.3f},{end:.3f})'"
            )
        return filts

    # ------------------------------------------------------------------ #
    # Estilo 3: slide_bottom — sobe do rodapé                             #
    # ------------------------------------------------------------------ #

    def _style_slide_bottom(self, phrase, start, end, w, h, fi, fo) -> List[str]:
        lines = _wrap_lines(phrase, self.max_chars)
        fs    = self._font_size(h)
        line_h = int(fs * 1.35)
        total_h = line_h * len(lines)
        base_y = int(h * 0.76) - total_h // 2
        fa    = _font_arg(self.font_path)
        color = self.palette["text_primary"]
        shadow = self.palette["text_shadow"]
        alpha = self._alpha_expr(start, end, fi, fo)
        slide_dur = min(fi + 0.5, (end - start) * 0.3)

        filts = []
        for idx, line in enumerate(lines):
            target_y = base_y + idx * line_h
            # sobe de H+20 até target_y em slide_dur segundos
            y_expr = (
                f"if(lt(t-{start:.3f},{slide_dur:.3f})"
                f",H+20+((t-{start:.3f})/{slide_dur:.3f})*({target_y}-H-20)"
                f",{target_y})"
            )
            filts.append(
                f"drawtext={fa}"
                f"text='{_esc(line)}':"
                f"fontsize={fs}:fontcolor={color}:"
                f"x=(W-tw)/2:y='{y_expr}':"
                f"shadowx=2:shadowy=2:shadowcolor={shadow}:"
                f"alpha='{alpha}':"
                f"enable='between(t,{start:.3f},{end:.3f})'"
            )
        return filts

    # ------------------------------------------------------------------ #
    # Estilo 4: glow_pulse — pulsa em opacidade ao ritmo da música        #
    # ------------------------------------------------------------------ #

    def _style_glow_pulse(self, phrase, start, end, w, h, fi, fo) -> List[str]:
        lines = _wrap_lines(phrase, self.max_chars)
        fs    = self._font_size(h)
        line_h = int(fs * 1.35)
        total_h = line_h * len(lines)
        base_y = int(h * 0.76) - total_h // 2
        fa    = _font_arg(self.font_path)
        color = self.palette["text_primary"]
        accent = self.palette["accent"]
        shadow = self.palette["text_shadow"]

        # Pulse entre 0.6 e 1.0 a 0.45 Hz, com fade in/out envelope
        envelope = self._alpha_expr(start, end, fi, fo)
        pulse_alpha = f"({envelope})*(0.70+0.30*sin(2*3.14159*0.45*t))"

        filts = []
        for idx, line in enumerate(lines):
            y_pos = base_y + idx * line_h
            # Sombra glow colorida (accent) + texto branco em cima
            filts.append(
                f"drawtext={fa}"
                f"text='{_esc(line)}':"
                f"fontsize={fs}:fontcolor={accent}:"
                f"x=(W-tw)/2:y={y_pos}:"
                f"shadowx=0:shadowy=0:shadowcolor={shadow}:"
                f"borderw=3:bordercolor={accent}:"
                f"alpha='{pulse_alpha}':"
                f"enable='between(t,{start:.3f},{end:.3f})'"
            )
            filts.append(
                f"drawtext={fa}"
                f"text='{_esc(line)}':"
                f"fontsize={fs}:fontcolor={color}:"
                f"x=(W-tw)/2:y={y_pos}:"
                f"shadowx=2:shadowy=2:shadowcolor={shadow}:"
                f"alpha='{envelope}':"
                f"enable='between(t,{start:.3f},{end:.3f})'"
            )
        return filts

    # ------------------------------------------------------------------ #
    # Estilo 5: cinematic — barras pretas + texto centralizado            #
    # ------------------------------------------------------------------ #

    def _style_cinematic(self, phrase, start, end, w, h, fi, fo) -> List[str]:
        lines = _wrap_lines(phrase, self.max_chars)
        fs    = self._font_size(h)
        line_h = int(fs * 1.45)
        total_h = line_h * len(lines)
        base_y = (h - total_h) // 2  # centro vertical exato
        fa    = _font_arg(self.font_path)
        color = self.palette["text_primary"]
        shadow = self.palette["text_shadow"]
        box_bg = self.palette["box_bg"]
        alpha = self._alpha_expr(start, end, fi, fo)

        bar_h = int(h * 0.13)

        filts = [
            # Barra superior
            f"drawbox=x=0:y=0:w=W:h={bar_h}:color={box_bg}:t=fill:"
            f"enable='between(t,{start:.3f},{end:.3f})'",
            # Barra inferior
            f"drawbox=x=0:y=H-{bar_h}:w=W:h={bar_h}:color={box_bg}:t=fill:"
            f"enable='between(t,{start:.3f},{end:.3f})'",
        ]
        for idx, line in enumerate(lines):
            y_pos = base_y + idx * line_h
            filts.append(
                f"drawtext={fa}"
                f"text='{_esc(line)}':"
                f"fontsize={fs}:fontcolor={color}:"
                f"x=(W-tw)/2:y={y_pos}:"
                f"shadowx=3:shadowy=3:shadowcolor={shadow}:"
                f"alpha='{alpha}':"
                f"enable='between(t,{start:.3f},{end:.3f})'"
            )
        return filts

    # ------------------------------------------------------------------ #
    # Progress Bar (usando geq para suporte dinâmico a qualquer FFmpeg)   #
    # ------------------------------------------------------------------ #

    def build_progress_bar(self, duration: float, video_h: int,
                           height_px: int = 3, opacity: float = 0.55) -> str:
        """
        Barra de progresso no rodapé que cresce com o tempo.
        Usa geq (funciona em qualquer versão FFmpeg com suporte a geq).
        """
        # Converte opacidade em valor 0-255 para canal alpha
        a_val = int(opacity * 255)
        bar_color = self.palette.get("bar", "0xF0B27A@0.60")
        # Extrai hex RGB da paleta (ignora @alpha se presente)
        hex_col = bar_color.split("@")[0].replace("0x", "").replace("#", "")
        if len(hex_col) == 6:
            r = int(hex_col[0:2], 16)
            g = int(hex_col[2:4], 16)
            b = int(hex_col[4:6], 16)
        else:
            r, g, b = 240, 178, 122  # warm_amber fallback

        # geq desenha pixels brancos na última faixa de height_px pixels
        # onde x < W * (t/duration)
        dur = max(duration, 1.0)
        return (
            f"geq="
            f"r='if(gt(Y\\,H-{height_px+1})*lt(X\\,W*min(t/{dur:.3f}\\,1.0)\\)\\,{r}\\,r(X\\,Y\\)\\)':"
            f"g='if(gt(Y\\,H-{height_px+1})*lt(X\\,W*min(t/{dur:.3f}\\,1.0)\\)\\,{g}\\,g(X\\,Y\\)\\)':"
            f"b='if(gt(Y\\,H-{height_px+1})*lt(X\\,W*min(t/{dur:.3f}\\,1.0)\\)\\,{b}\\,b(X\\,Y\\)\\)'"
        )

    # ------------------------------------------------------------------ #
    # Track Display (nome da faixa musical)                               #
    # ------------------------------------------------------------------ #

    def build_track_display(self, track_name: str, video_h: int,
                            display_duration: float = 7.0,
                            fade_s: float = 1.0) -> str:
        """
        Exibe o nome da faixa no canto inferior esquerdo por `display_duration` segundos.
        """
        fs = self._small_font(video_h)
        fa = _font_arg(self.font_path)
        color = self.palette["text_primary"]
        shadow = self.palette["text_shadow"]

        # Limpa nome: remove extensão, substitui _ e - por espaços
        name = Path(track_name).stem
        name = name.replace("_", " ").replace("-", " ").strip()
        if len(name) > 40:
            name = name[:37] + "..."

        start = 1.5
        end   = start + display_duration
        alpha = self._alpha_expr(start, end, fade_s, fade_s)

        return (
            f"drawtext={fa}"
            f"text='♪  {_esc(name)}':"
            f"fontsize={fs}:fontcolor={color}:"
            f"x=20:y=H-{fs+20}:"
            f"shadowx=1:shadowy=1:shadowcolor={shadow}:"
            f"alpha='{alpha}':"
            f"enable='between(t,{start:.1f},{end:.1f})'"
        )

    # ------------------------------------------------------------------ #
    # Construtor do filtro completo de texto (para encadear em filter_complex)
    # ------------------------------------------------------------------ #

    def build_full_text_chain(
        self,
        phrases: List[str],
        duration: float,
        video_w: int,
        video_h: int,
        track_name: str = "",
        display_duration: float = 9.0,
        fade_in: float = 0.9,
        fade_out: float = 0.9,
        styles: Optional[List[str]] = None,
        progress_bar: bool = True,
        progress_height: int = 3,
    ) -> List[str]:
        """
        Retorna lista completa de filtros (drawtext + drawbox + geq)
        prontos para encadear em filter_complex.
        """
        filters: List[str] = []

        # Frases
        filters.extend(self.build_phrase_filters(
            phrases=phrases,
            duration=duration,
            video_w=video_w,
            video_h=video_h,
            display_duration=display_duration,
            fade_in=fade_in,
            fade_out=fade_out,
            styles=styles,
        ))

        # Track name
        if track_name:
            filters.append(self.build_track_display(track_name, video_h))

        # Progress bar
        if progress_bar:
            filters.append(self.build_progress_bar(duration, video_h, progress_height))

        return filters
