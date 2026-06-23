import subprocess
import json
from pathlib import Path

import imageio_ffmpeg

FONTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"


def _ffmpeg_bin() -> str:
    return imageio_ffmpeg.get_ffmpeg_exe()


def _run(args: list[str]):
    """Executa o ffmpeg e levanta erro com a saída em caso de falha."""
    cmd = [_ffmpeg_bin(), "-y", *args]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr[-2000:] or "Falha no ffmpeg")


def probe_duration(path: str) -> float:
    """Retorna a duração do vídeo em segundos usando o ffmpeg."""
    cmd = [_ffmpeg_bin(), "-i", path]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    out = proc.stderr
    for line in out.splitlines():
        if "Duration:" in line:
            ts = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = ts.split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
    return 0.0


def process(input_path: str, output_path: str, start: float = 0.0, end: float = 0.0,
            brightness: float = 0.0, contrast: float = 1.0, saturation: float = 1.0):
    """Aplica corte + ajuste de iluminação num único passe de codificação.

    start/end em segundos (end=0 significa até o fim do vídeo).
    """
    args = []
    if start > 0:
        args += ["-ss", str(start)]
    args += ["-i", input_path]
    if end > 0:
        args += ["-t", str(max(0.0, end - start))]

    if brightness != 0.0 or contrast != 1.0 or saturation != 1.0:
        args += ["-vf", f"eq=brightness={brightness}:contrast={contrast}:saturation={saturation}"]

    args += ["-c:v", "libx264", "-preset", "fast", "-c:a", "aac", output_path]
    _run(args)


def join(input_paths: list[str], output_path: str):
    """Junta múltiplos vídeos em sequência, normalizando para um formato comum."""
    work_dir = Path(output_path).parent
    normalized = []
    for i, src in enumerate(input_paths):
        norm = str(work_dir / f"_norm_{i}_{Path(output_path).stem}.mp4")
        _run([
            "-i", src,
            "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,"
                   "pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1",
            "-r", "30",
            "-c:v", "libx264",
            "-preset", "fast",
            "-c:a", "aac",
            "-ar", "44100",
            norm,
        ])
        normalized.append(norm)

    list_file = work_dir / f"_concat_{Path(output_path).stem}.txt"
    list_file.write_text("".join(f"file '{p}'\n" for p in normalized))

    try:
        _run([
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_file),
            "-c", "copy",
            output_path,
        ])
    finally:
        list_file.unlink(missing_ok=True)
        for p in normalized:
            Path(p).unlink(missing_ok=True)


def thumbnail(input_path: str, output_path: str, at: float = 0.0):
    """Extrai um frame do vídeo como imagem JPEG."""
    _run([
        "-ss", str(at),
        "-i", input_path,
        "-frames:v", "1",
        "-q:v", "2",
        output_path,
    ])


def extract_audio(input_path: str, output_path: str):
    """Extrai a faixa de áudio em MP3 (para transcrição)."""
    _run([
        "-i", input_path,
        "-vn",
        "-ar", "16000",
        "-ac", "1",
        "-b:a", "64k",
        output_path,
    ])


# ---------- Cortes verticais com legenda (estilo TikTok/Reels) ----------

def _ass_time(t: float) -> str:
    if t < 0:
        t = 0.0
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    cs = int(round((s - int(s)) * 100))
    return f"{h}:{m:02d}:{int(s):02d}.{cs:02d}"


def _ass_escape(text: str) -> str:
    return text.replace("\n", " ").replace("{", "(").replace("}", ")").strip().upper()


def build_ass(segments: list[dict], clip_start: float, clip_end: float, output_path: str):
    """Gera um arquivo .ass com legenda estilizada para o trecho do corte."""
    dur = clip_end - clip_start
    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        "PlayResX: 1080\n"
        "PlayResY: 1920\n"
        "WrapStyle: 0\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Viral,DejaVu Sans,70,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,"
        "-1,0,0,0,100,100,0,0,1,5,2,2,60,60,260,1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    lines = []
    for s in segments:
        if s["end"] <= clip_start or s["start"] >= clip_end:
            continue
        st = max(0.0, s["start"] - clip_start)
        en = min(dur, s["end"] - clip_start)
        if en <= st:
            continue
        text = _ass_escape(s["text"])
        if not text:
            continue
        lines.append(f"Dialogue: 0,{_ass_time(st)},{_ass_time(en)},Viral,,0,0,0,,{text}")

    Path(output_path).write_text(header + "\n".join(lines) + "\n", encoding="utf-8")


def render_clip(input_path: str, output_path: str, start: float, end: float,
                ass_path: str, banner_path: str | None = None):
    """Renderiza um corte vertical 9:16 com fundo desfocado, legenda e banner opcional."""
    dur = max(0.0, end - start)
    args = ["-ss", str(start), "-i", input_path]

    banner_idx = None
    if banner_path:
        args += ["-loop", "1", "-i", banner_path]
        banner_idx = 1

    sub = f"subtitles=f='{ass_path}':fontsdir='{FONTS_DIR}'"
    fc = (
        "[0:v]split=2[bg][fg];"
        "[bg]scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,boxblur=20:5[bg];"
        "[fg]scale=1080:1920:force_original_aspect_ratio=decrease[fg];"
        "[bg][fg]overlay=(W-w)/2:(H-h)/2[base]"
    )
    last = "base"
    if banner_idx is not None:
        fc += f";[{banner_idx}:v]scale=1080:-1[ban];[base][ban]overlay=(W-w)/2:0[bn]"
        last = "bn"
    fc += f";[{last}]{sub}[outv]"

    args += [
        "-t", str(dur),
        "-filter_complex", fc,
        "-map", "[outv]", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "fast", "-c:a", "aac",
        "-shortest", output_path,
    ]
    _run(args)
