"""
Worker serverless RunPod — montagem de vídeo viral na GPU.

Input esperado:
{
  "input": {
    "scenes": [{"video_url": "...", "duration": 3.0, "text": "TEXTO NA TELA"}],
    "width": 1080,
    "height": 1920,
    "music_url": ""        # opcional, URL pública
  }
}

Output:
{ "video_base64": "<mp4 em base64>" }

Usa h264_nvenc (GPU) com fallback para libx264.
"""
import base64
import os
import subprocess
import tempfile
import urllib.request
from pathlib import Path

import runpod

FONTS_DIR = "/usr/share/fonts/truetype/dejavu"


def _download(url: str, dest: str):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=180) as r, open(dest, "wb") as f:
        while True:
            chunk = r.read(1 << 16)
            if not chunk:
                break
            f.write(chunk)


def _run(args: list[str]):
    cmd = ["ffmpeg", "-y", *args]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr[-2000:] or "Falha no ffmpeg")


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


def _build_ass(scenes, width, height, output_path):
    fontsize = max(40, round(height / 15))
    outline = max(2, round(fontsize / 18))
    margin = round(width * 0.07)
    header = (
        "[Script Info]\nScriptType: v4.00+\n"
        f"PlayResX: {width}\nPlayResY: {height}\nWrapStyle: 0\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Viral,DejaVu Sans,{fontsize},&H00FFFFFF,&H000000FF,&H00000000,&H96000000,"
        f"-1,0,0,0,100,100,0,0,1,{outline},3,5,{margin},{margin},0,1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    lines = []
    t = 0.0
    for sc in scenes:
        dur = float(sc.get("duration", 3))
        st, en = t, t + dur
        t = en
        text = _ass_escape(sc.get("text", ""))
        if not text:
            continue
        lines.append(
            f"Dialogue: 0,{_ass_time(st)},{_ass_time(en)},Viral,,0,0,0,,{{\\fad(150,150)}}{text}"
        )
    Path(output_path).write_text(header + "\n".join(lines) + "\n", encoding="utf-8")


def _render(scenes, scene_files, width, height, music_file, work, vcodec):
    norm = []
    total = sum(float(s.get("duration", 3)) for s in scenes)
    for i, (src, sc) in enumerate(zip(scene_files, scenes)):
        dur = float(sc.get("duration", 3))
        n = str(work / f"_vs_{i}.mp4")
        if src:
            _run([
                "-stream_loop", "-1", "-i", src, "-t", f"{dur:.3f}",
                "-vf", f"scale={width}:{height}:force_original_aspect_ratio=increase,"
                       f"crop={width}:{height},setsar=1,fps=30",
                "-an", "-c:v", vcodec, "-pix_fmt", "yuv420p", n,
            ])
        else:
            _run([
                "-f", "lavfi", "-i", f"color=c=0x0E0E12:s={width}x{height}:d={dur:.3f}:r=30",
                "-c:v", vcodec, "-pix_fmt", "yuv420p", n,
            ])
        norm.append(n)

    list_file = work / "_vcat.txt"
    list_file.write_text("".join(f"file '{p}'\n" for p in norm))
    silent = str(work / "_silent.mp4")
    _run(["-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", silent])

    ass = str(work / "_subs.ass")
    _build_ass(scenes, width, height, ass)

    out = str(work / "out.mp4")
    sub = f"subtitles=f='{ass}':fontsdir='{FONTS_DIR}'"
    args = ["-i", silent]
    if music_file:
        args += ["-stream_loop", "-1", "-i", music_file]
    args += ["-vf", sub]
    if music_file:
        fade_st = max(0.0, total - 2)
        args += ["-map", "0:v", "-map", "1:a",
                 "-af", f"volume=0.28,afade=t=out:st={fade_st:.2f}:d=2",
                 "-shortest", "-c:a", "aac", "-b:a", "128k"]
    else:
        args += ["-map", "0:v"]
    args += ["-c:v", vcodec, "-pix_fmt", "yuv420p", "-movflags", "+faststart", out]
    _run(args)
    return out


def handler(job):
    inp = job.get("input", {})
    scenes = inp.get("scenes", [])
    width = int(inp.get("width", 1080))
    height = int(inp.get("height", 1920))
    music_url = inp.get("music_url") or ""

    if not scenes:
        return {"error": "Nenhuma cena recebida"}

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)

        scene_files = []
        for i, sc in enumerate(scenes):
            url = sc.get("video_url") or ""
            if not url:
                scene_files.append(None)
                continue
            dest = str(work / f"src_{i}.mp4")
            try:
                _download(url, dest)
                scene_files.append(dest)
            except Exception:
                scene_files.append(None)

        music_file = None
        if music_url:
            try:
                music_file = str(work / "music.mp3")
                _download(music_url, music_file)
            except Exception:
                music_file = None

        # GPU primeiro; se o NVENC não estiver disponível, cai pro libx264
        try:
            out = _render(scenes, scene_files, width, height, music_file, work, "h264_nvenc")
        except Exception:
            out = _render(scenes, scene_files, width, height, music_file, work, "libx264")

        with open(out, "rb") as f:
            data = base64.b64encode(f.read()).decode("utf-8")

    return {"video_base64": data}


runpod.serverless.start({"handler": handler})
