#!/usr/bin/env python3
"""
STUDIO ENGINE — Gerador de vídeos evergreen lo-fi/relaxing para YouTube

Modos disponíveis:
  lofi      — 30-60 min, estética lo-fi clássica (Lofi Girl vibes)
  relaxing  — 30-60 min, natureza / ambient
  study     — 1-3h, foco total, efeitos mínimos
  shorts    — 30-60s, vertical 9:16 para YouTube Shorts

Funcionalidades:
  ✅ Frases geradas por IA (DeepSeek) com 5 estilos de animação de texto
  ✅ Visualizador de waveform sincronizado com o beat da música
  ✅ Barra de progresso animada no rodapé
  ✅ Exibição do nome da faixa musical
  ✅ Estilo visual lo-fi: grão, vinheta, color grading por modo
  ✅ Zoom/pan ultra-lento via scale+crop (eficiente em clips longos)
  ✅ Encoder x264 ou NVENC
  ✅ Metadados YouTube gerados por IA (título, descrição, tags)
  ✅ Fallback local para frases e metadados se API indisponível

Requisitos: ffmpeg + ffprobe no PATH, Python 3.8+
"""

import argparse
import hashlib
import json
import os
import random
import re as _re
import shutil
import signal
import subprocess
import threading
import time
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from deepseek_client import DeepSeekClient
from visual_styles import get_palette, get_style


# ---------------------------------------------------------------------------
# Constantes globais
# ---------------------------------------------------------------------------

VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi", ".flv", ".wmv", ".mpeg", ".mpg"}
AUDIO_EXTS = {".mp3", ".wav", ".aac", ".m4a", ".ogg", ".flac", ".wma"}
ENGINE_FPS = 30


# ---------------------------------------------------------------------------
# Utilitários FFmpeg
# ---------------------------------------------------------------------------

def _safe_int_even(x: float, minimum: int = 2) -> int:
    v = max(minimum, int(round(float(x))))
    if v % 2 != 0:
        v += 1
    return max(minimum, v)


def _ffprobe_json(args: List[str]) -> Dict:
    try:
        out = subprocess.check_output(["ffprobe", *args], text=True, stderr=subprocess.STDOUT)
        return json.loads(out)
    except Exception:
        return {}


def _get_duration(path: Path) -> float:
    data = _ffprobe_json([
        "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)
    ])
    try:
        return float(data["format"]["duration"])
    except Exception:
        return 0.0


_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/opentype/cantarell/Cantarell-Bold.otf",
    "/System/Library/Fonts/Helvetica.ttc",
    "C:/Windows/Fonts/arialbd.ttf",
]


def _find_font(override: str = "") -> str:
    if override and Path(override).exists():
        return override
    for f in _FONT_CANDIDATES:
        if Path(f).exists():
            return f
    return ""


def _track_drawtext(track_name: str, track_dur: float, font_path: str = "",
                    time_offset: float = 0.0) -> str:
    """Gera filtro drawtext para exibir nome da faixa no canto superior esquerdo.

    time_offset: tempo absoluto (segundos) em que essa faixa começa no vídeo.
    track_dur:   duração dessa faixa específica (não do vídeo total).
    """
    if not track_name or track_dur < 4.0:
        return ""
    name = Path(track_name).stem[:45].replace("_", " ").replace("-", " ").strip()
    for ch, esc in [("\\", "\\\\"), ("'", "\\'"), (":", "\\:"),
                    (",", "\\,"), (";", "\\;"), ("%", "%%")]:
        name = name.replace(ch, esc)
    fade_s = 1.0
    t_start = time_offset + 1.5
    t_end   = time_offset + min(9.5, max(3.0, track_dur - 1.5))
    if t_end <= t_start + 0.1:
        return ""
    alpha = (
        f"if(lt(t,{t_start:.2f}+{fade_s:.1f}),"
        f"max(0,(t-{t_start:.2f})/{fade_s:.1f}),"
        f"if(gt(t,{t_end:.2f}-{fade_s:.1f}),"
        f"max(0,({t_end:.2f}-t)/{fade_s:.1f}),1))"
    )
    fp = ""
    if font_path and Path(font_path).exists():
        safe = font_path.replace("\\", "/").replace("'", "\\'").replace(":", "\\:")
        fp = f"fontfile='{safe}':"
    return (
        f"drawtext={fp}"
        f"text='♪  {name}':"
        f"fontsize=22:fontcolor=0xFFF8E7:"
        f"x=20:y=20:"
        f"shadowx=1:shadowy=1:shadowcolor=0x1A0800@0.85:"
        f"alpha='{alpha}':"
        f"enable='between(t,{t_start:.2f},{t_end:.2f})'"
    )


def _pick_random_file(folder: Optional[Path], exts: set) -> Optional[Path]:
    if not folder or not folder.exists():
        return None
    files = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in exts]
    return random.choice(files) if files else None


def _pick_audio_tracks(folder: Optional[Path], min_duration: float) -> List[Path]:
    """Retorna lista de faixas de áudio suficientes para cobrir min_duration."""
    if not folder or not folder.exists():
        return []
    files = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in AUDIO_EXTS]
    if not files:
        return []
    random.shuffle(files)
    tracks: List[Path] = []
    total = 0.0
    for f in files:
        tracks.append(f)
        total += _get_duration(f)
        if total >= min_duration:
            break
    # Se não tiver duração suficiente, loop da última faixa
    return tracks


# ---------------------------------------------------------------------------
# Processo / Subprocess helpers
# ---------------------------------------------------------------------------

@dataclass
class CmdResult:
    rc: int
    elapsed: float
    stdout: str
    stderr: str
    timed_out: bool


class ProcRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._procs: set = set()

    def add(self, p: subprocess.Popen) -> None:
        with self._lock:
            self._procs.add(p)

    def discard(self, p: subprocess.Popen) -> None:
        with self._lock:
            self._procs.discard(p)

    def kill_all(self) -> None:
        with self._lock:
            procs = list(self._procs)
        for p in procs:
            try:
                kill_process_tree(p)
            except Exception:
                pass


def kill_process_tree(p: subprocess.Popen) -> None:
    if p.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(p.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    else:
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass


def run_cmd_capture(
    cmd: List[str], log_file: Path, timeout_s: int,
    proc_reg: Optional[ProcRegistry] = None
) -> CmdResult:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    timed_out = False
    kw = dict(
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", errors="replace",
    )
    if os.name == "nt":
        kw["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kw["start_new_session"] = True

    p = subprocess.Popen(cmd, **kw)
    if proc_reg:
        proc_reg.add(p)
    try:
        try:
            out, err = p.communicate(timeout=timeout_s)
            rc = int(p.returncode or 0)
        except subprocess.TimeoutExpired:
            timed_out = True
            kill_process_tree(p)
            out, err = p.communicate()
            rc = 124
    finally:
        if proc_reg:
            proc_reg.discard(p)

    elapsed = time.time() - t0
    try:
        with log_file.open("w", encoding="utf-8", errors="replace") as lf:
            lf.write("CMD:\n" + " ".join(cmd) + "\n\n")
            lf.write(f"TIMEOUT_S={timeout_s}\nELAPSED_S={elapsed:.2f}\n")
            lf.write(f"RC={rc}\nTIMED_OUT={timed_out}\n")
            lf.write("\n--- STDERR ---\n" + (err or ""))
            lf.write("\n--- STDOUT ---\n" + (out or ""))
    except Exception:
        pass
    return CmdResult(rc=rc, elapsed=elapsed, stdout=out or "", stderr=err or "", timed_out=timed_out)


def estimate_timeout(clip_dur_s: float, stabilize: bool, denoise: bool,
                     upscale: bool, intensity: float, base_s: int, mult: float) -> int:
    speed = 0.18
    if stabilize:  speed *= 0.75
    if denoise:    speed *= 0.80
    if upscale:    speed *= 0.75
    speed *= max(0.55, 1.0 - 0.35 * max(0.0, min(1.0, intensity)))
    speed = max(0.05, speed)
    t = max(float(base_s), (clip_dur_s / speed) * 1.6 + 60.0) * max(1.0, mult)
    return int(min(t, 4 * 3600))


_FFMPEG_TIME_RE = _re.compile(r"time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})")
_FFMPEG_SPEED_RE = _re.compile(r"speed=\s*([\d.]+)x")


def run_cmd_progress(
    cmd: List[str], log_file: Path, timeout_s: int,
    total_dur: float = 0.0, label: str = "",
    proc_reg: Optional["ProcRegistry"] = None,
) -> "CmdResult":
    """
    Executa um comando FFmpeg exibindo progresso em tempo real no terminal.
    Lê o stderr linha a linha em uma thread separada e imprime barra de progresso
    com percentual, tempo processado/total e ETA.
    """
    log_file.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    timed_out = False
    kw: dict = dict(
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", errors="replace", bufsize=1,
    )
    if os.name == "nt":
        kw["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kw["start_new_session"] = True

    p = subprocess.Popen(cmd, **kw)
    if proc_reg:
        proc_reg.add(p)

    stderr_lines: List[str] = []
    last_print_t = [0.0]

    def _read_stderr() -> None:
        for line in p.stderr:
            stderr_lines.append(line)
            if total_dur <= 0:
                continue
            m_time = _FFMPEG_TIME_RE.search(line)
            if not m_time:
                continue
            h, mi, s, cs = (int(m_time.group(i)) for i in range(1, 5))
            cur = h * 3600 + mi * 60 + s + cs / 100.0
            pct = min(100.0, cur / total_dur * 100.0)
            elapsed = time.time() - t0
            eta_s = int((elapsed / max(cur, 0.01)) * max(0.0, total_dur - cur))

            now = time.time()
            if now - last_print_t[0] < 4.0:
                continue
            last_print_t[0] = now

            filled = int(pct / 5)
            bar = "█" * filled + "░" * (20 - filled)
            cur_str = f"{int(cur) // 60:02d}:{int(cur) % 60:02d}"
            tot_str = f"{int(total_dur) // 60:02d}:{int(total_dur) % 60:02d}"
            eta_str = f"{eta_s // 60:02d}:{eta_s % 60:02d}"
            pfx = f"    {label} " if label else "    "
            print(
                f"{pfx}[{bar}] {pct:5.1f}%  {cur_str}/{tot_str}  ETA {eta_str}   ",
                end="\r", flush=True,
            )

    t_stderr = threading.Thread(target=_read_stderr, daemon=True)
    t_stderr.start()

    try:
        try:
            out = p.stdout.read()
            p.wait(timeout=timeout_s)
            rc = int(p.returncode or 0)
        except subprocess.TimeoutExpired:
            timed_out = True
            kill_process_tree(p)
            out = ""
            rc = 124
    finally:
        t_stderr.join(timeout=5)
        if proc_reg:
            proc_reg.discard(p)

    if total_dur > 0:
        print()  # nova linha após a barra de progresso

    elapsed = time.time() - t0
    err = "".join(stderr_lines)
    try:
        with log_file.open("w", encoding="utf-8", errors="replace") as lf:
            lf.write("CMD:\n" + " ".join(cmd) + "\n\n")
            lf.write(f"TIMEOUT_S={timeout_s}\nELAPSED_S={elapsed:.2f}\n")
            lf.write(f"RC={rc}\nTIMED_OUT={timed_out}\n")
            lf.write("\n--- STDERR ---\n" + err)
            lf.write("\n--- STDOUT ---\n" + (out or ""))
    except Exception:
        pass
    return CmdResult(rc=rc, elapsed=elapsed, stdout=out or "", stderr=err, timed_out=timed_out)


# ---------------------------------------------------------------------------
# Config de modo
# ---------------------------------------------------------------------------

@dataclass
class ModeConfig:
    dur_min: int        # duração mínima do vídeo (s)
    dur_max: int        # duração máxima do vídeo (s)
    clip_len_min: int   # tamanho mínimo de cada clip (s)
    clip_len_max: int   # tamanho máximo de cada clip (s)
    min_clips: int
    max_clips: int
    effect_intensity: float  # 0..1


MODES: Dict[str, ModeConfig] = {
    "lofi":     ModeConfig(30*60,  60*60,    1,  900,  3,  8,  0.15),
    "relaxing": ModeConfig(30*60,  60*60,    1,  900,  3,  8,  0.10),
    "study":    ModeConfig(60*60, 180*60,    1, 1800,  4, 12,  0.05),
    "shorts":   ModeConfig(30,     60,       1,   60,  1,  1,  0.30),
}


# ---------------------------------------------------------------------------
# StudioEngine
# ---------------------------------------------------------------------------

class StudioEngine:
    def __init__(self, args: argparse.Namespace):
        # Carrega config.json (opcional)
        cfg_path = Path(__file__).parent / "config.json"
        self.cfg_json: Dict = {}
        if cfg_path.exists():
            try:
                self.cfg_json = json.loads(cfg_path.read_text(encoding="utf-8"))
            except Exception:
                pass

        # Diretórios
        self.input_dir     = Path(args.input_dir)
        self.output_dir    = Path(args.output_dir)
        self.logs_dir      = Path(args.logs_dir)
        self.thumbs_dir    = Path(args.thumbs_dir)
        self.processed_dir = Path(args.processed_dir)
        self.failed_dir    = Path(args.failed_dir)

        for d in [self.output_dir, self.logs_dir, self.thumbs_dir,
                  self.processed_dir, self.failed_dir]:
            d.mkdir(parents=True, exist_ok=True)

        # Modo
        self.mode = args.mode.lower()
        if self.mode not in MODES:
            raise ValueError(f"Modo inválido: {self.mode}. Escolha: {list(MODES)}")
        self.mode_cfg = MODES[self.mode]
        self.visual   = get_style(self.mode)
        self.palette  = get_palette(self.mode)

        # Workers / timeouts
        self.max_workers       = int(args.workers)
        self.clip_timeout_s    = int(args.clip_timeout)
        self.clip_timeout_mult = float(args.clip_timeout_mult)
        self.final_timeout_s   = int(args.final_timeout)

        # Encoding
        self.final_crf    = int(args.final_crf)
        self.final_preset = args.final_preset
        self.concat_copy  = bool(args.concat_copy)
        self.encoder      = args.encoder
        self.nvenc_preset = args.nvenc_preset
        self.nvenc_cq     = int(args.nvenc_cq)
        self.nvenc_tune   = args.nvenc_tune

        # Resolução
        self.enable_upscale  = bool(args.enable_upscale)
        self.upscale_quality = args.upscale
        self.target_res: Optional[Tuple[int, int]] = tuple(args.target_res) if args.target_res else None

        # Para Shorts: forçar 9:16 se não especificado
        if self.mode == "shorts" and not self.target_res:
            self.target_res = (1080, 1920)

        # Filtros de qualidade
        self.enable_denoise    = bool(args.denoise)
        self.enable_stabilize  = bool(args.stabilize)
        self.enable_color      = bool(args.enhance_color)

        # Áudio
        music_dir = args.audio_music or self.cfg_json.get("audio", {}).get("music_dir", "audio_musicas")
        self.audio_music_dir   = Path(music_dir) if music_dir else None
        self.vol_music         = float(args.vol_music)
        _a = self.cfg_json.get("audio", {})
        self.fade_in           = float(args.fade_in  or _a.get("fade_in_s", 2.5))
        self.fade_out          = float(args.fade_out or _a.get("fade_out_s", 4.0))
        self.audio_sr          = int(_a.get("sample_rate", 44100))

        # IA / texto — chave sempre lida do config.json (ou variável de ambiente)
        _ds = self.cfg_json.get("deepseek", {})
        api_key = _ds.get("api_key", "") or os.environ.get("DEEPSEEK_API_KEY", "")
        if api_key in ("", "YOUR_DEEPSEEK_KEY_HERE"):
            api_key = ""
        self.deepseek    = DeepSeekClient(
            api_key=api_key,
            model=_ds.get("model", "deepseek-chat"),
            base_url=_ds.get("base_url", "https://api.deepseek.com/v1"),
            timeout_s=int(_ds.get("timeout_s", 30)),
        )
        self._ai_enabled = not getattr(args, "no_ai", False)

        # Visualizer
        _vis = self.cfg_json.get("visualizer", {})
        self.visualizer_enabled = _vis.get("enabled", True)
        self.vis_height_pct = float(
            self.visual.get("waves_height_pct", _vis.get("height_pct", 0.04))
        )
        self.vis_mode   = self.visual.get("waves_mode",  _vis.get("mode",  "cline"))
        self.vis_scale  = self.visual.get("waves_scale", _vis.get("scale", "lin"))
        # 4 cores para o waveform multicamada
        _default_multi = ["0xF5CBA7", "0xFFD700", "0xE07060", "0xFF9A8A"]
        self.vis_colors_multi: List[str] = self.visual.get("waves_colors_multi", _default_multi)

        # Progress bar
        _pb = self.cfg_json.get("progress_bar", {})
        self.progress_enabled = _pb.get("enabled", True)
        self.progress_height  = int(_pb.get("height_px", 3))

        # Fonte para drawtext (nome da faixa)
        _tx = self.cfg_json.get("text", {})
        self.font_path = _find_font(_tx.get("font_path", ""))

        # Thumbs
        self.make_thumbs = bool(args.thumbnails)

        # Estado
        self.stop_event = threading.Event()
        self.proc_reg   = ProcRegistry()
        self._ffmpeg_filters_cache: Optional[str] = None

        self._assert_tools()

    # ------------------------------------------------------------------ #
    # Utilitários internos                                                #
    # ------------------------------------------------------------------ #

    def _assert_tools(self) -> None:
        for tool in ("ffmpeg", "ffprobe"):
            try:
                subprocess.check_output([tool, "-version"], stderr=subprocess.STDOUT, text=True)
            except Exception as e:
                raise RuntimeError(f"Ferramenta obrigatória não encontrada: {tool}. {e}")

    def _ffmpeg_filters(self) -> str:
        if self._ffmpeg_filters_cache is None:
            try:
                self._ffmpeg_filters_cache = subprocess.check_output(
                    ["ffmpeg", "-hide_banner", "-filters"], text=True, stderr=subprocess.STDOUT
                )
            except Exception:
                self._ffmpeg_filters_cache = ""
        return self._ffmpeg_filters_cache

    def _has_filter(self, name: str) -> bool:
        return f" {name} " in self._ffmpeg_filters()

    # ------------------------------------------------------------------ #
    # Listagem / seleção de vídeos                                        #
    # ------------------------------------------------------------------ #

    def list_videos(self) -> List[Path]:
        # Route to subfolder: vertical/ para shorts, horizontal/ para outros modos
        if self.mode == "shorts":
            src_dir = self.input_dir / "vertical"
        else:
            src_dir = self.input_dir / "horizontal"

        # Fallback para raiz se a subpasta não existir
        if not src_dir.exists():
            src_dir = self.input_dir

        if not src_dir.exists():
            return []

        vids: List[Path] = []
        for ext in VIDEO_EXTS:
            vids.extend(src_dir.glob(f"*{ext}"))
            vids.extend(src_dir.glob(f"*{ext.upper()}"))
        vids = sorted({p for p in vids if p.is_file()},
                      key=lambda p: p.stat().st_mtime, reverse=True)
        return vids

    def pick_single_video(self, videos: List[Path], target_total_s: int) -> Optional[Dict]:
        """Seleciona um único vídeo aleatório e cria um loop de longa duração."""
        if not videos:
            return None
        video = random.choice(videos)
        inf = self.get_video_info(video)
        if float(inf["duration"]) <= 0:
            return None
        c = dict(inf)
        c.update({
            "start": 0.0,
            "end": float(target_total_s),
            "seg_len": float(target_total_s),
            "loop": True,
        })
        orig_min = int(float(inf["duration"])) // 60
        print(f"\n  Vídeo selecionado: {video.name} "
              f"({orig_min}min original → loop por {target_total_s // 60}min)")
        return c

    def get_video_info(self, path: Path) -> Dict:
        info = {"path": str(path), "name": path.name,
                "size_mb": path.stat().st_size / (1024 * 1024)}
        data = _ffprobe_json([
            "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height,r_frame_rate,codec_name",
            "-of", "json", str(path)
        ])
        w, h, fps = 1920, 1080, 30.0
        try:
            s  = data["streams"][0]
            w  = int(s.get("width") or 1920)
            h  = int(s.get("height") or 1080)
            fr = s.get("r_frame_rate") or "30/1"
            if "/" in fr:
                num, den = fr.split("/", 1)
                fps = (int(num) / int(den)) if int(den) else 30.0
            else:
                fps = float(fr)
        except Exception:
            pass
        dur = _get_duration(path)
        info.update({"width": w, "height": h, "fps": fps,
                     "duration": dur,
                     "duration_str": str(timedelta(seconds=int(dur)))})
        return info

    def pick_clips(self, videos: List[Path], target_total_s: int) -> List[Dict]:
        if not videos:
            return []
        shuffled = list(videos)
        random.shuffle(shuffled)

        # Accept all valid videos regardless of duration (short clips will be looped)
        infos: List[Dict] = []
        for v in shuffled:
            inf = self.get_video_info(v)
            if float(inf["duration"]) > 0:
                infos.append(inf)

        if not infos:
            print("⚠️ Nenhum vídeo válido encontrado em input_videos/.")
            return []

        # How many distinct clips to use (allow reuse when fewer videos than min_clips)
        desired = max(1, min(self.mode_cfg.max_clips, len(infos)))
        desired = max(self.mode_cfg.min_clips, desired)

        # Build pool — repeat source list if fewer videos than desired
        pool: List[Dict] = []
        while len(pool) < desired:
            pool.extend(infos)
        pool = pool[:desired]
        random.shuffle(pool)

        def make_segment(inf: Dict, seg_len: float) -> Dict:
            d = float(inf["duration"])
            needs_loop = d < seg_len
            if needs_loop:
                # Loop from the beginning; start offset not meaningful when looping
                start = 0.0
            else:
                seg_len = min(seg_len, d)
                start = random.uniform(0.0, max(0.0, d - seg_len))
            c = dict(inf)
            c.update({"start": start, "end": start + seg_len,
                      "seg_len": seg_len, "loop": needs_loop})
            return c

        clips: List[Dict] = []
        total = 0.0
        # Distribute target duration evenly across the pool
        base_seg = target_total_s / desired
        for inf in pool:
            seg = random.uniform(
                base_seg * 0.8,
                min(base_seg * 1.2, self.mode_cfg.clip_len_max),
            )
            seg = max(seg, 1.0)
            clips.append(make_segment(inf, seg))
            total += clips[-1]["seg_len"]

        # Top-up if still short (reuse any video)
        extras = list(infos) * 4
        random.shuffle(extras)
        while total < target_total_s and len(clips) < int(self.mode_cfg.max_clips * 2):
            inf = random.choice(extras)
            remaining = target_total_s - total
            seg = max(1.0, min(remaining, self.mode_cfg.clip_len_max))
            clips.append(make_segment(inf, seg))
            total += clips[-1]["seg_len"]

        looped = sum(1 for c in clips if c.get("loop"))
        print(f"\n  Clips selecionados: {len(clips)} ({looped} com loop) | "
              f"alvo={target_total_s//60}min | total≈{int(total)//60}min")
        return clips

    # ------------------------------------------------------------------ #
    # Câmera lo-fi: scale + crop (eficiente para clips longos)            #
    # ------------------------------------------------------------------ #

    def _lofi_camera_filter(self, ow: int, oh: int, clip_dur: float) -> Tuple[str, str]:
        """
        Escala o vídeo levemente acima da resolução alvo e aplica pan lento.
        Muito mais rápido que zoompan para clips de 5-30 minutos.
        """
        overscan = self.visual.get("overscan", 1.04)
        sw = _safe_int_even(ow * overscan, 2)
        sh = _safe_int_even(oh * overscan, 2)
        dur = max(1.0, clip_dur)

        direction = random.choices(
            ["right", "left", "down", "up", "diag_rd", "diag_lu"],
            weights=[0.20, 0.20, 0.15, 0.15, 0.15, 0.15],
            k=1
        )[0]

        dx = f"(iw-{ow})"  # espaço horizontal disponível após crop
        dy = f"(ih-{oh})"  # espaço vertical disponível após crop

        # Use t/dur directly — no min() needed because:
        # 1. -t seg_len in FFmpeg limits t to [0, dur]
        # 2. crop filter auto-clamps coordinates that exceed the valid range
        # This avoids any comma inside expressions (FFmpeg uses comma as filter separator)
        m = f"t/{dur:.3f}"
        mi = f"(1-t/{dur:.3f})"

        if direction == "right":
            cx, cy = f"{dx}*{m}", f"{dy}/2"
        elif direction == "left":
            cx, cy = f"{dx}*{mi}", f"{dy}/2"
        elif direction == "down":
            cx, cy = f"{dx}/2", f"{dy}*{m}"
        elif direction == "up":
            cx, cy = f"{dx}/2", f"{dy}*{mi}"
        elif direction == "diag_rd":
            cx, cy = f"{dx}*{m}", f"{dy}*{m}"
        else:  # diag_lu
            cx, cy = f"{dx}*{mi}", f"{dy}*{mi}"

        filt = (
            f"scale={sw}:{sh}:force_original_aspect_ratio=increase:flags=lanczos,"
            f"crop={ow}:{oh}:{cx}:{cy}"
        )
        return filt, f"cam:{direction}"

    # ------------------------------------------------------------------ #
    # Filtros de estilo visual (grão, vinheta, color grade)               #
    # ------------------------------------------------------------------ #

    def _style_filters(self) -> List[str]:
        filters: List[str] = []
        style = self.visual

        # Color grading
        if style.get("color_eq"):
            filters.append(style["color_eq"])

        # Grão de filme
        grain = style.get("grain_strength", 0)
        if grain > 0:
            alls = grain / 255.0
            filters.append(f"noise=alls={alls:.4f}:allf=t+u")

        # Vinheta
        if style.get("vignette"):
            angle = style.get("vignette_angle", "PI/4")
            filters.append(f"vignette=angle={angle}:mode=forward")

        return filters

    # ------------------------------------------------------------------ #
    # Remasterização: denoise, escala e nitidez                          #
    # ------------------------------------------------------------------ #

    def _remaster_filters(self, src_w: int, src_h: int, tw: int, th: int) -> List[str]:
        """
        Pipeline de remasterização aplicado a cada clip:
          1. Estabilização (opcional)
          2. Redução de ruído — sempre ativa (suave ou forte via --denoise)
          3. Escala para resolução alvo com lanczos (se necessário)
          4. Nitidez pós-escala (unsharp) — sempre ativa
          5. Melhoria de cor adicional (opcional via --enhance-color)
        """
        filters: List[str] = []

        # 1. Estabilização
        if self.enable_stabilize:
            filters.append("deshake=rx=48:ry=48")

        # 2. Redução de ruído: leve sempre, forte com --denoise
        if self.enable_denoise:
            filters.append("hqdn3d=4:3:6:4")
        else:
            filters.append("hqdn3d=1.5:1.0:3:2")

        # 3. Escala para resolução alvo
        needs_scale = tw > 0 and th > 0 and (tw, th) != (src_w, src_h)
        if needs_scale:
            filters.append(
                f"scale={tw}:{th}:force_original_aspect_ratio=increase:flags=lanczos,"
                f"crop={tw}:{th}"
            )

        # 4. Nitidez — compensação de blur de compressão/escala
        sharpen = self.visual.get("sharpen", 0.5)
        luma_a  = max(0.1, min(1.5, sharpen))
        chroma_a = luma_a * 0.35
        filters.append(f"unsharp=lx=5:ly=5:la={luma_a:.2f}:cx=3:cy=3:ca={chroma_a:.2f}")

        # 5. Boost de cor extra (opcional)
        if self.enable_color:
            filters.append("eq=brightness=0.01:contrast=1.04:saturation=1.08")

        return filters

    # ------------------------------------------------------------------ #
    # Encoder args                                                        #
    # ------------------------------------------------------------------ #

    def _clip_encoder_args(self, crf: int) -> List[str]:
        if self.encoder == "nvenc":
            return [
                "-c:v", "h264_nvenc",
                "-preset", self.nvenc_preset,
                "-tune", self.nvenc_tune,
                "-rc", "vbr",
                "-cq:v", str(self.nvenc_cq),
                "-b:v", "0",
                "-pix_fmt", "yuv420p",
            ]
        return ["-c:v", "libx264", "-preset", "medium", "-crf", str(crf), "-pix_fmt", "yuv420p"]

    # ------------------------------------------------------------------ #
    # Processamento de clip individual                                    #
    # ------------------------------------------------------------------ #

    def process_clip(self, clip: Dict, idx: int, temp_dir: Path,
                     final_w: int, final_h: int) -> Optional[Path]:
        if self.stop_event.is_set():
            return None

        src      = Path(clip["path"])
        start    = float(clip["start"])
        seg_len  = max(1.0, float(clip["seg_len"]))
        intensity = max(0.0, min(1.0, float(self.mode_cfg.effect_intensity)))

        filters: List[str] = []

        # --- Câmera lo-fi (scale+crop, ultra-lento) ---
        cam_f, cam_tag = self._lofi_camera_filter(final_w, final_h, seg_len)
        filters.append(cam_f)

        # --- Rotação micro (muito sutil no lo-fi) ---
        if random.random() < (0.10 + 0.15 * intensity):
            ang = random.uniform(-0.15, 0.15) * (0.3 + intensity)
            filters.append(f"rotate={ang}*PI/180:fillcolor=black@0:ow=iw:oh=ih")

        # --- Variação de velocidade (muito sutil) ---
        if random.random() < 0.15:
            speed = random.uniform(0.996, 1.004)
            filters.append(f"setpts=PTS/{speed:.4f}")

        # --- Remasterização: denoise, escala, nitidez ---
        # _lofi_camera_filter already scaled/cropped to final_w x final_h,
        # so pass target dims as src to skip the redundant scale step.
        filters.extend(self._remaster_filters(final_w, final_h, final_w, final_h))

        # --- Estilo visual lo-fi ---
        filters.extend(self._style_filters())

        # --- Normalização final ---
        filters += [f"fps={ENGINE_FPS}", "setsar=1", "format=yuv420p"]

        vf = ",".join(filters)
        out = temp_dir / f"clip_{idx:03d}_{src.stem}.mp4"
        log = self.logs_dir / f"clip_{idx:03d}_{src.stem}.log"

        crf = random.randint(18, 22)

        timeout_s = estimate_timeout(
            clip_dur_s=seg_len,
            stabilize=self.enable_stabilize,
            denoise=self.enable_denoise,
            upscale=(self.enable_upscale and self.upscale_quality != "none") or bool(self.target_res),
            intensity=intensity,
            base_s=self.clip_timeout_s,
            mult=self.clip_timeout_mult,
        )

        needs_loop = clip.get("loop", False) or seg_len > float(clip.get("duration", seg_len)) * 0.99

        concat_file: Optional[Path] = None
        if needs_loop:
            # Use concat demuxer to repeat the clip — more reliable than -stream_loop
            src_dur = max(0.1, float(clip.get("duration", 1.0)))
            repeats = int(seg_len / src_dur) + 2
            concat_file = out.parent / f"loop_{idx:03d}.txt"
            with concat_file.open("w", encoding="utf-8") as cf:
                # FFmpeg concat demuxer: use forward slashes (works on Windows too)
                path_str = str(src.resolve()).replace("\\", "/").replace("'", "\\'")
                line = f"file '{path_str}'\n"
                for _ in range(repeats):
                    cf.write(line)
            cmd = [
                "ffmpeg", "-y", "-hide_banner",
                "-f", "concat", "-safe", "0",
                "-i", str(concat_file),
                "-t", str(seg_len),
                "-vf", vf, "-an",
                "-movflags", "+faststart",
            ]
        else:
            cmd = [
                "ffmpeg", "-y", "-hide_banner",
                "-fflags", "+genpts",
                "-ss", str(start), "-i", str(src),
                "-t", str(seg_len),
                "-vf", vf, "-an",
                "-movflags", "+faststart",
            ]
        cmd += self._clip_encoder_args(crf)
        cmd += [str(out)]

        res = run_cmd_progress(cmd, log, timeout_s=timeout_s,
                               total_dur=seg_len, label=f"clip {idx}",
                               proc_reg=self.proc_reg)

        # Clean up temporary concat list
        if concat_file and concat_file.exists():
            try:
                concat_file.unlink()
            except Exception:
                pass

        if res.rc != 0 or not out.exists() or out.stat().st_size < 1024:
            tag = "TIMEOUT" if res.timed_out else f"rc={res.rc}"
            print(f"  ⚠  Clip {idx} falhou [{tag}] ({int(res.elapsed)}s): {src.name}")
            # Print lines that look like actual errors (skip FFmpeg header/info)
            _skip = {"ffmpeg version", "built with", "built on", "libav", "configuration",
                     "auto-inserting", "auto inserting", "[info]", "encoder ", "decoder "}
            error_lines = []
            for line in (res.stderr or "").splitlines():
                sl = line.strip().lower()
                if not sl:
                    continue
                if any(sl.startswith(s) for s in _skip):
                    continue
                error_lines.append(line.strip())
            # Show last 8 lines — FFmpeg errors always appear near the end
            for el in error_lines[-8:]:
                print(f"     {el}")
            # On the first failure, also print the full command for manual debugging
            if idx == 0:
                print(f"     CMD: {' '.join(cmd)}")
            try:
                out.unlink(missing_ok=True)
            except Exception:
                pass
            try:
                if src.exists():
                    dest = self.failed_dir / src.name
                    if not dest.exists():
                        shutil.copy2(src, dest)
            except Exception:
                pass
            return None

        print(f"  ✓  Clip {idx} [{cam_tag}] crf={crf} ({int(res.elapsed)}s): {src.name}")
        return out

    # ------------------------------------------------------------------ #
    # Concat                                                              #
    # ------------------------------------------------------------------ #

    def _escape_path(self, p: Path) -> str:
        return p.resolve().as_posix().replace("'", r"'\''")

    def _write_concat_list(self, clips: List[Path], ref: Path) -> Path:
        lst = ref.with_suffix(".concat.txt")
        lst.parent.mkdir(parents=True, exist_ok=True)
        with lst.open("w", encoding="utf-8") as f:
            for p in clips:
                f.write(f"file '{self._escape_path(p)}'\n")
        return lst

    def _concat_copy(self, clips: List[Path], out: Path) -> bool:
        lst = self._write_concat_list(clips, out)
        log = self.logs_dir / f"concat_copy_{out.stem}.log"
        cmd = [
            "ffmpeg", "-y", "-hide_banner",
            "-f", "concat", "-safe", "0", "-i", str(lst),
            "-an", "-c", "copy", "-movflags", "+faststart", str(out)
        ]
        res = run_cmd_capture(cmd, log, self.final_timeout_s, self.proc_reg)
        try:
            lst.unlink(missing_ok=True)
        except Exception:
            pass
        return res.rc == 0 and out.exists() and out.stat().st_size > 1024

    def _concat_reencode(self, clips: List[Path], out: Path, w: int, h: int) -> bool:
        lst = self._write_concat_list(clips, out)
        log = self.logs_dir / f"concat_reencode_{out.stem}.log"
        vf  = f"scale={w}:{h}:flags=lanczos,fps={ENGINE_FPS},setsar=1,format=yuv420p"
        cmd = [
            "ffmpeg", "-y", "-hide_banner",
            "-fflags", "+genpts",
            "-f", "concat", "-safe", "0", "-i", str(lst),
            "-an", "-vf", vf,
            "-c:v", "libx264", "-preset", self.final_preset,
            "-crf", str(self.final_crf), "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", "-video_track_timescale", "90000",
            str(out)
        ]
        res = run_cmd_capture(cmd, log, self.final_timeout_s, self.proc_reg)
        try:
            lst.unlink(missing_ok=True)
        except Exception:
            pass
        return res.rc == 0 and out.exists() and out.stat().st_size > 1024

    def concat_video_only(self, clips: List[Path], out: Path, w: int, h: int) -> bool:
        if not clips:
            return False
        if self.concat_copy:
            if self._concat_copy(clips, out):
                return True
            print("  ⚠  concat copy falhou; reencodando (mais lento).")
        ok = self._concat_reencode(clips, out, w, h)
        if not ok:
            print("  ✗  concat reencode falhou (veja logs/concat_reencode_*.log).")
        return ok

    # ------------------------------------------------------------------ #
    # Playlist de áudio                                                   #
    # ------------------------------------------------------------------ #

    def _build_audio_playlist(self, tracks: List[Path], min_duration: float) -> Path:
        """
        Cria um arquivo de playlist no formato concat demuxer do FFmpeg.
        As faixas tocam em sequência; se a duração total for insuficiente,
        a última faixa é repetida automaticamente.
        """
        playlist_file = self.logs_dir / "audio_playlist.txt"
        total = sum(_get_duration(t) for t in tracks)
        with playlist_file.open("w", encoding="utf-8") as f:
            for t in tracks:
                path_str = str(t.resolve()).replace("\\", "/").replace("'", "\\'")
                f.write(f"file '{path_str}'\n")
            # Loop na última faixa se duração total for insuficiente
            if total < min_duration and tracks:
                last = tracks[-1]
                last_dur = max(0.1, _get_duration(last))
                extra = int((min_duration - total) / last_dur) + 2
                path_str = str(last.resolve()).replace("\\", "/").replace("'", "\\'")
                for _ in range(extra):
                    f.write(f"file '{path_str}'\n")
        return playlist_file

    # ------------------------------------------------------------------ #
    # Renderização final: áudio + texto + waveform + progress bar         #
    # ------------------------------------------------------------------ #

    def render_final(
        self,
        video_in: Path,
        video_out: Path,
        video_w: int,
        video_h: int,
    ) -> bool:
        """
        Combina em uma única passagem FFmpeg:
          - Áudio via concat (inputs individuais — sem gap entre faixas)
          - Nome de CADA faixa no canto superior com offset de tempo correto
          - Waveform neon de 3 camadas: outer glow + inner glow + core
          - Barra de progresso no rodapé
        """
        dur = _get_duration(video_in)
        print(f"  Duração do clipe mudo: {dur:.1f}s ({int(dur) // 60}min {int(dur) % 60}s)")
        if dur <= 0.5:
            print("  ✗  Duração inválida para render final.")
            return False

        # 1. Seleciona faixas base
        tracks = _pick_audio_tracks(self.audio_music_dir, dur)
        if not tracks:
            print("  ⚠  Nenhuma música encontrada. Gerando sem áudio.")
            shutil.copy2(video_in, video_out)
            return True

        # Calcula duração de cada faixa e cria lista completa com loop
        track_durs = [_get_duration(t) for t in tracks]
        total_audio = sum(track_durs)
        # Extend com cópias da última faixa até cobrir o vídeo
        all_audio: List[Path] = list(tracks)
        all_durs: List[float] = list(track_durs)
        while total_audio < dur and tracks:
            last_t, last_d = tracks[-1], track_durs[-1]
            all_audio.append(last_t)
            all_durs.append(last_d)
            total_audio += last_d
        n_audio = len(all_audio)

        names = [t.stem.replace("_", " ").replace("-", " ") for t in tracks]
        print(f"  Playlist: {n_audio} input(s) | {len(tracks)} faixa(s) → "
              f"{', '.join(names[:4])}{'...' if len(names) > 4 else ''}")

        # 2. Altura do visualizador
        wh = _safe_int_even(int(video_h * self.vis_height_pct), 2)

        # 3. Per-track drawtext com offset temporal acumulado
        t_acc = 0.0
        drawtext_parts: List[str] = []
        for trk, td in zip(tracks, track_durs):
            dt_f = _track_drawtext(trk.name, td, self.font_path, time_offset=t_acc)
            if dt_f:
                drawtext_parts.append(dt_f)
            t_acc += td

        # 4. Barra de progresso
        h_pb = self.progress_height
        bar_f = (
            f"drawbox=x=0:y=ih-{h_pb}:w=iw*t/{dur:.3f}:h={h_pb}"
            f":color=0xF0B27A@0.55:t=fill"
        )
        base_filters = drawtext_parts + ([bar_f] if self.progress_enabled else [])
        if not base_filters:
            base_filters = ["copy"]
        vbase_filter = f"[0:v]{','.join(base_filters)}[vbase]"

        # 5. Cadeia de áudio com concat (gapless, sem chiado entre faixas)
        # concat filter (not aconcat) is available in all FFmpeg versions.
        # Each input is normalised to the target sample-rate/format BEFORE
        # concatenation, so tracks with different rates/channels work fine.
        fade_out_start = max(0.0, dur - self.fade_out)
        vol = self.vol_music
        fc_parts: List[str] = []

        # Per-input normalisation → [anorm0], [anorm1], …
        for i in range(n_audio):
            fc_parts.append(
                f"[{i + 1}:a]aresample={self.audio_sr},"
                f"aformat=sample_fmts=fltp:channel_layouts=stereo[anorm{i}]"
            )
        if n_audio == 1:
            audio_in_label = "[anorm0]"
        else:
            cat_in = "".join(f"[anorm{i}]" for i in range(n_audio))
            audio_in_label = "[acat]"
            fc_parts.append(f"{cat_in}concat=n={n_audio}:v=0:a=1[acat]")

        audio_chain_base = (
            f"{audio_in_label}"
            f"asetpts=N/SR/TB,"
            f"volume={vol:.3f},"
            f"afade=t=in:st=0:d={self.fade_in:.2f},"
            f"afade=t=out:st={fade_out_start:.3f}:d={self.fade_out:.2f},"
            f"alimiter=limit=0.95"
        )

        # 6. Visualizador neon: 3 camadas (outer glow → inner glow → core)
        c1, c2, c3, _ = self.vis_colors_multi   # outer, inner, core, unused
        fps = ENGINE_FPS
        # colorkey removes the black bg from each showwaves layer
        ck_loose = "colorkey=0x000000:similarity=0.22:blend=0.18"   # outer glow: keep haze
        ck_mid   = "colorkey=0x000000:similarity=0.14:blend=0.10"   # inner: tighter
        ck_core  = "colorkey=0x000000:similarity=0.08:blend=0.04"   # core: sharp

        if self.visualizer_enabled:
            fc_parts.append(audio_chain_base + ",asplit=4[aout][aw1][aw2][aw3]")
            fc_parts.append(vbase_filter)
            fc_parts.extend([
                # Outer glow: wide blur → bloom halo
                f"[aw1]showwaves=s={video_w}x{wh}:mode=cline:rate={fps}"
                f":colors={c1}:scale=sqrt,format=rgba,gblur=sigma=7,{ck_loose}[wg_outer]",
                # Inner glow: medium blur → neon tube body
                f"[aw2]showwaves=s={video_w}x{wh}:mode=cline:rate={fps}"
                f":colors={c2}:scale=sqrt,format=rgba,gblur=sigma=3,{ck_mid}[wg_inner]",
                # Core: no blur → sharp bright line
                f"[aw3]showwaves=s={video_w}x{wh}:mode=cline:rate={fps}"
                f":colors={c3}:scale=sqrt,format=rgba,{ck_core}[wg_core]",
                # Dark background strip + layer composition
                f"[vbase]drawbox=x=0:y=ih-{wh}:w=iw:h={wh}"
                f":color=0x000000@0.88:t=fill[vdark]",
                f"[vdark][wg_outer]overlay=x=0:y=H-{wh}:format=auto[v1]",
                f"[v1][wg_inner]overlay=x=0:y=H-{wh}:format=auto[v2]",
                f"[v2][wg_core]overlay=x=0:y=H-{wh}:format=auto[vfinal]",
            ])
            v_out, a_out = "[vfinal]", "[aout]"
        else:
            fc_parts.append(audio_chain_base + "[aout]")
            fc_parts.append(vbase_filter)
            v_out, a_out = "[vbase]", "[aout]"

        fc = ";".join(p for p in fc_parts if p)
        log = self.logs_dir / f"render_final_{video_out.stem}.log"

        # 7. Monta o comando com inputs individuais de áudio
        cmd = ["ffmpeg", "-y", "-hide_banner", "-i", str(video_in)]
        for af in all_audio:
            cmd.extend(["-i", str(af)])
        cmd.extend([
            "-filter_complex", fc,
            "-map", v_out,
            "-map", a_out,
            "-t", f"{dur:.3f}",
            "-c:v", "libx264",
            "-preset", self.final_preset,
            "-crf", str(self.final_crf),
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            str(video_out),
        ])

        print(f"  Renderizando {int(dur) // 60}min {int(dur) % 60}s de vídeo final...")
        res = run_cmd_progress(cmd, log, self.final_timeout_s,
                               total_dur=dur, label="render",
                               proc_reg=self.proc_reg)
        if res.rc != 0 or not video_out.exists():
            print(f"  ✗  Render final falhou rc={res.rc}")
            _skip_rf = ("frame=", "size=", "speed=", "[info]", "Press [q]")
            for line in (res.stderr or "").splitlines():
                stripped = line.strip()
                if not stripped:
                    continue
                if any(stripped.startswith(s) for s in _skip_rf):
                    continue
                print(f"     {stripped}")
            print(f"     CMD: {' '.join(cmd)}")
            return False

        out_dur = _get_duration(video_out)
        print(f"  ✓  Render final: {n_audio} input(s) | {len(tracks)} faixa(s) | "
              f"duração final: {int(out_dur) // 60}min {int(out_dur) % 60}s")
        return True

    # ------------------------------------------------------------------ #
    # Thumbnail                                                           #
    # ------------------------------------------------------------------ #

    def generate_thumbnail(self, video_path: Path, thumb_out: Path) -> bool:
        dur = _get_duration(video_path)
        if dur <= 1.0:
            return False

        candidates: List[Path] = []
        for i, t in enumerate([dur * 0.25, dur * 0.50, dur * 0.75], 1):
            tmp = self.thumbs_dir / f"{thumb_out.stem}_cand{i}.jpg"
            log = self.logs_dir / f"thumb_cand{i}_{thumb_out.stem}.log"
            cmd = [
                "ffmpeg", "-y", "-hide_banner",
                "-ss", str(t), "-i", str(video_path),
                "-frames:v", "1",
                "-vf", "eq=contrast=1.12:saturation=1.08,unsharp=3:3:0.8:3:3:0.2",
                "-q:v", "2", str(tmp),
            ]
            res = run_cmd_capture(cmd, log, 120, self.proc_reg)
            if res.rc == 0 and tmp.exists() and tmp.stat().st_size > 10_000:
                candidates.append(tmp)

        if not candidates:
            return False

        best = max(candidates, key=lambda p: p.stat().st_size)
        try:
            if thumb_out.exists():
                thumb_out.unlink(missing_ok=True)
            shutil.move(str(best), str(thumb_out))
        except Exception:
            return False
        finally:
            for c in candidates:
                if c.exists() and c != thumb_out:
                    try:
                        c.unlink(missing_ok=True)
                    except Exception:
                        pass

        return True

    # ------------------------------------------------------------------ #
    # Salvar metadados YouTube                                            #
    # ------------------------------------------------------------------ #

    def _save_metadata(self, video_path: Path, metadata: Dict) -> None:
        meta_file = video_path.with_suffix(".meta.json")
        try:
            with meta_file.open("w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            print(f"  ✓  Metadata: {meta_file.name}")
        except Exception as e:
            print(f"  ⚠  Falha ao salvar metadata: {e}")

    # ------------------------------------------------------------------ #
    # Pipeline principal: um vídeo                                        #
    # ------------------------------------------------------------------ #

    def run_one(self) -> Optional[Path]:
        videos = self.list_videos()
        if not videos:
            subfolder = "vertical" if self.mode == "shorts" else "horizontal"
            print(f"  ✗  Nenhum vídeo em input_videos/{subfolder}/ (ou input_videos/).")
            return None

        target_total = random.randint(self.mode_cfg.dur_min, self.mode_cfg.dur_max)

        # Resolução final
        if self.target_res:
            final_w, final_h = self.target_res
        else:
            base = self.get_video_info(videos[0])
            final_w, final_h = int(base["width"]), int(base["height"])
            # Para modos YouTube (não-shorts): garante mínimo 1920×1080.
            # O _lofi_camera_filter já faz scale+crop para o target, então
            # upscalar aqui custa apenas o encode — qualidade sempre Full HD.
            if self.mode != "shorts" and final_w < 1920:
                final_w, final_h = 1920, 1080
            elif self.enable_upscale and self.upscale_quality != "none" and final_w < 1920:
                final_w, final_h = 1920, 1080

        final_w = _safe_int_even(final_w, 2)
        final_h = _safe_int_even(final_h, 2)

        print(f"\n  Studio Engine — modo={self.mode} | {final_w}x{final_h} @ {ENGINE_FPS}fps")
        print(f"  Duração alvo: {target_total//60}min | efeito: {self.mode_cfg.effect_intensity:.2f}")

        # --- Selecionar único vídeo para loop ---
        clip = self.pick_single_video(videos, target_total)
        if not clip:
            print("  ✗  Não foi possível selecionar vídeo.")
            return None

        temp_dir = self.logs_dir / f"temp_{int(time.time())}"
        temp_dir.mkdir(parents=True, exist_ok=True)

        try:
            print("\n  Processando vídeo (loop)...")
            mute_out = self.process_clip(clip, 0, temp_dir, final_w, final_h)
            if not mute_out:
                print("  ✗  Falha ao processar vídeo.")
                return None

            ts   = int(time.time())
            seed = hashlib.md5(f"{ts}{random.random()}".encode()).hexdigest()[:8]
            out_final = self.output_dir / f"{self.mode}_{ts}_{seed}.mp4"

            # --- Render final (áudio playlist + texto + visualizador) ---
            print("\n  Render final (áudio + animações + waveform)...")
            ok = self.render_final(
                video_in=mute_out,
                video_out=out_final,
                video_w=final_w,
                video_h=final_h,
            )
            try:
                mute_out.unlink(missing_ok=True)
            except Exception:
                pass
            if not ok:
                return None

            # --- Thumbnail ---
            if self.make_thumbs:
                thumb = self.thumbs_dir / f"{out_final.stem}.jpg"
                if self.generate_thumbnail(out_final, thumb):
                    print(f"  ✓  Thumbnail: {thumb.name}")
                else:
                    print("  ⚠  Não foi possível gerar thumbnail.")

            # --- Metadados YouTube ---
            if self._ai_enabled:
                dur_min = int(_get_duration(out_final) // 60)
                meta = self.deepseek.generate_youtube_metadata(
                    style=self.mode, phrases=[], duration_min=dur_min
                )
                self._save_metadata(out_final, meta)

            size_mb = out_final.stat().st_size / (1024 * 1024)
            print(f"\n  Concluido: {out_final.name} ({size_mb:.1f} MB)")
            return out_final

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def run_batch(self, n: int) -> List[Path]:
        outs: List[Path] = []
        for i in range(n):
            print(f"\n{'='*68}\n  JOB {i+1}/{n} — {self.mode.upper()}\n{'='*68}")
            try:
                out = self.run_one()
            except KeyboardInterrupt:
                print("  Batch interrompido.")
                break
            if out:
                outs.append(out)
            if i < n - 1:
                time.sleep(random.uniform(2, 5))
        return outs


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Studio Engine — gerador de vídeos evergreen lo-fi/relaxing para YouTube",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Lo-fi com IA ativa (chave em config.json)
  python studio_engine.py --mode lofi --input-dir ./input_videos --thumbnails

  # Sem IA (frases e metadados desativados)
  python studio_engine.py --mode relaxing --input-dir ./input_videos --no-ai

  # Sessão de estudo longa, 3 vídeos em paralelo
  python studio_engine.py --mode study --input-dir ./input_videos --num-videos 3 --workers 2

  # YouTube Shorts (9:16 automático)
  python studio_engine.py --mode shorts --input-dir ./input_videos --encoder nvenc
        """,
    )

    # Modo
    p.add_argument("--mode", choices=list(MODES), required=True,
                   help=f"Estilo do vídeo: {', '.join(MODES)}")

    # Diretórios
    p.add_argument("--input-dir", required=True, help="Pasta com vídeos de fundo (backgrounds)")
    p.add_argument("--output-dir",    default="output")
    p.add_argument("--logs-dir",      default="logs")
    p.add_argument("--thumbs-dir",    default="thumbnails")
    p.add_argument("--processed-dir", default="processed")
    p.add_argument("--failed-dir",    default="failed")

    # Processamento
    p.add_argument("--workers",            type=int,   default=1)
    p.add_argument("--num-videos",         type=int,   default=1)
    p.add_argument("--clip-timeout",       type=int,   default=900)
    p.add_argument("--clip-timeout-mult",  type=float, default=1.0)
    p.add_argument("--final-timeout",      type=int,   default=7200,
                   help="Timeout para render final (s). Videos longos precisam de mais tempo.")

    # Encoding
    p.add_argument("--final-crf",    type=int, default=20)
    p.add_argument("--final-preset", default="medium")
    p.add_argument("--concat-copy",  action="store_true")
    p.add_argument("--encoder",      choices=["x264", "nvenc"], default="x264")
    p.add_argument("--nvenc-preset", default="p5")
    p.add_argument("--nvenc-cq",     type=int, default=19)
    p.add_argument("--nvenc-tune",   default="hq")

    # Resolução
    p.add_argument("--enable-upscale", action="store_true")
    p.add_argument("--upscale", choices=["none", "low", "medium", "high"], default="high")
    p.add_argument("--target-res", nargs=2, type=int, metavar=("W", "H"),
                   help="Resolução de saída. Shorts usa 1080x1920 por padrão.")

    # Filtros visuais extras
    p.add_argument("--enhance-color", action="store_true")
    p.add_argument("--denoise",       action="store_true")
    p.add_argument("--stabilize",     action="store_true")

    # Áudio
    p.add_argument("--audio-music", help="Pasta de músicas lo-fi (padrão: audio_musicas)")
    p.add_argument("--vol-music",   type=float, default=1.0)
    p.add_argument("--fade-in",     type=float, default=None)
    p.add_argument("--fade-out",    type=float, default=None)

    # IA / metadados
    p.add_argument("--no-ai",         action="store_true",
                   help="Desativar geração de metadados YouTube pela IA. "
                        "A chave API é configurada em config.json.")
    p.add_argument("--no-visualizer", action="store_true", help="Desativar waveform visualizer")

    # Saída
    p.add_argument("--thumbnails", action="store_true")

    return p


def main():
    parser = build_parser()
    args   = parser.parse_args()

    engine = StudioEngine(args)

    if args.no_visualizer:
        engine.visualizer_enabled = False

    outs = engine.run_batch(int(args.num_videos))

    print(f"\n{'='*68}")
    print(f"  Concluido. Gerados: {len(outs)} vídeos")
    for i, o in enumerate(outs, 1):
        mb = o.stat().st_size / (1024 * 1024)
        print(f"    {i}. {o.name}  ({mb:.1f} MB)")
    print(f"{'='*68}")


if __name__ == "__main__":
    main()
