import subprocess
import json
from pathlib import Path

import imageio_ffmpeg


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


def trim(input_path: str, output_path: str, start: float, end: float):
    """Corta o trecho entre start e end (segundos), recodificando para corte preciso."""
    duration = max(0.0, end - start)
    _run([
        "-ss", str(start),
        "-i", input_path,
        "-t", str(duration),
        "-c:v", "libx264",
        "-preset", "fast",
        "-c:a", "aac",
        output_path,
    ])


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


def adjust(input_path: str, output_path: str, brightness: float = 0.0,
           contrast: float = 1.0, saturation: float = 1.0):
    """Ajusta brilho (-1 a 1), contraste (0 a 3) e saturação (0 a 3)."""
    _run([
        "-i", input_path,
        "-vf", f"eq=brightness={brightness}:contrast={contrast}:saturation={saturation}",
        "-c:v", "libx264",
        "-preset", "fast",
        "-c:a", "copy",
        output_path,
    ])


def thumbnail(input_path: str, output_path: str, at: float = 0.0):
    """Extrai um frame do vídeo como imagem JPEG."""
    _run([
        "-ss", str(at),
        "-i", input_path,
        "-frames:v", "1",
        "-q:v", "2",
        output_path,
    ])
