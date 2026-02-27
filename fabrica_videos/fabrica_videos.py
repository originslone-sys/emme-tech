import argparse
import random
import subprocess
import sys
import textwrap
import time
import hashlib
from pathlib import Path
from typing import Optional, List, Tuple

import requests

DEFAULT_API_URL = "https://emmetech.digital/api/receber_video.php"
DEFAULT_API_KEY  = "a4aLYTawyy4HEUGQIoHCSjDOtSrxh4SA"

# Fontes: Windows, Linux e macOS (primeira encontrada é usada)
FONT_PATHS = [
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\Arial.ttf",
    r"C:\Windows\Fonts\calibri.ttf",
    r"C:\Windows\Fonts\Calibri.ttf",
    r"C:\Windows\Fonts\verdana.ttf",
    r"C:\Windows\Fonts\Verdana.ttf",
    r"C:\Windows\Fonts\tahoma.ttf",
    r"C:\Windows\Fonts\Tahoma.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/Library/Fonts/Arial.ttf",
    "/System/Library/Fonts/SFNSDisplay.ttf",
]

FRASES_MOTIVACIONAIS = [
    "A tempestade não dura para sempre.", "Seu limite é você quem define.", "Cair faz parte. Levantar é a glória.",
    "Respira fundo e recomeça.", "Dor temporária, desistência eterna.", "Não desista do seu começo.",
    "Você é mais forte do que acha.", "Faça acontecer, mesmo com medo.", "O não você já tem, busque o sim.",
    "Coragem é sentir medo e ir mesmo assim.", "Levanta a cabeça e segue o jogo.", "A sua força está na sua fé.",
    "Tudo passa, até isso.", "Um dia de cada vez.", "Não pare quando estiver cansado, pare quando terminar.",
    "Você sobreviveu 100% dos seus dias ruins.", "Transforme pedras em degraus.", "O caminho é difícil, mas a vista é linda.",
    "Seu passado não define seu futuro.", "Levanta, sacode a poeira e dá a volta por cima.", "Acredite no seu taco.",
    "Você é o suficiente.", "Não se compare, se admire.", "Abraça seus defeitos e brilha.", "Ninguém faz igual a você.",
    "Seu valor não depende de opinião alheia.", "Olha no espelho e se orgulha.", "Você é única(o), ponto final.",
    "Pare de duvidar de você.", "Confia no processo e em si mesmo.", "A sua vibe atrai sua tribo.",
    "Seja sua maior prioridade.", "Cala a boca da insegurança.", "Você pode mais do que imagina.", "Se ame em primeiro lugar.",
    "Ninguém anda na sua velocidade.", "Seu jeito é o seu sucesso.", "Não peça licença para existir.", "Acredite, você é incrível.",
    "Cada dia é uma nova chance.", "Pequenos passos também levam longe.", "Não existe fracasso, só aprendizado.",
    "Você foi feito para vencer.", "Nada te para quando você crê.", "Silêncio e foco: a fórmula do sucesso.",
]

TEXT_POSITIONS = [
    "x=(w-text_w)/2:y=h-(h/4)",
    "x=(w-text_w)/2:y=(h/10)",
    "x=20:y=h-(h/4)",
    "x=(w-text_w)-20:y=h-(h/4)",
    "x=(w-text_w)/2:y=(h/2)-(text_h/2)",
]

TEXT_COLORS = ["white", "yellow", "white@0.92", "cyan@0.90"]

AUDIO_EQ_OPTIONS: List[List[str]] = [
    [],
    ["equalizer=f=80:width_type=o:width=2:g=-2.0"],
    ["equalizer=f=10000:width_type=o:width=2:g=1.5"],
    ["equalizer=f=3500:width_type=o:width=2:g=1.2"],
    ["equalizer=f=200:width_type=o:width=2:g=1.5"],
    ["equalizer=f=80:width_type=o:width=2:g=-1.5",
     "equalizer=f=8000:width_type=o:width=2:g=1.0"],
]

VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi", ".flv", ".wmv"}

# Cache para encoder de hardware (evita rodar o teste a cada vídeo)
_HW_ENCODER_CACHE: Optional[str] = None


# ──────────────────────────────────────────────
# UTILITÁRIOS
# ──────────────────────────────────────────────

def _ff_path(p: Path) -> str:
    s = str(p.resolve()).replace("\\", "/")
    s = s.replace(":", r"\:")
    return s


def _find_font() -> Optional[Path]:
    for fp in FONT_PATHS:
        p = Path(fp)
        if p.exists():
            return p
    return None


def calcular_hash_arquivo(arquivo: Path, algoritmo: str = "md5") -> str:
    hash_obj = hashlib.new(algoritmo)
    with arquivo.open("rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()


def tem_audio(arquivo_video: Path) -> bool:
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "a",
        "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(arquivo_video)
    ]
    try:
        return "audio" in subprocess.check_output(cmd, text=True).strip().lower()
    except Exception:
        return False


def obter_info_video(arquivo_video: Path) -> dict:
    info: dict = {}
    try:
        res = subprocess.check_output(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height", "-of", "csv=p=0", str(arquivo_video)],
            text=True
        ).strip().split(",")
        if len(res) == 2:
            info["width"], info["height"] = int(res[0]), int(res[1])
    except Exception:
        info["width"], info["height"] = 1920, 1080

    try:
        fps_str = subprocess.check_output(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=r_frame_rate",
             "-of", "default=noprint_wrappers=1:nokey=1", str(arquivo_video)],
            text=True
        ).strip()
        if "/" in fps_str:
            n, d = map(int, fps_str.split("/"))
            info["fps"] = n / d if d else 30.0
        else:
            info["fps"] = float(fps_str) if fps_str else 30.0
    except Exception:
        info["fps"] = 30.0

    try:
        info["codec"] = subprocess.check_output(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=codec_name",
             "-of", "default=noprint_wrappers=1:nokey=1", str(arquivo_video)],
            text=True
        ).strip()
    except Exception:
        info["codec"] = "h264"

    return info


def obter_duracao(arquivo_video: Path) -> float:
    """Retorna a duração do vídeo em segundos via ffprobe."""
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(arquivo_video)
    ]
    try:
        val = subprocess.check_output(cmd, text=True, timeout=15).strip()
        return float(val) if val else 0.0
    except Exception:
        return 0.0


def detect_hw_encoder() -> str:
    """
    Detecta encoder de vídeo via hardware (NVENC → AMF → libx264).
    Testa codificando um frame 32x32 de 0.1s.
    Resultado fica em cache de módulo.
    """
    global _HW_ENCODER_CACHE
    if _HW_ENCODER_CACHE is not None:
        return _HW_ENCODER_CACHE

    for encoder in ["h264_nvenc", "h264_amf"]:
        try:
            r = subprocess.run(
                ["ffmpeg", "-y", "-f", "lavfi",
                 "-i", "color=black:size=32x32:duration=0.1",
                 "-c:v", encoder, "-f", "null", "-"],
                capture_output=True, timeout=8
            )
            if r.returncode == 0:
                _HW_ENCODER_CACHE = encoder
                print(f"[GPU] Encoder de hardware ativo: {encoder}")
                return encoder
        except Exception:
            pass

    _HW_ENCODER_CACHE = "libx264"
    return "libx264"


# ──────────────────────────────────────────────
# REORDENAÇÃO DE CENAS
# ──────────────────────────────────────────────

def _build_scene_reorder(
    n_segs: int,
    perm: List[int],
    duracao: float,
    video_tem_audio: bool,
) -> Tuple[List[str], str, Optional[str]]:
    """
    Gera partes do filter_complex para reordenar segmentos do vídeo (e áudio).

    Retorna (fc_parts, vsrc_label, asrc_label).
      - vsrc_label: label de saída do vídeo reordenado (ex: 'vcombined')
      - asrc_label: label de saída do áudio reordenado, ou None
    """
    parts: List[str] = []
    seg_dur = duracao / n_segs

    # ---- Vídeo ----
    split_labels = "".join(f"[vr{i}]" for i in range(n_segs))
    parts.append(f"[0:v]split={n_segs}{split_labels}")

    for i in range(n_segs):
        start = i * seg_dur
        if i < n_segs - 1:
            end = (i + 1) * seg_dur
            trim = f"trim=start={start:.3f}:end={end:.3f},setpts=PTS-STARTPTS"
        else:
            trim = f"trim=start={start:.3f},setpts=PTS-STARTPTS"
        parts.append(f"[vr{i}]{trim}[vs{i}]")

    concat_in_v = "".join(f"[vs{perm[i]}]" for i in range(n_segs))
    parts.append(f"{concat_in_v}concat=n={n_segs}:v=1:a=0[vcombined]")
    vsrc = "vcombined"

    # ---- Áudio ----
    asrc: Optional[str] = None
    if video_tem_audio:
        asplit_labels = "".join(f"[ar{i}]" for i in range(n_segs))
        parts.append(f"[0:a]asplit={n_segs}{asplit_labels}")

        for i in range(n_segs):
            start = i * seg_dur
            if i < n_segs - 1:
                end = (i + 1) * seg_dur
                atrim = f"atrim=start={start:.3f}:end={end:.3f},asetpts=PTS-STARTPTS"
            else:
                atrim = f"atrim=start={start:.3f},asetpts=PTS-STARTPTS"
            parts.append(f"[ar{i}]{atrim}[as{i}]")

        concat_in_a = "".join(f"[as{perm[i]}]" for i in range(n_segs))
        parts.append(f"{concat_in_a}concat=n={n_segs}:v=0:a=1[acombined]")
        asrc = "acombined"

    return parts, vsrc, asrc


# ──────────────────────────────────────────────
# FILTROS DE VÍDEO
# ──────────────────────────────────────────────

def _build_video_filters(
    width: int,
    height: int,
    fps: float,
    duracao: float,
    ts: int,
    logs_dir: Path,
    input_stem: str,
    font_path_obj: Optional[Path],
    texto_quebrado: str,
    do_ken_burns: bool,
    do_intro_outro: bool,
    intro_dur: float,
    outro_dur: float,
) -> Tuple[str, Optional[Path], float, dict]:
    """
    Monta a cadeia completa de filtros de vídeo.

    Retorna: (filtro_str, arquivo_texto_temp, speed_factor, info_dict)
    """
    info: dict = {}

    # ---- Parâmetros aleatórios ----
    crop_px_x    = random.randint(5, 30)
    crop_px_y    = random.randint(5, 30)
    scale_factor = round(random.uniform(0.985, 1.015), 5)
    use_hflip    = random.random() < 0.5
    rotate_angle = round(random.uniform(-1.5, 1.5), 4)
    speed_factor = round(random.uniform(0.95, 1.05), 5)
    brightness   = round(random.uniform(-0.015, 0.015), 5)
    contrast     = round(random.uniform(0.993, 1.007), 5)
    hue_shift    = round(random.uniform(-15.0, 15.0), 3)
    hue_sat      = round(random.uniform(0.96, 1.04), 4)
    grain_strength = random.randint(1, 6)
    pad_px       = random.randint(4, 20) * 2  # sempre par

    info.update({
        "crop": f"{crop_px_x}x{crop_px_y}px",
        "scale": scale_factor,
        "hflip": use_hflip,
        "rotate": f"{rotate_angle:.2f}°",
        "speed": speed_factor,
        "hue_shift": f"{hue_shift:.1f}°",
        "hue_sat": hue_sat,
        "grain": grain_strength,
        "pad": f"{pad_px}px",
    })

    # ---- Drawtext ----
    arquivo_texto_temp: Optional[Path] = None
    drawtext_filter = ""
    if font_path_obj is not None:
        arquivo_texto_temp = logs_dir / f"texto_temp_{input_stem}_{ts}.txt"
        arquivo_texto_temp.write_text(texto_quebrado, encoding="utf-8")
        fontsize   = max(18, int(height / 38))
        box_border = max(4, int(fontsize / 5))
        font_color = random.choice(TEXT_COLORS)
        text_pos   = random.choice(TEXT_POSITIONS)
        drawtext_filter = (
            f"drawtext="
            f"fontfile='{_ff_path(font_path_obj)}':"
            f"textfile='{_ff_path(arquivo_texto_temp)}':"
            f"fontcolor={font_color}:fontsize={fontsize}:"
            f"box=1:boxcolor=black@0.5:boxborderw={box_border}:"
            f"line_spacing={int(fontsize / 4)}:"
            f"{text_pos}"
        )
        info["font"] = font_path_obj.name
        info["text_color"] = font_color
    else:
        info["font"] = "N/A"

    # ---- Ken Burns (zoompan) ----
    # Zoom suave de 0→2.5% ao longo do vídeo. CPU-intensivo mas muito eficaz.
    zoompan_filter = ""
    if do_ken_burns:
        total_frames_est = max(30, int(duracao * fps))
        zoom_per_frame = round(0.025 / total_frames_est, 9)
        # Dimensões do frame após crop+scale (para o parâmetro s= do zoompan)
        w_z = (int((width - crop_px_x * 2) * scale_factor) // 2) * 2
        h_z = (int((height - crop_px_y * 2) * scale_factor) // 2) * 2
        w_z = max(32, w_z)
        h_z = max(32, h_z)
        # Direção: zoom_in (cresce) ou zoom_out (decresce a partir de 1.025)
        direction = random.choice(["in", "out"])
        if direction == "in":
            z_expr = f"min(zoom+{zoom_per_frame},1.025)"
        else:
            # Usa variável 'on' (output frame number) para zoom que decresce
            z_expr = f"max(1.0,1.025-on*{zoom_per_frame})"
        zoompan_filter = (
            f"zoompan=z='{z_expr}':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d=1:s={w_z}x{h_z}"
        )
        info["ken_burns"] = f"{direction} ({zoom_per_frame:.9f}/frame)"

    # ---- Monta cadeia de filtros ----
    filters: List[str] = []

    # 1) Transformações geométricas
    filters.append(f"crop=iw-{crop_px_x * 2}:ih-{crop_px_y * 2}:{crop_px_x}:{crop_px_y}")
    filters.append(
        f"scale=trunc(iw*{scale_factor}/2)*2:trunc(ih*{scale_factor}/2)*2:flags=lanczos"
    )
    if use_hflip:
        filters.append("hflip")
    filters.append(f"rotate={rotate_angle}*PI/180:fillcolor=black@1")

    # 2) Temporal (speed)
    filters.append(f"setpts={speed_factor}*PTS")

    # 3) Ken Burns (zoom suave) — antes das correções de cor
    if zoompan_filter:
        filters.append(zoompan_filter)

    # 4) Correção de cor
    filters.append(f"eq=brightness={brightness}:contrast={contrast}")
    filters.append(f"hue=h={hue_shift}:s={hue_sat}")

    # 5) Ruído
    filters.append(f"noise=alls={grain_strength}:allf=t+u")

    # 6) Bordas pretas
    filters.append(f"pad=iw+{pad_px * 2}:ih+{pad_px * 2}:{pad_px}:{pad_px}:color=black")

    # 7) Texto
    if drawtext_filter:
        filters.append(drawtext_filter)

    # 8) Intro/outro em preto (tpad — acrescenta frames pretos no início e fim)
    if do_intro_outro and (intro_dur > 0 or outro_dur > 0):
        filters.append(
            f"tpad=start_duration={intro_dur:.2f}:stop_duration={outro_dur:.2f}:color=black"
        )
        info["intro_outro"] = f"{intro_dur:.1f}s / {outro_dur:.1f}s"

    filtro_video = ",".join(filters)
    return filtro_video, arquivo_texto_temp, speed_factor, info


# ──────────────────────────────────────────────
# FILTROS DE ÁUDIO
# ──────────────────────────────────────────────

def _build_audio_af(
    speed_factor: float,
    audio_pitch: float,
    audio_eq: List[str],
    intro_dur: float = 0.0,
    outro_dur: float = 0.0,
) -> str:
    """
    Monta a cadeia de filtros de áudio:
      EQ espectral → atempo (sync) → asetrate+aresample (pitch) →
      adelay (intro silence) → apad (outro silence)
    """
    audio_sync = round(1.0 / speed_factor, 6)
    parts: List[str] = []

    parts.extend(audio_eq)
    parts.append(f"atempo={audio_sync}")
    parts.append(f"asetrate=44100*{audio_pitch}")
    parts.append("aresample=44100")

    # Silêncio de intro: adelay vem DEPOIS do processamento
    # para que 1s de silêncio seja literalmente 1s na saída.
    if intro_dur > 0:
        intro_ms = int(intro_dur * 1000)
        parts.append(f"adelay={intro_ms}|{intro_ms}")

    if outro_dur > 0:
        parts.append(f"apad=pad_dur={outro_dur:.2f}")

    return ",".join(parts)


# ──────────────────────────────────────────────
# ENCODING PARAMS
# ──────────────────────────────────────────────

def _encoding_params(encoder: str) -> List[str]:
    """Retorna os parâmetros de encoding corretos para o encoder detectado."""
    video_bitrate = random.choice(["1500k", "1800k", "2000k", "2200k", "2500k"])
    br      = int(video_bitrate[:-1])
    maxrate = int(br * 1.2)
    bufsize = int(br * 2.0)
    crf     = random.randint(20, 26)

    if encoder == "h264_nvenc":
        return [
            "-c:v", "h264_nvenc",
            "-preset", random.choice(["p4", "p5"]),  # p4=balanced, p5=slow+quality
            "-rc", "vbr",
            "-cq", str(crf),
            "-b:v", video_bitrate,
            "-maxrate", f"{maxrate}k",
            "-bufsize", f"{bufsize}k",
            "-pix_fmt", "yuv420p",
        ]
    elif encoder == "h264_amf":
        return [
            "-c:v", "h264_amf",
            "-quality", "balanced",
            "-b:v", video_bitrate,
            "-maxrate", f"{maxrate}k",
            "-pix_fmt", "yuv420p",
        ]
    else:  # libx264
        return [
            "-c:v", "libx264",
            "-preset", random.choice(["medium", "slow"]),
            "-crf", str(crf),
            "-b:v", video_bitrate,
            "-maxrate", f"{maxrate}k",
            "-bufsize", f"{bufsize}k",
            "-pix_fmt", "yuv420p",
        ]


# ──────────────────────────────────────────────
# PROCESSAMENTO PRINCIPAL
# ──────────────────────────────────────────────

def processar_video(input_file: Path, output_file: Path, logs_dir: Path, pasta_mp3: Path) -> bool:
    logs_dir.mkdir(parents=True, exist_ok=True)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    if not input_file.exists():
        print(f"[ERRO] Input não existe: {input_file}")
        return False

    hash_original   = calcular_hash_arquivo(input_file)[:16]
    texto_escolhido = random.choice(FRASES_MOTIVACIONAIS)
    video_tem_audio = tem_audio(input_file)
    info_video      = obter_info_video(input_file)
    duracao         = obter_duracao(input_file)
    width           = info_video.get("width", 1920)
    height          = info_video.get("height", 1080)
    fps             = float(info_video.get("fps", 30.0))
    ts              = int(time.time() * 1000)

    chars_por_linha = max(20, int(width / 40))
    texto_quebrado  = textwrap.fill(texto_escolhido, width=chars_por_linha)

    print(f"\n[{input_file.name}] Iniciando processamento...")
    print(f"-> Hash: {hash_original} | {width}x{height} | {fps:.2f}fps | {duracao:.1f}s")
    print(f"-> Áudio: {'Sim' if video_tem_audio else 'Não'}")

    font_path_obj = _find_font()
    if font_path_obj is None:
        print("[AVISO] Nenhuma fonte encontrada. Overlay desativado.")

    # ── Flags de features ──────────────────────────────────────────────
    # Reordenação: só faz sentido em vídeos com 3+ segmentos distinguíveis (>30s)
    do_scene_reorder = (duracao > 30.0) and (random.random() < 0.6)
    # Intro/outro: frames pretos no começo e fim
    do_intro_outro   = random.random() < 0.55
    intro_dur        = round(random.uniform(0.5, 2.0), 2) if do_intro_outro else 0.0
    outro_dur        = round(random.uniform(0.5, 1.5), 2) if do_intro_outro else 0.0
    # Ken Burns: zoom suave ao longo do vídeo (desativado em CPUs lentos sem GPU)
    hw_enc           = detect_hw_encoder()
    do_ken_burns     = random.random() < (0.6 if hw_enc != "libx264" else 0.3)

    # ── Parâmetros de reordenação ───────────────────────────────────────
    n_segs = 3
    perm   = list(range(n_segs))
    if do_scene_reorder:
        while perm == list(range(n_segs)):   # garante que há mudança real
            random.shuffle(perm)

    # ── Filtros de vídeo ───────────────────────────────────────────────
    filtro_video, arquivo_texto_temp, speed_factor, info_tx = _build_video_filters(
        width, height, fps, duracao, ts,
        logs_dir, input_file.stem,
        font_path_obj, texto_quebrado,
        do_ken_burns, do_intro_outro, intro_dur, outro_dur,
    )

    # ── Filtros de áudio ───────────────────────────────────────────────
    audio_pitch = round(random.uniform(0.97, 1.03), 5)
    audio_eq    = random.choice(AUDIO_EQ_OPTIONS)
    orig_af     = _build_audio_af(speed_factor, audio_pitch, audio_eq, intro_dur, outro_dur)

    # ── Música de fundo ────────────────────────────────────────────────
    musica_escolhida: Optional[Path] = None
    if pasta_mp3.exists() and pasta_mp3.is_dir():
        lista_mp3 = [m for m in pasta_mp3.iterdir() if m.suffix.lower() == ".mp3" and m.is_file()]
        if lista_mp3:
            musica_escolhida = random.choice(lista_mp3)

    # ── Log de features ────────────────────────────────────────────────
    print(f"-> Hflip: {info_tx['hflip']} | Hue: {info_tx['hue_shift']} | "
          f"Rot: {info_tx['rotate']} | Speed: {info_tx['speed']:.4f}")
    print(f"-> Grain: {info_tx['grain']} | Pad: {info_tx['pad']} | "
          f"Pitch: {audio_pitch:.4f} | EQ: {'Sim' if audio_eq else 'Não'}")
    print(f"-> KenBurns: {'Sim (' + info_tx.get('ken_burns','') + ')' if do_ken_burns else 'Não'} | "
          f"Reorder: {'Sim ' + str(perm) if do_scene_reorder else 'Não'} | "
          f"GPU: {hw_enc}")
    if do_intro_outro:
        print(f"-> Intro/Outro: {intro_dur:.1f}s / {outro_dur:.1f}s preto")
    if musica_escolhida:
        print(f"-> Música: '{musica_escolhida.name}'")

    # ── Monta comando FFmpeg ───────────────────────────────────────────
    comando: List[str] = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
        "-i", str(input_file)
    ]
    if musica_escolhida:
        music_limit = round(duracao * 1.06 + 10, 1)  # margem para speed + intro/outro
        comando.extend(["-t", str(music_limit), "-i", str(musica_escolhida)])
    music_idx = 1  # índice do input de música (sempre 1 quando presente)

    # Decide se precisa de filter_complex ou pode usar -vf/-af
    need_fc = do_scene_reorder or (musica_escolhida is not None)

    if need_fc:
        fc_parts: List[str] = []

        # ---- Fonte de vídeo (com ou sem reordenação) ----
        if do_scene_reorder:
            reorder_parts, vsrc, asrc_reorder = _build_scene_reorder(
                n_segs, perm, duracao, video_tem_audio
            )
            fc_parts.extend(reorder_parts)
        else:
            vsrc = "0:v"
            asrc_reorder = "0:a" if video_tem_audio else None

        # ---- Filtros de vídeo ----
        fc_parts.append(f"[{vsrc}]{filtro_video}[vout]")

        # ---- Filtros de áudio ----
        asrc = asrc_reorder  # pode ser "acombined", "0:a" ou None

        bg_vol = round(random.uniform(0.20, 0.45), 2)

        if musica_escolhida:
            if asrc:
                fc_parts.append(f"[{asrc}]{orig_af}[orig_a]")
                fc_parts.append(f"[{music_idx}:a]volume={bg_vol}[bg_a]")
                fc_parts.append(
                    f"[orig_a][bg_a]amix=inputs=2:duration=first:weights=1 {bg_vol}[aout]"
                )
            else:
                # Sem áudio original: usa só música
                fc_parts.append(f"[{music_idx}:a]volume={bg_vol},atempo=1.0[aout]")
        else:
            # Sem música: áudio original processado
            if asrc:
                fc_parts.append(f"[{asrc}]{orig_af}[aout]")

        filter_complex = ";".join(fc_parts)
        comando.extend(["-filter_complex", filter_complex, "-map", "[vout]"])

        if musica_escolhida or (not musica_escolhida and asrc):
            comando.extend(["-map", "[aout]"])
        if musica_escolhida and not asrc:
            comando.append("-shortest")

    else:
        # ---- Caminho simples: sem música, sem reordenação ----
        comando.extend(["-vf", filtro_video])
        if video_tem_audio:
            comando.extend(["-af", orig_af])

    # ── Encoding ───────────────────────────────────────────────────────
    comando.extend(_encoding_params(hw_enc))
    if musica_escolhida or video_tem_audio:
        comando.extend([
            "-c:a", "aac",
            "-b:a", random.choice(["128k", "160k", "192k"]),
            "-ar",  random.choice(["44100", "48000"]),
        ])

    # ── Metadata: apaga tudo, injeta custom ────────────────────────────
    comando.extend(["-map_metadata", "-1"])
    for kv in [
        f"title=Video_{ts}",
        f"artist=Creator_{random.randint(1000, 9999)}",
        f"comment=ID_{hash_original[:8]}_{ts}",
        "creation_time=1970-01-01T00:00:00.000000Z",
        f"encoder=FFmpeg Custom {random.randint(1000, 9999)}",
        "copyright=", "description=", "location=",
    ]:
        comando.extend(["-metadata", kv])

    comando.extend(["-movflags", "+faststart", str(output_file)])

    # ── Execução ───────────────────────────────────────────────────────
    ffmpeg_log = logs_dir / f"ffmpeg_{input_file.stem}.log"
    try:
        print("-> Executando FFmpeg...")
        with ffmpeg_log.open("w", encoding="utf-8", errors="ignore") as lf:
            lf.write("CMD:\n" + " ".join(comando) + "\n\n")
            proc = subprocess.run(comando, stdout=lf, stderr=lf, text=True)

        if proc.returncode != 0:
            try:
                log_content = ffmpeg_log.read_text(encoding="utf-8", errors="replace")
            except Exception:
                log_content = ""
            print(f"\n[ERRO] FFmpeg falhou (código {proc.returncode}). Log:\n{log_content}")
            return False

        if not output_file.exists():
            print(f"\n[ERRO] Output não foi criado: {output_file}")
            return False
        if output_file.stat().st_size < 200_000:
            print(f"\n[ERRO] Output muito pequeno ({output_file.stat().st_size} bytes)")
            return False

        hash_novo = calcular_hash_arquivo(output_file)[:16]
        print(f"-> Hash novo: {hash_novo}")
        print(f"[OK] Salvo em: {output_file}")
        return True

    finally:
        if arquivo_texto_temp is not None:
            try:
                arquivo_texto_temp.unlink(missing_ok=True)
            except Exception:
                pass


# ──────────────────────────────────────────────
# UPLOAD / JOB / UTILITÁRIOS DE FLUXO
# ──────────────────────────────────────────────

def enviar_para_servidor(caminho_video: Path, vmos_id: str, legenda: str, api_url: str, api_key: str = DEFAULT_API_KEY) -> bool:
    try:
        with caminho_video.open("rb") as f:
            resp = requests.post(
                api_url,
                data={"api_key": api_key, "vmos_id": vmos_id, "legenda": legenda},
                files={"arquivo_mp4": f},
                timeout=180
            )
        if resp.status_code == 403:
            print("[ERRO] Upload rejeitado (403). Verifique api_key.")
            return False
        try:
            resultado = resp.json()
        except Exception:
            print(f"[ERRO] Servidor retornou não-JSON: HTTP {resp.status_code} | {resp.text[:300]}")
            return False
        if resultado.get("sucesso"):
            print(f"Upload OK! Fila da conta '{vmos_id}'.")
            return True
        print(f"[ERRO] Servidor recusou: {resultado.get('mensagem')}")
        return False
    except Exception as ex:
        print(f"[ERRO] Falha no upload: {ex}")
        return False


def listar_inputs(input_path: Path) -> list[Path]:
    if input_path.is_file():
        return [input_path]
    if input_path.is_dir():
        vids = [v for v in input_path.iterdir() if v.suffix.lower() in VIDEO_EXTS and v.is_file()]
        vids.sort(key=lambda v: v.stat().st_mtime)
        return vids
    return []


def _safe_move(src: Path, dst_dir: Path) -> Path:
    dst_dir.mkdir(parents=True, exist_ok=True)
    base = dst_dir / src.name
    if not base.exists():
        src.rename(base)
        return base
    alt = dst_dir / f"{src.stem}_{int(time.time() * 1000)}{src.suffix}"
    src.rename(alt)
    return alt


def cleanup_input_on_success(input_file: Path, mode: str, processed_dir: Path) -> None:
    mode = (mode or "move").lower()
    if mode == "keep":
        return
    if mode == "delete":
        input_file.unlink(missing_ok=True)
        return
    _safe_move(input_file, processed_dir)


def cleanup_input_on_fail(input_file: Path, failed_dir: Path) -> None:
    _safe_move(input_file, failed_dir)


def job_get(job_url: str, api_key: str = DEFAULT_API_KEY) -> dict:
    r = requests.get(job_url, params={"api_key": api_key}, timeout=30)
    r.raise_for_status()
    data = r.json()
    if not data.get("sucesso"):
        raise RuntimeError(f"Job GET falhou: {data}")
    return data.get("job") or {}


def job_ack(ack_url: str, nonce: str, status: str, ok: int = 0, fail: int = 0, message: str = "", api_key: str = DEFAULT_API_KEY) -> None:
    r = requests.post(ack_url, data={
        "api_key": api_key, "nonce": nonce, "status": status,
        "result_ok": str(ok), "result_fail": str(fail), "message": message,
    }, timeout=30)
    r.raise_for_status()
    data = r.json()
    if not data.get("sucesso"):
        raise RuntimeError(f"Job ACK falhou: {data}")


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Fábrica de vídeos originais.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", default="output")
    parser.add_argument("--music-dir", default="musicas_fundo")
    parser.add_argument("--logs-dir", default="logs")
    parser.add_argument("--api-url", default=DEFAULT_API_URL)
    parser.add_argument("--api-key", default=DEFAULT_API_KEY)
    parser.add_argument("--job-url", default="")
    parser.add_argument("--ack-url", default="")
    parser.add_argument("--upload", action="store_true")
    parser.add_argument("--vmos-id", default="")
    parser.add_argument("--legenda", default="")
    parser.add_argument("--on-success", choices=["move", "delete", "keep"], default="move")
    parser.add_argument("--processed-dir", default="processed")
    parser.add_argument("--failed-dir", default="failed")
    parser.add_argument("--clean-output-after-upload", action="store_true")
    parser.add_argument("--max-videos", type=int, default=0)
    args = parser.parse_args()

    input_path    = Path(args.input)
    output_dir    = Path(args.output_dir)
    music_dir     = Path(args.music_dir)
    logs_dir      = Path(args.logs_dir)
    processed_dir = Path(args.processed_dir)
    failed_dir    = Path(args.failed_dir)
    api_key       = args.api_key

    for d in [output_dir, logs_dir, processed_dir, failed_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # JOB MODE
    if args.job_url and args.ack_url:
        job    = job_get(args.job_url, api_key)
        status = (job.get("status") or "idle").lower()
        if status not in ("pending", "running"):
            print(f"Nenhum job pendente. status={status}")
            return
        nonce = job.get("nonce") or ""
        if not nonce:
            print("Job inválido: falta nonce.")
            return
        vmos_id  = (job.get("vmos_id") or "").strip()
        if not vmos_id:
            job_ack(args.ack_url, nonce, "error", 0, 0, "Job inválido: vmos_id vazio.", api_key)
            return
        job_ack(args.ack_url, nonce, "running", 0, 0, "Worker iniciou.", api_key)
        args.upload                   = True
        args.vmos_id                  = vmos_id
        args.legenda                  = (job.get("legenda") or "").strip()
        args.max_videos               = int(job.get("max_videos") or 1)
        args.on_success               = job.get("on_success") or "move"
        args.clean_output_after_upload = bool(job.get("clean_output_after_upload") or False)

    inputs = listar_inputs(input_path)
    if not inputs:
        print(f"Nenhum vídeo em: {input_path}")
        return

    if args.max_videos and args.max_videos > 0:
        inputs = inputs[:args.max_videos]

    if args.upload and not str(args.vmos_id).strip():
        print("[ERRO] --vmos-id obrigatório para upload.")
        return

    ok, fail, last_nonce = 0, 0, ""
    if args.job_url and args.ack_url:
        try:
            last_nonce = job_get(args.job_url, api_key).get("nonce") or ""
        except Exception:
            pass

    for vid in inputs:
        out = output_dir / f"{vid.stem}_edit_{int(time.time())}{vid.suffix.lower()}"

        if not processar_video(vid, out, logs_dir, music_dir):
            fail += 1
            cleanup_input_on_fail(vid, failed_dir)
            continue

        if args.upload:
            if not enviar_para_servidor(out, str(args.vmos_id).strip(),
                                         str(args.legenda or "").strip(),
                                         args.api_url, api_key):
                fail += 1
                cleanup_input_on_fail(vid, failed_dir)
                continue
            if args.clean_output_after_upload and out.exists():
                out.unlink(missing_ok=True)

        ok += 1
        cleanup_input_on_success(vid, args.on_success, processed_dir)

    print(f"\nFinalizado. OK={ok} | FALHAS={fail}")

    if args.job_url and args.ack_url and last_nonce:
        final_status = "done" if fail == 0 else "error"
        msg = "Concluído." if fail == 0 else "Concluído com falhas."
        job_ack(args.ack_url, last_nonce, final_status, ok, fail, msg, api_key)

    sys.exit(1 if fail > 0 else 0)


if __name__ == "__main__":
    main()
