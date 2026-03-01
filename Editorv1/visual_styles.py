"""
Visual Style Presets — Lo-fi / Relaxing / Study / Shorts

Define grão, vinheta, color grading, paleta de cores e parâmetros
de visualizador de áudio para cada estilo de vídeo.
"""

from typing import Dict, Any

# ---------------------------------------------------------------------------
# Paletas de cores (text_primary, text_shadow, accent, bar)
# Formato: cores hexadecimais compatíveis com FFmpeg drawtext/drawbox
# ---------------------------------------------------------------------------

COLOR_PALETTES: Dict[str, Dict[str, str]] = {
    "warm_amber": {
        "text_primary":  "0xFFF8E7",
        "text_shadow":   "0x1A0800@0.85",
        "accent":        "0xF5CBA7",
        "bar":           "0xF0B27A@0.60",
        "waves":         "0xF5CBA7@0.45",
        "box_bg":        "0x1A0A00@0.70",
    },
    "cool_blue": {
        "text_primary":  "0xE8F8FF",
        "text_shadow":   "0x050F1A@0.85",
        "accent":        "0xAED6F1",
        "bar":           "0x85C1E9@0.60",
        "waves":         "0xAED6F1@0.45",
        "box_bg":        "0x040C14@0.70",
    },
    "neon_purple": {
        "text_primary":  "0xFFE8F8",
        "text_shadow":   "0x1A0020@0.90",
        "accent":        "0xFF6EC7",
        "bar":           "0xC39BD3@0.60",
        "waves":         "0xFF6EC7@0.50",
        "box_bg":        "0x150010@0.75",
    },
    "forest_green": {
        "text_primary":  "0xEAF9E7",
        "text_shadow":   "0x050F02@0.85",
        "accent":        "0x82E0AA",
        "bar":           "0x58D68D@0.60",
        "waves":         "0x82E0AA@0.45",
        "box_bg":        "0x030A02@0.70",
    },
    "tokyo_night": {
        "text_primary":  "0xF0F0FF",
        "text_shadow":   "0x000008@0.90",
        "accent":        "0x7B68EE",
        "bar":           "0x9B59B6@0.60",
        "waves":         "0x7B68EE@0.50",
        "box_bg":        "0x040004@0.75",
    },
}


# ---------------------------------------------------------------------------
# Estilos Visuais
# ---------------------------------------------------------------------------

VISUAL_STYLES: Dict[str, Dict[str, Any]] = {
    "lofi": {
        # Grão de filme (noise strength 0-25)
        "grain_strength": 7,
        # Vinheta FFmpeg (ângulo PI/x: menor = mais vinheta)
        "vignette": True,
        "vignette_angle": "PI/4",
        # Correção de cor (FFmpeg eq filter)
        "color_eq": "eq=brightness=-0.03:contrast=1.06:saturation=0.82:gamma=1.08",
        # Zoom ultra-lento via crop (escala de overscan: ex. 1.04 = 4% maior)
        "overscan": 1.04,
        # Paleta de cores
        "palette": "warm_amber",
        # Waveform visualizer
        "waves_mode": "cline",
        "waves_scale": "sqrt",
        # Duração mínima de clip para este modo (s)
        "clip_min_s": 300,
    },
    "relaxing": {
        "grain_strength": 3,
        "vignette": True,
        "vignette_angle": "PI/5",
        "color_eq": "eq=brightness=0.01:contrast=1.03:saturation=1.05:gamma=0.97",
        "overscan": 1.03,
        "palette": "cool_blue",
        "waves_mode": "cline",
        "waves_scale": "lin",
        "clip_min_s": 300,
    },
    "study": {
        "grain_strength": 1,
        "vignette": True,
        "vignette_angle": "PI/6",
        "color_eq": "eq=brightness=0.00:contrast=1.02:saturation=0.92:gamma=1.00",
        "overscan": 1.02,
        "palette": "warm_amber",
        "waves_mode": "p2p",
        "waves_scale": "sqrt",
        "clip_min_s": 600,
    },
    "shorts": {
        "grain_strength": 6,
        "vignette": True,
        "vignette_angle": "PI/4",
        "color_eq": "eq=brightness=-0.02:contrast=1.08:saturation=0.87:gamma=1.06",
        "overscan": 1.05,
        "palette": "neon_purple",
        "waves_mode": "cline",
        "waves_scale": "log",
        "clip_min_s": 20,
    },
}


def get_style(mode: str) -> Dict[str, Any]:
    """Retorna o estilo visual para o modo dado. Fallback para 'lofi'."""
    return VISUAL_STYLES.get(mode, VISUAL_STYLES["lofi"])


def get_palette(style_name: str) -> Dict[str, str]:
    """Retorna a paleta de cores para um nome de estilo visual."""
    style = VISUAL_STYLES.get(style_name, VISUAL_STYLES["lofi"])
    palette_name = style.get("palette", "warm_amber")
    return COLOR_PALETTES.get(palette_name, COLOR_PALETTES["warm_amber"])
