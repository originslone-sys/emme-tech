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
import concurrent.futures
import hashlib
import json
import os
import random
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
from text_animator import TextAnimator
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
        # Chave placeholder não conta como válida
        if api_key in ("", "YOUR_DEEPSEEK_KEY_HERE"):
            api_key = ""
        self.deepseek = DeepSeekClient(
            api_key=api_key,
            model=_ds.get("model", "deepseek-chat"),
            base_url=_ds.get("base_url", "https://api.deepseek.com/v1"),
            timeout_s=int(_ds.get("timeout_s", 30)),
        )

        _ph = self.cfg_json.get("phrases", {})
        # --no-ai desativa IA completamente (sem frases e sem metadados)
        ai_enabled = not getattr(args, "no_ai", False)
        self.phrases_enabled   = ai_enabled and _ph.get("enabled", True)
        self.phrases_count     = int(getattr(args, "phrases_count", None) or _ph.get("count_per_video", 6))
        self.phrase_display    = float(_ph.get("display_duration_s", 9.0))
        self.phrase_fade       = float(_ph.get("fade_in_s", 0.9))
        self.phrase_categories = _ph.get("categories", ["reflection", "motivation", "mindfulness", "positivity", "stoicism"])
        self._ai_enabled       = ai_enabled

        _tx = self.cfg_json.get("text", {})
        self.text_animator = TextAnimator(
            font_path=_tx.get("font_path", ""),
            font_size=int(_tx.get("font_size_base", 54)),
            palette=self.palette,
            max_chars=int(_tx.get("line_max_chars", 42)),
        )
        self.anim_styles = _tx.get("animation_styles",
                                   ["fade_center", "slide_left", "slide_bottom", "glow_pulse", "cinematic"])

        # Visualizer / progress / track
        _vis = self.cfg_json.get("visualizer", {})
        self.visualizer_enabled = _vis.get("enabled", True)
        self.vis_height_pct     = float(_vis.get("height_pct", 0.07))
        self.vis_mode           = self.visual.get("waves_mode", _vis.get("mode", "cline"))
        self.vis_scale          = self.visual.get("waves_scale", _vis.get("scale", "sqrt"))

        _pb = self.cfg_json.get("progress_bar", {})
        self.progress_enabled = _pb.get("enabled", True)
        self.progress_height  = int(_pb.get("height_px", 3))

        _td = self.cfg_json.get("track_display", {})
        self.track_display_enabled  = _td.get("enabled", True)
        self.track_display_duration = float(_td.get("duration_s", 7.0))

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
        if not self.input_dir.exists():
            return []
        vids: List[Path] = []
        for ext in VIDEO_EXTS:
            vids.extend(self.input_dir.glob(f"*{ext}"))
            vids.extend(self.input_dir.glob(f"*{ext.upper()}"))
        vids = sorted({p for p in vids if p.is_file()},
                      key=lambda p: p.stat().st_mtime, reverse=True)
        return vids

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
            f"scale={sw}:{sh}:flags=lanczos,"
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
    # Filtros de qualidade adicionais (denoise, stabilize, upscale)       #
    # ------------------------------------------------------------------ #

    def _quality_filters(self, w: int, h: int, tw: int, th: int) -> List[str]:
        filters: List[str] = []
        if self.enable_stabilize:
            filters.append("deshake=rx=48:ry=48")
        if self.enable_denoise:
            filters.append("hqdn3d=3:2:4:3")
        if self.enable_color:
            filters.append("eq=brightness=0.01:contrast=1.03:saturation=1.05")
        if (tw, th) != (w, h) and (tw > 0 and th > 0):
            algo = {"low": "bilinear", "medium": "spline"}.get(self.upscale_quality, "lanczos")
            filters.append(f"scale={tw}:{th}:flags={algo}")
            filters.append("unsharp=3:3:0.6:3:3:0.15")
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

        # --- Filtros de qualidade ---
        filters.extend(self._quality_filters(
            clip.get("width", final_w), clip.get("height", final_h), final_w, final_h
        ))

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

        res = run_cmd_capture(cmd, log, timeout_s=timeout_s, proc_reg=self.proc_reg)

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
    # Renderização final: áudio + texto + waveform + progress bar         #
    # ------------------------------------------------------------------ #

    def render_final(
        self,
        video_in: Path,
        video_out: Path,
        phrases: List[str],
        track_name: str,
        video_w: int,
        video_h: int,
    ) -> bool:
        """
        Combina em uma única passagem FFmpeg:
          - Mix de áudio (música, fade in/out, loop se necessário)
          - Animações de texto (frases DeepSeek)
          - Visualizador de waveform (beat-reactive)
          - Barra de progresso
          - Track name display
        """
        dur = _get_duration(video_in)
        if dur <= 0.5:
            print("  ✗  Duração inválida para render final.")
            return False

        # Seleciona faixa(s) de música
        music_file = _pick_random_file(self.audio_music_dir, AUDIO_EXTS)
        if not music_file:
            print("  ⚠  Nenhuma música encontrada. Gerando sem áudio.")
            shutil.copy2(video_in, video_out)
            return True

        track_name = track_name or music_file.name

        # Altura do visualizador
        wh = _safe_int_even(int(video_h * self.vis_height_pct), 2)
        wave_color = self.palette.get("waves", "0xF5CBA7@0.45")

        # Filtros de texto
        text_filters = self.text_animator.build_full_text_chain(
            phrases=phrases,
            duration=dur,
            video_w=video_w,
            video_h=video_h,
            track_name=track_name if self.track_display_enabled else "",
            display_duration=self.phrase_display,
            fade_in=self.phrase_fade,
            fade_out=self.phrase_fade,
            styles=self.anim_styles,
            progress_bar=self.progress_enabled,
            progress_height=self.progress_height,
        )

        # Constrói filter_complex
        fade_out_start = max(0.0, dur - self.fade_out)
        vol = self.vol_music

        # Processamento de áudio: trim + fade + volume + resample + limiter
        audio_chain = (
            f"[1:a]atrim=0:{dur:.3f},asetpts=N/SR/TB,"
            f"volume={vol:.3f},"
            f"afade=t=in:st=0:d={self.fade_in:.2f},"
            f"afade=t=out:st={fade_out_start:.3f}:d={self.fade_out:.2f},"
            f"aresample={self.audio_sr},"
            f"aformat=channel_layouts=stereo,"
            f"alimiter=limit=0.95"
        )

        # Cadeia de vídeo: text overlays
        if text_filters:
            video_chain = "[0:v]" + ",".join(text_filters)
        else:
            video_chain = "[0:v]null"

        if self.visualizer_enabled:
            fc_parts = [
                audio_chain + ",asplit=2[aout][awaves]",
                f"[awaves]showwaves=s={video_w}x{wh}:mode={self.vis_mode}"
                f":rate={ENGINE_FPS}:colors={wave_color}:scale={self.vis_scale}[waves]",
                video_chain + "[vtxt]",
                f"[vtxt][waves]overlay=x=0:y=H-{wh}:shortest=1[vfinal]",
            ]
            v_out = "[vfinal]"
            a_out = "[aout]"
        else:
            fc_parts = [
                audio_chain + "[aout]",
                video_chain + "[vfinal]",
            ]
            v_out = "[vfinal]"
            a_out = "[aout]"

        fc = ";".join(fc_parts)
        log = self.logs_dir / f"render_final_{video_out.stem}.log"

        cmd = [
            "ffmpeg", "-y", "-hide_banner",
            "-i", str(video_in),
            "-stream_loop", "-1", "-i", str(music_file),
            "-filter_complex", fc,
            "-map", v_out,
            "-map", a_out,
            "-c:v", "libx264",
            "-preset", self.final_preset,
            "-crf", str(self.final_crf),
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            "-movflags", "+faststart",
            str(video_out),
        ]

        res = run_cmd_capture(cmd, log, self.final_timeout_s, self.proc_reg)
        if res.rc != 0 or not video_out.exists():
            print(f"  ✗  Render final falhou rc={res.rc}")
            return False

        print(f"  ✓  Render final: musica={music_file.name} | frases={len(phrases)}")
        return True

    # ------------------------------------------------------------------ #
    # Thumbnail                                                           #
    # ------------------------------------------------------------------ #

    def generate_thumbnail(self, video_path: Path, thumb_out: Path,
                           best_phrase: str = "") -> bool:
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
            print("  ✗  Nenhum vídeo em input_videos/.")
            return None

        target_total = random.randint(self.mode_cfg.dur_min, self.mode_cfg.dur_max)

        # Resolução final
        if self.target_res:
            final_w, final_h = self.target_res
        else:
            base = self.get_video_info(videos[0])
            final_w, final_h = int(base["width"]), int(base["height"])
            if self.enable_upscale and self.upscale_quality != "none" and final_w < 1920:
                final_w, final_h = 1920, 1080

        final_w = _safe_int_even(final_w, 2)
        final_h = _safe_int_even(final_h, 2)

        print(f"\n  Studio Engine — modo={self.mode} | {final_w}x{final_h} @ {ENGINE_FPS}fps")
        print(f"  Duração alvo: {target_total//60}min | efeito: {self.mode_cfg.effect_intensity:.2f}")

        # --- Gerar frases via DeepSeek ---
        phrases: List[str] = []
        if self.phrases_enabled:
            print("\n  Gerando frases (DeepSeek)...")
            phrases = self.deepseek.generate_phrases(
                categories=self.phrase_categories,
                count=self.phrases_count,
            )
            print(f"  {len(phrases)} frases prontas {'(API)' if self.deepseek.available else '(banco local)'}")
            for i, p in enumerate(phrases, 1):
                print(f"    {i}. {p}")

        # --- Selecionar clips ---
        clips = self.pick_clips(videos, target_total)
        if not clips:
            print("  ✗  Não foi possível selecionar clips.")
            return None

        temp_dir = self.logs_dir / f"temp_{int(time.time())}"
        temp_dir.mkdir(parents=True, exist_ok=True)

        processed: List[Tuple[int, Path]] = []

        try:
            print(f"\n  Processando {len(clips)} clips...")

            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as ex:
                futs = {
                    ex.submit(self.process_clip, clip, i, temp_dir, final_w, final_h): i
                    for i, clip in enumerate(clips)
                }
                try:
                    for fut in concurrent.futures.as_completed(futs):
                        if self.stop_event.is_set():
                            break
                        i = futs[fut]
                        try:
                            p = fut.result()
                            if p:
                                processed.append((i, p))
                        except Exception as e:
                            print(f"  ✗  Clip {i}: {e}")
                except KeyboardInterrupt:
                    self.stop_event.set()
                    print("\n  Interrompido (Ctrl+C). Finalizando processos FFmpeg...")
                    self.proc_reg.kill_all()
                    try:
                        ex.shutdown(wait=False, cancel_futures=True)
                    except Exception:
                        pass
                    raise

            processed.sort(key=lambda x: x[0])
            clip_paths = [p for _, p in processed]

            if len(clip_paths) < 1:
                print("  ✗  Nenhum clip processado.")
                return None
            if len(clip_paths) < 2 and self.mode != "shorts":
                print("  ✗  Poucos clips para concatenar.")
                return None

            ts   = int(time.time())
            seed = hashlib.md5(f"{ts}{random.random()}".encode()).hexdigest()[:8]
            out_mute  = self.output_dir / f"{self.mode}_mute_{ts}_{seed}.mp4"
            out_final = self.output_dir / f"{self.mode}_{ts}_{seed}.mp4"

            # --- Concat ---
            print("\n  Concatenando clips...")
            if not self.concat_video_only(clip_paths, out_mute, final_w, final_h):
                print("  ✗  Concat falhou.")
                return None

            # --- Render final (áudio + texto + visualizador) ---
            print("\n  Render final (áudio + animações + waveform)...")
            ok = self.render_final(
                video_in=out_mute,
                video_out=out_final,
                phrases=phrases,
                track_name="",
                video_w=final_w,
                video_h=final_h,
            )
            try:
                out_mute.unlink(missing_ok=True)
            except Exception:
                pass
            if not ok:
                return None

            # --- Thumbnail ---
            if self.make_thumbs:
                thumb = self.thumbs_dir / f"{out_final.stem}.jpg"
                if self.generate_thumbnail(out_final, thumb, phrases[0] if phrases else ""):
                    print(f"  ✓  Thumbnail: {thumb.name}")
                else:
                    print("  ⚠  Não foi possível gerar thumbnail.")

            # --- Metadados YouTube ---
            if self._ai_enabled:
                dur_min = int(_get_duration(out_final) // 60)
                meta = self.deepseek.generate_youtube_metadata(
                    style=self.mode, phrases=phrases, duration_min=dur_min
                )
                self._save_metadata(out_final, meta)

            # --- Move fontes para processed ---
            used_sources = {Path(c["path"]) for c in clips}
            for src in used_sources:
                if src.exists():
                    dest = self.processed_dir / src.name
                    if dest.exists():
                        dest = self.processed_dir / f"{src.stem}_{ts}{src.suffix}"
                    try:
                        shutil.move(str(src), str(dest))
                    except Exception:
                        pass

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

    # IA / frases
    p.add_argument("--no-ai",          action="store_true",
                   help="Desativar IA completamente (sem frases animadas, sem metadados YouTube). "
                        "A chave API é configurada em config.json.")
    p.add_argument("--phrases-count",  type=int, default=6, help="Número de frases por vídeo")
    p.add_argument("--no-visualizer",  action="store_true", help="Desativar waveform visualizer")

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
