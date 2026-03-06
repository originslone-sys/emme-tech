#!/usr/bin/env python3
"""
STUDIO ENGINE — Edição automática (acervo -> novos vídeos) — Foco em QUALIDADE + PERFORMANCE

Funcionalidades:
- modos teaser | compilado | premium
- MANTÉM áudio original do vídeo (sem substituição por música externa)
- Auto-detecção GPU: usa NVENC+CPU juntos se disponível, senão só CPU
- Maximiza uso de hardware: threads=0, workers=cpu_count, preset agressivo
- upscale inteligente com target-res + sharpen adaptativo
- denoise avançado + enhance-color + stabilize
- micro rotate + grain cinematográfico
- câmera (zoom/pan) via zoompan
- 3 thumbnails por vídeo finalizado
- concat demuxer -c copy com fallback reencode
- timeout dinâmico por clip + Ctrl+C seguro

Requisitos:
- ffmpeg + ffprobe no PATH
"""

import argparse
import concurrent.futures
import hashlib
import json
import io
import os
import random
import re
import sys
import shutil
import signal
import subprocess
import threading
import time
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple


VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi", ".flv", ".wmv", ".mpeg", ".mpg"}

ENGINE_FPS = 30  # FIX: engine em 30 fps sempre


def _safe_int_even(x: float, minimum: int = 2) -> int:
    v = int(round(float(x)))
    if v < minimum:
        v = minimum
    if v % 2 != 0:
        v -= 1
    if v < minimum:
        v = minimum
    if v % 2 != 0:
        v += 1
    return v


def _ffprobe_json(args: List[str]) -> Dict:
    try:
        out = subprocess.check_output(["ffprobe", *args], text=True, stderr=subprocess.STDOUT)
        return json.loads(out)
    except Exception:
        return {}


def _get_duration(path: Path) -> float:
    data = _ffprobe_json([
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json",
        str(path)
    ])
    try:
        return float(data["format"]["duration"])
    except Exception:
        return 0.0


# ---------------- Hardware Detection ----------------

def _detect_nvenc() -> bool:
    """Testa se h264_nvenc está disponível (GPU NVIDIA com driver compatível)."""
    try:
        p = subprocess.run(
            ["ffmpeg", "-hide_banner", "-f", "lavfi", "-i", "nullsrc=s=256x256:d=0.1",
             "-c:v", "h264_nvenc", "-f", "null", "-"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=10,
        )
        return p.returncode == 0
    except Exception:
        return False


def _get_cpu_count() -> int:
    """Retorna número de CPUs disponíveis (mínimo 1)."""
    try:
        return max(1, os.cpu_count() or 1)
    except Exception:
        return 1


def _optimal_workers(cpu_count: int, has_gpu: bool) -> int:
    """Calcula workers ideais: com GPU pode usar mais parallelismo."""
    if has_gpu:
        return max(2, min(cpu_count, 8))
    return max(1, min(cpu_count // 2, 6))


# ---------------- Robust Subprocess + Kill Tree ----------------

@dataclass
class CmdResult:
    rc: int
    elapsed: float
    stdout: str
    stderr: str
    timed_out: bool


class ProcRegistry:
    """Mantém referência de processos ativos para matar no Ctrl+C."""
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._procs: set[subprocess.Popen] = set()

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
    """
    Windows: taskkill /T /F
    Linux/Mac: mata grupo (se start_new_session=True).
    """
    if p.poll() is not None:
        return

    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(p.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    else:
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass


def run_cmd_capture(cmd: List[str], log_file: Path, timeout_s: int, proc_reg: Optional[ProcRegistry] = None) -> CmdResult:
    """
    Executa cmd, captura stdout/stderr, escreve no log, aplica timeout e mata árvore se estourar.
    """
    log_file.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    timed_out = False

    creationflags = 0
    start_new_session = False
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        start_new_session = True

    p = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=creationflags,
        start_new_session=start_new_session
    )

    if proc_reg:
        proc_reg.add(p)

    try:
        try:
            out, err = p.communicate(timeout=timeout_s)
            rc = int(p.returncode or 0)
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                kill_process_tree(p)
            finally:
                out, err = p.communicate()
            rc = 124
    finally:
        if proc_reg:
            proc_reg.discard(p)

    elapsed = time.time() - t0

    try:
        with log_file.open("w", encoding="utf-8", errors="replace") as lf:
            lf.write("CMD:\n")
            lf.write(" ".join(cmd) + "\n\n")
            lf.write(f"TIMEOUT_S={timeout_s}\n")
            lf.write(f"ELAPSED_S={elapsed:.2f}\n")
            lf.write(f"RC={rc}\n")
            lf.write(f"TIMED_OUT={timed_out}\n")
            lf.write("\n--- STDERR ---\n")
            lf.write(err or "")
            lf.write("\n--- STDOUT ---\n")
            lf.write(out or "")
    except Exception:
        pass

    return CmdResult(rc=rc, elapsed=elapsed, stdout=out or "", stderr=err or "", timed_out=timed_out)


# ---------------- Progress Bar Helpers ----------------

_RE_TIME = re.compile(r"time=(\d+):(\d+):(\d+(?:\.\d+)?)")
_BAR_WIDTH = 30


def _parse_ffmpeg_time(line: str) -> Optional[float]:
    """Extrai 'time=HH:MM:SS.xx' do stderr do FFmpeg e retorna segundos."""
    m = _RE_TIME.search(line)
    if m:
        return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    return None


def _format_bar(pct: float, width: int = _BAR_WIDTH) -> str:
    filled = int(width * pct)
    bar = "\u2588" * filled + "\u2591" * (width - filled)
    return bar


def _format_time(secs: float) -> str:
    m, s = divmod(int(secs), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


_RE_OUTTIME = re.compile(r"out_time=(\d+):(\d+):(\d+(?:\.\d+)?)")


def run_cmd_with_progress(
    cmd: List[str],
    log_file: Path,
    timeout_s: int,
    total_duration: float,
    label: str = "",
    proc_reg: Optional[ProcRegistry] = None,
) -> CmdResult:
    """
    Executa FFmpeg com barra de progresso em tempo real.
    Usa -progress pipe:1 para forçar output machine-readable no stdout.
    Lê com readline() para entrega imediata (sem buffer do iterador).
    """
    log_file.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    timed_out = False
    stderr_chunks: List[bytes] = []

    # Injeta -progress pipe:1 no comando (logo após "ffmpeg")
    prog_cmd = list(cmd)
    prog_cmd[1:1] = ["-progress", "pipe:1"]

    creationflags = 0
    start_new_session = False
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        start_new_session = True

    p = subprocess.Popen(
        prog_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False,
        creationflags=creationflags,
        start_new_session=start_new_session,
    )

    if proc_reg:
        proc_reg.add(p)

    last_pct = -1.0

    def _read_stderr():
        """Captura stderr inteiro para log."""
        try:
            while True:
                chunk = p.stderr.read(4096)
                if not chunk:
                    break
                stderr_chunks.append(chunk)
        except Exception:
            pass

    def _read_stdout_progress():
        """Lê stdout com readline() (sem buffer), parseia out_time=."""
        nonlocal last_pct
        try:
            while True:
                raw_line = p.stdout.readline()
                if not raw_line:
                    break
                decoded = raw_line.decode("utf-8", errors="replace").strip()
                m = _RE_OUTTIME.search(decoded)
                if m and total_duration > 0:
                    t = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
                    pct = min(t / total_duration, 1.0)
                    # Atualiza a cada 5% para não poluir o terminal
                    next_threshold = (int(last_pct * 20) + 1) / 20.0 if last_pct >= 0 else 0.0
                    if pct >= next_threshold or (last_pct < 0 and pct > 0):
                        last_pct = pct
                        elapsed = time.time() - t0
                        eta = (elapsed / pct - elapsed) if pct > 0.01 else 0
                        bar = _format_bar(pct)
                        print(
                            f"  {label}|{bar}| {pct*100:5.1f}% "
                            f"| {_format_time(elapsed)}/{_format_time(total_duration)} "
                            f"| ETA {_format_time(eta)}"
                        )
        except Exception:
            pass

    t_err = threading.Thread(target=_read_stderr, daemon=True)
    t_prog = threading.Thread(target=_read_stdout_progress, daemon=True)
    t_err.start()
    t_prog.start()

    try:
        try:
            p.wait(timeout=timeout_s)
            rc = int(p.returncode or 0)
        except subprocess.TimeoutExpired:
            timed_out = True
            kill_process_tree(p)
            p.wait()
            rc = 124
    finally:
        if proc_reg:
            proc_reg.discard(p)

    t_err.join(timeout=5)
    t_prog.join(timeout=5)

    # Finaliza a barra de progresso
    elapsed_final = time.time() - t0
    if not timed_out and rc == 0:
        bar = _format_bar(1.0)
        print(
            f"  {label}|{bar}| 100.0% "
            f"| {_format_time(elapsed_final)}/{_format_time(total_duration)} "
            f"| Concluido!"
        )

    elapsed = time.time() - t0
    out = ""  # stdout consumido pelo parser de progresso
    err = b"".join(stderr_chunks).decode("utf-8", errors="replace")

    try:
        with log_file.open("w", encoding="utf-8", errors="replace") as lf:
            lf.write("CMD:\n")
            lf.write(" ".join(cmd) + "\n\n")
            lf.write(f"TIMEOUT_S={timeout_s}\n")
            lf.write(f"ELAPSED_S={elapsed:.2f}\n")
            lf.write(f"RC={rc}\n")
            lf.write(f"TIMED_OUT={timed_out}\n")
            lf.write("\n--- STDERR ---\n")
            lf.write(err)
            lf.write("\n--- STDOUT ---\n")
            lf.write(out)
    except Exception:
        pass

    return CmdResult(rc=rc, elapsed=elapsed, stdout=out, stderr=err, timed_out=timed_out)


def estimate_timeout_seconds(
    clip_dur_s: float,
    stabilize: bool,
    denoise: bool,
    upscale: bool,
    intensity: float,
    base_timeout_s: int,
    multiplier: float,
) -> int:
    # crop+scale é rápido; efeitos pesados são stabilize/denoise/upscale
    speed_min = 0.25
    if stabilize:
        speed_min *= 0.70
    if denoise:
        speed_min *= 0.80
    if upscale:
        speed_min *= 0.70

    # Penalidade composta: quando 3+ efeitos pesados estão ativos juntos
    heavy_count = sum([stabilize, denoise, upscale])
    if heavy_count >= 3:
        speed_min *= 0.60  # combinação extrema
    elif heavy_count >= 2:
        speed_min *= 0.80

    inten = max(0.0, min(1.0, float(intensity)))
    speed_min *= max(0.55, 1.0 - 0.35 * inten)
    speed_min = max(0.02, speed_min)

    estimated = clip_dur_s / speed_min
    timeout = estimated * 2.0 + 120.0  # margem maior: 2x + 2min base
    timeout *= max(1.0, float(multiplier))

    timeout = max(timeout, float(base_timeout_s))
    timeout = min(timeout, 6.0 * 60.0 * 60.0)  # teto 6h (era 4h)
    return int(timeout)


# ---------------- Config ----------------

@dataclass
class ModeConfig:
    dur_min: int
    dur_max: int
    clip_len_min: int
    clip_len_max: int
    min_clips: int
    max_clips: int
    effect_intensity: float  # 0..1


MODES = {
    "teaser": ModeConfig(dur_min=6 * 60,  dur_max=8 * 60,  clip_len_min=120, clip_len_max=180, min_clips=2, max_clips=5, effect_intensity=0.85),
    "compilado": ModeConfig(dur_min=10 * 60, dur_max=14 * 60, clip_len_min=180, clip_len_max=300, min_clips=2, max_clips=5, effect_intensity=0.60),
    "premium": ModeConfig(dur_min=14 * 60, dur_max=18 * 60, clip_len_min=300, clip_len_max=420, min_clips=2, max_clips=3,  effect_intensity=0.40),
}


class StudioEngine:
    def __init__(self, args: argparse.Namespace):
        self.input_dir = Path(args.input_dir)
        self.output_dir = Path(args.output_dir)
        self.logs_dir = Path(args.logs_dir)
        self.thumbs_dir = Path(args.thumbs_dir)
        self.processed_dir = Path(args.processed_dir)
        self.failed_dir = Path(args.failed_dir)

        for d in [self.output_dir, self.logs_dir, self.thumbs_dir, self.processed_dir, self.failed_dir]:
            d.mkdir(parents=True, exist_ok=True)

        self.mode = args.mode.lower()
        if self.mode not in MODES:
            raise ValueError(f"Modo inválido: {self.mode}")
        self.cfg = MODES[self.mode]

        self._assert_tools()

        # --- Auto-detecção de hardware ---
        self.cpu_count = _get_cpu_count()
        self.has_gpu = _detect_nvenc()

        # Encoder: auto-detecta se não forçado
        encoder_arg = args.encoder
        if encoder_arg == "auto":
            self.encoder = "nvenc" if self.has_gpu else "x264"
        else:
            self.encoder = encoder_arg

        # Workers: auto = máximo baseado no hardware
        workers_arg = int(args.workers)
        if workers_arg <= 0:
            self.max_workers = _optimal_workers(self.cpu_count, self.has_gpu)
        else:
            self.max_workers = workers_arg

        # Threads ffmpeg: 0 = usa todos os cores
        self.ffmpeg_threads = int(args.ffmpeg_threads)

        self.clip_timeout_s = int(args.clip_timeout)
        self.clip_timeout_mult = float(args.clip_timeout_mult)
        self.final_timeout_s = int(args.final_timeout)

        self.final_crf = int(args.final_crf)
        self.final_preset = args.final_preset
        self.concat_copy = bool(args.concat_copy)

        self.nvenc_preset = args.nvenc_preset
        self.nvenc_cq = int(args.nvenc_cq)
        self.nvenc_tune = args.nvenc_tune

        self.enable_upscale = bool(args.enable_upscale)
        self.upscale_quality = args.upscale
        self.target_res = tuple(args.target_res) if args.target_res else None

        self.enable_denoise = bool(args.denoise)
        self.enable_stabilize = bool(args.stabilize)
        self.enable_enhance_color = bool(args.enhance_color)

        self.make_thumbs = bool(args.thumbnails)
        self.num_thumbs = max(1, min(10, int(args.num_thumbs)))

        self._filters_cache = None
        self.stop_event = threading.Event()
        self.proc_reg = ProcRegistry()

        self._print_hardware_info()

    def _assert_tools(self) -> None:
        for tool in ("ffmpeg", "ffprobe"):
            try:
                subprocess.check_output([tool, "-version"], stderr=subprocess.STDOUT, text=True)
            except Exception as e:
                raise RuntimeError(f"Ferramenta obrigatória não encontrada/exec: {tool}. Erro: {e}")

    def _print_hardware_info(self) -> None:
        gpu_status = f"NVENC (encoder={self.encoder})" if self.has_gpu else "Nenhuma (CPU only)"
        print(f"\n{'='*60}")
        print(f"  HARDWARE DETECTADO")
        print(f"  CPU cores: {self.cpu_count}")
        print(f"  GPU NVIDIA: {gpu_status}")
        print(f"  Workers paralelos: {self.max_workers}")
        print(f"  FFmpeg threads: {'auto (todos)' if self.ffmpeg_threads == 0 else self.ffmpeg_threads}")
        print(f"  Encoder: {self.encoder}")
        print(f"{'='*60}")

    def _ffmpeg_filters(self) -> str:
        if self._filters_cache is not None:
            return self._filters_cache
        try:
            out = subprocess.check_output(["ffmpeg", "-hide_banner", "-filters"], text=True, stderr=subprocess.STDOUT)
            self._filters_cache = out
        except Exception:
            self._filters_cache = ""
        return self._filters_cache

    def _has_filter(self, name: str) -> bool:
        txt = self._ffmpeg_filters()
        return f" {name} " in txt

    def list_videos(self) -> List[Path]:
        if not self.input_dir.exists():
            return []
        vids: List[Path] = []
        for ext in VIDEO_EXTS:
            vids.extend(self.input_dir.glob(f"*{ext}"))
            vids.extend(self.input_dir.glob(f"*{ext.upper()}"))
        vids = [p for p in vids if p.is_file()]
        vids.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return vids

    def get_video_info(self, path: Path) -> Dict:
        info = {"path": str(path), "name": path.name, "size_mb": path.stat().st_size / (1024 * 1024)}

        data = _ffprobe_json([
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,r_frame_rate,codec_name",
            "-of", "json",
            str(path)
        ])

        w, h, fps = 1920, 1080, 30.0
        try:
            s = data["streams"][0]
            w = int(s.get("width") or 1920)
            h = int(s.get("height") or 1080)
            fr = s.get("r_frame_rate") or "30/1"
            if "/" in fr:
                num, den = fr.split("/", 1)
                fps = (int(num) / int(den)) if int(den) else 30.0
            else:
                fps = float(fr)
        except Exception:
            pass

        dur = _get_duration(path)
        info.update({
            "width": w, "height": h, "fps": fps,
            "duration": dur,
            "duration_str": str(timedelta(seconds=int(dur)))
        })
        return info

    def pick_clips(self, videos: List[Path], target_total_s: int) -> List[Dict]:
        if not videos:
            return []

        shuffled = videos[:]
        random.shuffle(shuffled)

        infos: List[Dict] = []
        for v in shuffled[:max(self.cfg.max_clips * 2, 10)]:
            inf = self.get_video_info(v)
            if inf["duration"] >= self.cfg.clip_len_min:
                infos.append(inf)

        if not infos:
            return []

        clips: List[Dict] = []
        total = 0.0
        desired = random.randint(self.cfg.min_clips, min(self.cfg.max_clips, len(infos)))

        pool = infos[:]
        random.shuffle(pool)

        def choose_segment(inf: Dict, seg_len: float) -> Dict:
            d = float(inf["duration"])
            seg_len = min(seg_len, d)
            start_max = max(0.0, d - seg_len)
            start = random.uniform(0.0, start_max) if start_max > 0 else 0.0
            clip = dict(inf)
            clip["start"] = start
            clip["end"] = start + seg_len
            clip["seg_len"] = seg_len
            return clip

        for inf in pool[:desired]:
            seg_len = random.uniform(self.cfg.clip_len_min, min(self.cfg.clip_len_max, float(inf["duration"])))
            clip = choose_segment(inf, seg_len)
            clips.append(clip)
            total += clip["seg_len"]

        remaining = pool[desired:]
        while total < target_total_s and remaining and len(clips) < int(self.cfg.max_clips * 1.8):
            inf = random.choice(remaining)
            remaining.remove(inf)
            seg_len = random.uniform(self.cfg.clip_len_min, min(self.cfg.clip_len_max, float(inf["duration"])))
            clip = choose_segment(inf, seg_len)
            clips.append(clip)
            total += clip["seg_len"]

        print(f"\n📋 Clips selecionados: {len(clips)} | alvo={target_total_s}s | total≈{int(total)}s")
        return clips

    # --------- CÂMERA (zoompan) ----------

    def _camera_filter(self, base_w: int, base_h: int, clip_dur: float) -> Tuple[str, str]:
        """Efeito de câmera usando crop+scale (rápido e confiável para vídeo).
        zoompan é lento/instável com vídeo — crop+scale usa expressões com 'n' (frame number).
        """
        layer = random.choices(
            population=["wide", "close70", "super50"],
            weights=[0.30, 0.45, 0.25],
            k=1
        )[0]

        crop_scale = 1.00 if layer == "wide" else (0.70 if layer == "close70" else 0.50)

        ow = _safe_int_even(base_w, 2)
        oh = _safe_int_even(base_h, 2)

        tech = random.choices(
            population=["zoom", "panx", "pany"],
            weights=[0.45, 0.30, 0.25],
            k=1
        )[0]

        inten = max(0.0, min(1.0, float(self.cfg.effect_intensity)))
        total_frames = max(1, int(float(clip_dur) * ENGINE_FPS))

        # Pre-scale: normaliza input para ow x oh antes de crop
        pre_scale = f"scale={ow}:{oh}:flags=bilinear"

        if layer == "wide":
            filt = pre_scale
            tag = "cam:wide"
            return filt, tag

        # Para close70/super50: crop animado após normalização
        # crop_w/crop_h = tamanho da janela de crop (menor que ow x oh)
        crop_w = _safe_int_even(ow * crop_scale, 2)
        crop_h = _safe_int_even(oh * crop_scale, 2)

        # Margem disponível para pan
        margin_x = ow - crop_w  # ex: 1920-1344=576 para close70
        margin_y = oh - crop_h

        pan_frac = 0.25 + 0.45 * inten

        if tech == "zoom":
            # Zoom progressivo: crop começa grande, diminui ao centro
            zoom_amount = 0.015 + 0.030 * inten
            start_w = _safe_int_even(min(crop_w * (1 + zoom_amount), ow), 2)
            start_h = _safe_int_even(min(crop_h * (1 + zoom_amount), oh), 2)
            # w/h diminuem de start a crop ao longo do clip
            w_expr = f"{start_w}-({start_w}-{crop_w})*n/{total_frames}"
            h_expr = f"{start_h}-({start_h}-{crop_h})*n/{total_frames}"
            x_expr = "(in_w-ow)/2"
            y_expr = "(in_h-oh)/2"
            filt = (
                f"{pre_scale},"
                f"crop=w='{w_expr}':h='{h_expr}':x='{x_expr}':y='{y_expr}',"
                f"scale={ow}:{oh}:flags=bilinear"
            )
            tag = f"cam:zoom+{layer}"

        elif tech == "panx":
            max_slide = int(margin_x * pan_frac)
            x_expr = f"{max_slide}*n/{total_frames}"
            y_expr = f"(in_h-{crop_h})/2"
            filt = (
                f"{pre_scale},"
                f"crop={crop_w}:{crop_h}:x='{x_expr}':y='{y_expr}',"
                f"scale={ow}:{oh}:flags=bilinear"
            )
            tag = f"cam:panx+{layer}"

        else:  # pany
            max_slide = int(margin_y * pan_frac)
            x_expr = f"(in_w-{crop_w})/2"
            y_expr = f"{max_slide}*n/{total_frames}"
            filt = (
                f"{pre_scale},"
                f"crop={crop_w}:{crop_h}:x='{x_expr}':y='{y_expr}',"
                f"scale={ow}:{oh}:flags=bilinear"
            )
            tag = f"cam:pany+{layer}"

        return filt, tag

    # --------- QUALIDADE ----------

    def _quality_filters(self, info: Dict) -> List[str]:
        filters: List[str] = []

        if self.enable_stabilize:
            filters.append("deshake=rx=64:ry=64")

        if self.enable_denoise:
            # hqdn3d sozinho já é suficiente e MUITO mais rápido que nlmeans
            # nlmeans=s=3:p=7:r=15 causava timeout em clips >2min com zoompan+upscale
            filters.append("hqdn3d=3:2:5:3.5")

        if self.enable_enhance_color:
            filters.append("eq=brightness=0.02:contrast=1.06:saturation=1.12:gamma=1.02")
            if self._has_filter("vibrance"):
                filters.append("vibrance=1.18")
            filters.append("colorbalance=rs=0.02:gs=0.01:bs=-0.01:rm=0.01:gm=0.005:bm=-0.005")

        w = int(info.get("width") or 1920)
        h = int(info.get("height") or 1080)

        if self.target_res:
            tw, th = self.target_res
        else:
            if self.enable_upscale and self.upscale_quality != "none":
                if w < 1920:
                    tw, th = 1920, 1080
                elif w < 2560:
                    tw, th = 2560, 1440
                else:
                    tw, th = w, h
            else:
                tw, th = w, h

        tw = _safe_int_even(tw, 2)
        th = _safe_int_even(th, 2)

        if (tw, th) != (w, h):
            algo = "lanczos+accurate_rnd"
            if self.upscale_quality == "low":
                algo = "bilinear"
            elif self.upscale_quality == "medium":
                algo = "spline"
            filters.append(f"scale={tw}:{th}:flags={algo}")

        # sharpen adaptativo: mais forte em upscale, suave em resolução nativa
        if (tw, th) != (w, h):
            filters.append("unsharp=5:5:1.0:5:5:0.3")
        else:
            filters.append("unsharp=3:3:0.6:3:3:0.15")

        return filters

    # --------- ENCODER ARGS ----------

    def _clip_encoder_args(self, q_crf_or_cq: int) -> List[str]:
        if self.encoder == "nvenc":
            return [
                "-c:v", "h264_nvenc",
                "-preset", self.nvenc_preset,
                "-tune", self.nvenc_tune,
                "-rc", "vbr",
                "-cq:v", str(q_crf_or_cq),
                "-b:v", "0",
                "-pix_fmt", "yuv420p",
                "-threads", str(self.ffmpeg_threads),
            ]
        return [
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", str(q_crf_or_cq),
            "-pix_fmt", "yuv420p",
            "-threads", str(self.ffmpeg_threads),
        ]

    # --------- CLIP PROCESS ----------

    def process_clip(self, clip: Dict, idx: int, temp_dir: Path, final_w: int, final_h: int, total_clips: int = 0) -> Optional[Path]:
        if self.stop_event.is_set():
            return None

        src = Path(clip["path"])
        start = float(clip["start"])
        seg_len = max(1.0, float(clip["seg_len"]))

        intensity = max(0.0, min(1.0, float(self.cfg.effect_intensity)))

        filters: List[str] = []

        cam_f, cam_tag = self._camera_filter(final_w, final_h, seg_len)
        filters.append(cam_f)

        if random.random() < (0.25 + 0.20 * intensity):
            ang = random.uniform(-0.25, 0.25) * (0.4 + intensity)
            filters.append(f"rotate={ang}*PI/180:fillcolor=black@0")

        if random.random() < (0.12 + 0.18 * intensity):
            filters.append(f"noise=alls={random.uniform(0.0005, 0.0018)}:allf=t+u")

        speed = 1.0
        af_filters: List[str] = []
        if random.random() < (0.25 + 0.15 * intensity):
            speed = random.uniform(0.992, 1.008)
            filters.append(f"setpts=PTS/{speed}")
            af_filters.append(f"atempo={speed}")

        filters.extend(self._quality_filters(clip))

        # garante formato final: fps + SAR consistente
        filters.append(f"fps={ENGINE_FPS}")
        filters.append("setsar=1")
        filters.append("format=yuv420p")

        # filtros de áudio: normalização + limpeza
        af_filters.append("aresample=44100")
        af_filters.append("dynaudnorm=p=0.9:s=5")

        vf = ",".join(filters)
        af = ",".join(af_filters)

        out = temp_dir / f"clip_{idx:03d}_{src.stem}.mp4"
        log = self.logs_dir / f"clip_{idx:03d}_{src.stem}.log"

        if self.mode == "teaser":
            q = random.randint(18, 21)
        elif self.mode == "compilado":
            q = random.randint(17, 20)
        else:
            q = random.randint(16, 19)

        timeout_s = estimate_timeout_seconds(
            clip_dur_s=seg_len,
            stabilize=self.enable_stabilize,
            denoise=self.enable_denoise,
            upscale=(self.enable_upscale and self.upscale_quality != "none") or bool(self.target_res),
            intensity=self.cfg.effect_intensity,
            base_timeout_s=self.clip_timeout_s,
            multiplier=self.clip_timeout_mult,
        )

        cmd = [
            "ffmpeg", "-y", "-hide_banner",
            "-fflags", "+genpts",
            "-ss", str(start),
            "-i", str(src),
            "-t", str(seg_len),
            "-vf", vf,
            "-af", af,
            "-movflags", "+faststart",
            "-video_track_timescale", "90000",
        ]
        cmd += self._clip_encoder_args(q)
        cmd += ["-c:a", "aac", "-b:a", "192k"]
        cmd += [str(out)]

        clip_label = f"Clip {idx+1}/{total_clips} " if total_clips else f"Clip {idx} "
        res = run_cmd_with_progress(
            cmd, log,
            timeout_s=timeout_s,
            total_duration=seg_len,
            label=clip_label,
            proc_reg=self.proc_reg,
        )

        if res.rc != 0 or not out.exists() or out.stat().st_size < 1024:
            if res.timed_out:
                print(f"  ⚠️ Timeout clip {idx+1} rc=124 ({int(res.elapsed)}s/{timeout_s}s): {src.name}")
            else:
                print(f"  ⚠️ Falha clip {idx+1} rc={res.rc}: {src.name}")
            try:
                if out.exists():
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

        print(f"  ✅ Clip {idx+1}/{total_clips} OK [{cam_tag}] speed={speed:.4f}")
        return out

    # --------- CONCAT (FAST COPY + FALLBACK BLINDADO) ----------

    def _escape_concat_path(self, p: Path) -> str:
        s = p.resolve().as_posix()          # ABSOLUTO (fix do seu erro)
        s = s.replace("'", r"'\''")         # escape aspas simples
        return s

    def _write_concat_list(self, clips: List[Path], out_video: Path) -> Path:
        concat_list = out_video.with_suffix(".concat.txt")
        concat_list.parent.mkdir(parents=True, exist_ok=True)
        with concat_list.open("w", encoding="utf-8", errors="replace") as f:
            for p in clips:
                f.write(f"file '{self._escape_concat_path(p)}'\n")
        return concat_list

    def _concat_copy(self, clips: List[Path], out_video: Path, total_duration: float = 0) -> bool:
        if not clips:
            return False

        concat_list = self._write_concat_list(clips, out_video)
        log = self.logs_dir / f"concat_copy_{out_video.stem}.log"

        cmd = [
            "ffmpeg", "-y", "-hide_banner",
            "-f", "concat", "-safe", "0",
            "-i", str(concat_list),
            "-c", "copy",
            "-movflags", "+faststart",
            str(out_video),
        ]

        res = run_cmd_with_progress(
            cmd, log,
            timeout_s=self.final_timeout_s,
            total_duration=total_duration,
            label="Concat (copy) ",
            proc_reg=self.proc_reg,
        )

        try:
            concat_list.unlink(missing_ok=True)
        except Exception:
            pass

        return res.rc == 0 and out_video.exists() and out_video.stat().st_size > 1024

    def _concat_reencode(self, clips: List[Path], out_video: Path, target_w: int, target_h: int, total_duration: float = 0) -> bool:
        if not clips:
            return False

        concat_list = self._write_concat_list(clips, out_video)
        log = self.logs_dir / f"concat_reencode_{out_video.stem}.log"

        vf = f"scale={target_w}:{target_h}:flags=lanczos,fps={ENGINE_FPS},setsar=1,format=yuv420p"

        cmd = [
            "ffmpeg", "-y", "-hide_banner",
            "-fflags", "+genpts",
            "-threads", str(self.ffmpeg_threads),
            "-f", "concat", "-safe", "0",
            "-i", str(concat_list),
            "-vf", vf,
            "-movflags", "+faststart",
            "-video_track_timescale", "90000",
            "-c:v", "libx264",
            "-preset", self.final_preset,
            "-crf", str(self.final_crf),
            "-pix_fmt", "yuv420p",
            "-threads", str(self.ffmpeg_threads),
            "-c:a", "aac",
            "-b:a", "192k",
            str(out_video),
        ]

        res = run_cmd_with_progress(
            cmd, log,
            timeout_s=self.final_timeout_s,
            total_duration=total_duration,
            label="Concat (reencode) ",
            proc_reg=self.proc_reg,
        )

        try:
            concat_list.unlink(missing_ok=True)
        except Exception:
            pass

        return res.rc == 0 and out_video.exists() and out_video.stat().st_size > 1024

    def concat_video_only(self, clips: List[Path], out_video: Path, target_w: int, target_h: int, total_duration: float = 0) -> bool:
        if not clips:
            return False

        if self.concat_copy:
            if self._concat_copy(clips, out_video, total_duration=total_duration):
                return True
            print("⚠️ concat copy falhou; fazendo fallback para reencode (mais lento).")

        ok = self._concat_reencode(clips, out_video, target_w, target_h, total_duration=total_duration)
        if not ok:
            print("❌ Concat reencode falhou (veja logs/concat_reencode_*.log).")
        return ok

    # --------- THUMB ----------

    def generate_thumbnails(self, video_path: Path, base_stem: str) -> List[Path]:
        """Gera N thumbnails do vídeo em pontos diferentes, retorna lista de paths salvos."""
        dur = _get_duration(video_path)
        if dur <= 1.0:
            return []

        n = self.num_thumbs
        # Gera mais candidatas que o necessário para escolher as melhores
        num_candidates = max(n * 2, 6)
        positions = [dur * (i + 1) / (num_candidates + 1) for i in range(num_candidates)]

        candidates: List[Path] = []

        for i, t in enumerate(positions, 1):
            tmp = self.thumbs_dir / f"{base_stem}_cand{i}.jpg"
            log = self.logs_dir / f"thumb_{base_stem}_cand{i}.log"
            cmd = [
                "ffmpeg", "-y", "-hide_banner",
                "-ss", str(t),
                "-i", str(video_path),
                "-frames:v", "1",
                "-vf", "eq=contrast=1.10:saturation=1.10,unsharp=3:3:0.8:3:3:0.2",
                "-q:v", "2",
                str(tmp),
            ]
            res = run_cmd_capture(cmd, log, timeout_s=120, proc_reg=self.proc_reg)
            if res.rc == 0 and tmp.exists() and tmp.stat().st_size > 10_000:
                candidates.append(tmp)

        if not candidates:
            return []

        # Ordena por tamanho (maior = mais detalhes/qualidade) e pega as top N
        candidates.sort(key=lambda p: p.stat().st_size, reverse=True)
        selected = candidates[:n]
        to_remove = candidates[n:]

        saved: List[Path] = []
        for i, cand in enumerate(selected, 1):
            final_name = self.thumbs_dir / f"{base_stem}_thumb{i}.jpg"
            try:
                if final_name.exists():
                    final_name.unlink(missing_ok=True)
                shutil.move(str(cand), str(final_name))
                saved.append(final_name)
            except Exception:
                pass

        # Limpa candidatas não selecionadas
        for c in to_remove:
            try:
                if c.exists():
                    c.unlink(missing_ok=True)
            except Exception:
                pass

        return saved

    # --------- RUN ONE / BATCH ----------

    def run_one(self) -> Optional[Path]:
        videos = self.list_videos()
        if not videos:
            print("❌ Nenhum vídeo encontrado no input.")
            return None

        target_total = random.randint(self.cfg.dur_min, self.cfg.dur_max)

        if self.target_res:
            final_w, final_h = self.target_res
        else:
            base = self.get_video_info(videos[0])
            final_w, final_h = int(base["width"]), int(base["height"])
            if self.enable_upscale and self.upscale_quality != "none":
                if final_w < 1920:
                    final_w, final_h = 1920, 1080

        final_w = _safe_int_even(final_w, 2)
        final_h = _safe_int_even(final_h, 2)

        print(f"\n🎬 STUDIO ENGINE mode={self.mode}")
        print(f"🎯 Duração alvo: {target_total}s ({target_total/60:.1f}min)")
        print(f"📐 Saída: {final_w}x{final_h} @ {ENGINE_FPS}fps")
        print(f"🎛️ Intensidade efeitos: {self.cfg.effect_intensity:.2f}")
        gpu_tag = "GPU+CPU" if self.has_gpu else "CPU only"
        print(f"⚙️ Encoder: {self.encoder} | {gpu_tag} | Workers: {self.max_workers} | Concat copy: {'ON' if self.concat_copy else 'OFF'}")
        print(f"🔊 Áudio: original do vídeo (mantido)")

        clips = self.pick_clips(videos, target_total)
        if not clips:
            print("❌ Não foi possível selecionar clipes.")
            return None

        temp_dir = self.logs_dir / f"temp_{int(time.time())}"
        temp_dir.mkdir(parents=True, exist_ok=True)

        processed: List[Tuple[int, Path]] = []

        try:
            total_clips = len(clips)
            total_dur = sum(float(c.get("seg_len", 0)) for c in clips)
            print(f"\n🎞️ Processando {total_clips} clipes ({_format_time(total_dur)} total)...\n")

            try:
                for i, clip in enumerate(clips):
                    if self.stop_event.is_set():
                        break
                    try:
                        p = self.process_clip(clip, i, temp_dir, final_w, final_h, total_clips=total_clips)
                        if p:
                            processed.append((i, p))
                    except Exception as e:
                        print(f"  ❌ Erro clip {i+1}: {e}")
            except KeyboardInterrupt:
                self.stop_event.set()
                print("\n🛑 Interrompido (Ctrl+C). Finalizando processos FFmpeg...")
                self.proc_reg.kill_all()
                raise

            processed.sort(key=lambda x: x[0])
            clip_paths = [p for _, p in processed]

            if len(clip_paths) < 2:
                print("❌ Poucos clipes processados para concatenar.")
                return None

            ts = int(time.time())
            seed = hashlib.md5(f"{ts}{random.random()}".encode()).hexdigest()[:8]

            out_video_final = self.output_dir / f"{self.mode}_{ts}_{seed}.mp4"

            # Calcula duração total dos clipes processados para barra de progresso do concat
            concat_dur = sum(_get_duration(p) for p in clip_paths)
            print(f"\n🧩 Concatenando {len(clip_paths)} clipes ({_format_time(concat_dur)})...")
            if not self.concat_video_only(clip_paths, out_video_final, final_w, final_h, total_duration=concat_dur):
                print("❌ Concat falhou.")
                return None
            print(f"✅ Vídeo final: {out_video_final.name}")

            if self.make_thumbs:
                thumbs = self.generate_thumbnails(out_video_final, out_video_final.stem)
                if thumbs:
                    print(f"🖼️ {len(thumbs)} thumbnail(s) gerada(s):")
                    for th in thumbs:
                        print(f"   - {th.name}")
                else:
                    print("⚠️ Não consegui gerar thumbnails.")

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

            size_mb = out_video_final.stat().st_size / (1024 * 1024)
            print(f"\n✨ FINAL: {out_video_final.name} ({size_mb:.1f} MB)")
            return out_video_final

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def run_batch(self, n: int) -> List[Path]:
        outs: List[Path] = []
        for i in range(n):
            print(f"\n{'='*70}\n🚀 JOB {i+1}/{n}\n{'='*70}")
            try:
                out = self.run_one()
            except KeyboardInterrupt:
                print("🛑 Batch interrompido.")
                break
            if out:
                outs.append(out)
            if i < n - 1:
                time.sleep(random.uniform(2, 5))
        return outs


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Studio Engine - geração automática de vídeos (acervo -> novos uploads)")
    p.add_argument("--mode", choices=["teaser", "compilado", "premium"], required=True)

    p.add_argument("--input-dir", required=True)
    p.add_argument("--output-dir", default="output")
    p.add_argument("--logs-dir", default="logs")
    p.add_argument("--thumbs-dir", default="thumbnails")
    p.add_argument("--processed-dir", default="processed")
    p.add_argument("--failed-dir", default="failed")

    p.add_argument("--workers", type=int, default=0,
                   help="Workers paralelos (0=auto: detecta baseado no hardware)")
    p.add_argument("--ffmpeg-threads", type=int, default=0,
                   help="Threads FFmpeg por processo (0=auto: usa todos os cores)")
    p.add_argument("--num-videos", type=int, default=1)

    p.add_argument("--clip-timeout", type=int, default=900, help="Timeout mínimo (piso) por clip (s)")
    p.add_argument("--clip-timeout-mult", type=float, default=1.0, help="Multiplicador extra do timeout dinâmico")
    p.add_argument("--final-timeout", type=int, default=2400)

    p.add_argument("--final-crf", type=int, default=18)
    p.add_argument("--final-preset", default="medium")

    p.add_argument("--concat-copy", action="store_true", help="Tenta concat demuxer com -c copy (muito mais rápido)")

    p.add_argument("--encoder", choices=["auto", "x264", "nvenc"], default="auto",
                   help="Encoder dos clips (auto=detecta GPU, x264 ou nvenc).")
    p.add_argument("--nvenc-preset", default="p5", help="Preset NVENC (p1..p7)")
    p.add_argument("--nvenc-cq", type=int, default=19, help="CQ NVENC (CRF-like)")
    p.add_argument("--nvenc-tune", default="hq", help="Tune NVENC (ex: hq, ll, ull...)")

    p.add_argument("--enable-upscale", action="store_true", help="Permite upscale automático (ou target-res)")
    p.add_argument("--upscale", choices=["none", "low", "medium", "high"], default="high")
    p.add_argument("--target-res", nargs=2, type=int, metavar=("W", "H"))

    p.add_argument("--enhance-color", action="store_true")
    p.add_argument("--denoise", action="store_true")
    p.add_argument("--stabilize", action="store_true")

    p.add_argument("--thumbnails", action="store_true")
    p.add_argument("--num-thumbs", type=int, default=3,
                   help="Número de thumbnails por vídeo (1-10, default=3)")

    return p


def main():
    parser = build_parser()
    args = parser.parse_args()

    engine = StudioEngine(args)
    outs = engine.run_batch(int(args.num_videos))

    print(f"\n{'='*70}")
    print(f"✅ Concluído. Gerados: {len(outs)}")
    for i, o in enumerate(outs, 1):
        mb = o.stat().st_size / (1024 * 1024)
        print(f"  {i}. {o.name} ({mb:.1f} MB)")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()