import subprocess
import random
import os
import json
import tempfile
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw

FONTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"


def _ffmpeg_bin() -> str:
    return imageio_ffmpeg.get_ffmpeg_exe()


def _run(args: list[str]):
    """Executa o ffmpeg e levanta erro com a saída em caso de falha."""
    cmd = [_ffmpeg_bin(), "-y", *args]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr[-2000:] or "Falha no ffmpeg")


def _run_with_progress(args: list[str], total_duration: float, on_progress=None):
    """Executa o ffmpeg reportando progresso (0–99%) via callback on_progress(pct)."""
    cmd = [_ffmpeg_bin(), "-y", *args, "-progress", "pipe:1", "-nostats"]
    with tempfile.TemporaryFile(mode="w+") as errf:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=errf, text=True)
        for line in proc.stdout:
            line = line.strip()
            if line == "progress=end":
                break
            if line.startswith("out_time_us=") and total_duration > 0 and on_progress:
                try:
                    us = int(line.split("=")[1])
                    pct = min(99, int((us / 1_000_000) / total_duration * 100))
                    on_progress(pct)
                except ValueError:
                    pass
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.terminate()
            proc.wait()
        errf.seek(0)
        stderr = errf.read()
    if proc.returncode != 0:
        raise RuntimeError(stderr[-2000:] or "Falha no ffmpeg")


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


def banner_overlay_height(banner_path: str, video_width: int = 1080) -> int:
    """Altura que o banner terá ao ser escalado para a largura do vídeo."""
    try:
        with Image.open(banner_path) as im:
            w, h = im.size
        if w <= 0:
            return 0
        return round(video_width * h / w)
    except Exception:
        return 0


def build_ass(segments: list[dict], clip_start: float, clip_end: float, output_path: str,
              clip_title: str | None = None, sub_margin_v: int = 120):
    """Gera um arquivo .ass com legenda no rodapé e título fixo opcional no topo.

    sub_margin_v: distância da legenda até o rodapé (px) — sobe a legenda quando
    há um banner embaixo, para não sobrepor.
    """
    dur = clip_end - clip_start
    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        "PlayResX: 1080\n"
        "PlayResY: 1920\n"
        "WrapStyle: 1\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        # Alignment=2 = bottom-center; MarginV do rodapé
        f"Style: Sub,DejaVu Sans,48,&H00FFFFFF,&H000000FF,&H00000000,&H96000000,"
        f"-1,0,0,0,100,100,0,0,1,4,2,2,80,80,{sub_margin_v},1\n"
        # Alignment=8 = top-center; MarginV do topo
        "Style: Title,DejaVu Sans,48,&H00FFFFFF,&H000000FF,&H00000000,&HB4000000,"
        "-1,0,0,0,100,100,0,0,1,4,2,8,80,80,100,1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    lines = []
    # Título fixo no topo (dura o clipe inteiro)
    if clip_title and clip_title.strip():
        title_text = _ass_escape(clip_title)
        lines.append(f"Dialogue: 0,{_ass_time(0)},{_ass_time(dur)},Title,,0,0,0,,{title_text}")

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
        lines.append(f"Dialogue: 0,{_ass_time(st)},{_ass_time(en)},Sub,,0,0,0,,{text}")

    Path(output_path).write_text(header + "\n".join(lines) + "\n", encoding="utf-8")


def render_clip(input_path: str, output_path: str, start: float, end: float,
                ass_path: str, banner_path: str | None = None,
                channel_name: str | None = None):
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
        fc += f";[{banner_idx}:v]scale=1080:-1[ban];[base][ban]overlay=(W-w)/2:H-h[bn]"
        last = "bn"

    video_filters = sub
    if channel_name and channel_name.strip():
        video_filters += "," + _drawtext_watermark(channel_name, 1080, 1920)
    fc += f";[{last}]{video_filters}[outv]"

    args += [
        "-t", str(dur),
        "-filter_complex", fc,
        "-map", "[outv]", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "fast", "-c:a", "aac",
        "-shortest", output_path,
    ]
    _run(args)


# ---------- Vídeo viral gerado do zero (cenas + legenda + música) ----------

def _chunk_caption(text: str, max_chars: int = 32) -> list[str]:
    """Quebra a fala em pedaços curtos (algumas palavras) para legenda dinâmica."""
    words = text.split()
    chunks: list[str] = []
    cur = ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > max_chars:
            chunks.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        chunks.append(cur)
    return chunks or [text]


def build_viral_ass(scenes: list[dict], width: int, height: int, output_path: str):
    """Gera um .ass com a fala do narrador como legenda, sincronizada por cena.

    A narração de cada cena é quebrada em pedaços curtos distribuídos ao longo
    da duração da cena (estilo auto-legenda). Se não houver narração, usa o
    'text' curto da cena. scenes: lista de {text, narration, duration}.
    """
    fontsize = max(34, round(height / 20))
    outline = max(2, round(fontsize / 18))
    margin_h = round(width * 0.07)
    margin_v = round(height * 0.08)  # distância do rodapé
    max_chars = max(18, round(width / 34))
    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        f"PlayResX: {width}\n"
        f"PlayResY: {height}\n"
        "WrapStyle: 0\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Viral,DejaVu Sans,{fontsize},&H00FFFFFF,&H000000FF,&H00000000,&H96000000,"
        f"-1,0,0,0,100,100,0,0,1,{outline},2,2,{margin_h},{margin_h},{margin_v},1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    lines = []
    t = 0.0
    for sc in scenes:
        dur = float(sc.get("duration", 3))
        scene_start, scene_end = t, t + dur
        t = scene_end

        source = (sc.get("narration") or sc.get("text") or "").strip()
        if not source:
            continue

        chunks = _chunk_caption(source, max_chars)
        # distribui a duração da cena proporcional ao tamanho de cada pedaço
        weights = [max(1, len(c)) for c in chunks]
        total_w = sum(weights)
        ct = scene_start
        for chunk, w in zip(chunks, weights):
            seg = dur * (w / total_w)
            st, en = ct, min(scene_end, ct + seg)
            ct = en
            text = _ass_escape(chunk)
            if not text or en <= st:
                continue
            lines.append(
                f"Dialogue: 0,{_ass_time(st)},{_ass_time(en)},Viral,,0,0,0,,{{\\fad(120,120)}}{text}"
            )
    Path(output_path).write_text(header + "\n".join(lines) + "\n", encoding="utf-8")


def _drawtext_watermark(text: str, width: int, height: int) -> str:
    """Retorna o filtro drawtext para a marca d'água centralizada."""
    escaped = text.replace("\\", "\\\\").replace("'", "\\'").replace(":", "\\:").strip()
    fontfile = FONTS_DIR / "DejaVuSans-Bold.ttf"
    fontsize = max(28, round(height / 28))
    ff = f"fontfile='{fontfile}':" if fontfile.exists() else ""
    return (
        f"drawtext={ff}text='{escaped}':fontsize={fontsize}:"
        f"fontcolor=white@0.30:x=(w-text_w)/2:y=(h-text_h)/2:"
        f"shadowcolor=black@0.25:shadowx=2:shadowy=2"
    )


def render_viral(scene_paths: list[str | None], scenes: list[dict],
                 width: int, height: int, music_path: str | None,
                 output_path: str, on_progress=None,
                 narration_paths: list[str | None] | None = None,
                 channel_name: str | None = None):
    """Monta o vídeo viral: normaliza cada cena, concatena, queima legendas e
    mixa narração (volume cheio) + música (abafada). scene_paths[i]=None vira
    um fundo escuro; narration_paths[i]=None vira silêncio naquela cena."""
    work = Path(output_path).parent
    stem = Path(output_path).stem
    norm: list[str] = []
    narr_segs: list[str] = []
    total = sum(float(s.get("duration", 3)) for s in scenes)
    has_narr = bool(narration_paths and any(narration_paths))
    cleanup: list[str] = []
    try:
        for i, (src, sc) in enumerate(zip(scene_paths, scenes)):
            dur = float(sc.get("duration", 3))
            n = str(work / f"_vs_{i}_{stem}.mp4")
            if src:
                _run([
                    "-stream_loop", "-1", "-i", src,
                    "-t", f"{dur:.3f}",
                    "-vf", f"scale={width}:{height}:force_original_aspect_ratio=increase,"
                           f"crop={width}:{height},setsar=1,fps=30",
                    "-an", "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p", n,
                ])
            else:
                _run([
                    "-f", "lavfi",
                    "-i", f"color=c=0x0E0E12:s={width}x{height}:d={dur:.3f}:r=30",
                    "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p", n,
                ])
            norm.append(n)
            cleanup.append(n)

            if has_narr:
                seg = str(work / f"_na_{i}_{stem}.wav")
                na = narration_paths[i] if narration_paths else None
                if na:
                    # narração + silêncio até o fim da cena (alinha com o vídeo)
                    _run(["-i", na, "-af", "apad", "-t", f"{dur:.3f}",
                          "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le", seg])
                else:
                    _run(["-f", "lavfi",
                          "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
                          "-t", f"{dur:.3f}", "-c:a", "pcm_s16le", seg])
                narr_segs.append(seg)
                cleanup.append(seg)

        list_file = work / f"_vcat_{stem}.txt"
        list_file.write_text("".join(f"file '{p}'\n" for p in norm))
        cleanup.append(str(list_file))
        silent = str(work / f"_vsilent_{stem}.mp4")
        cleanup.append(silent)
        _run(["-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", silent])

        narr_wav = None
        if has_narr:
            nlist = work / f"_nacat_{stem}.txt"
            nlist.write_text("".join(f"file '{p}'\n" for p in narr_segs))
            cleanup.append(str(nlist))
            narr_wav = str(work / f"_narr_{stem}.wav")
            cleanup.append(narr_wav)
            _run(["-f", "concat", "-safe", "0", "-i", str(nlist), "-c", "copy", narr_wav])

        ass = str(work / f"_v_{stem}.ass")
        cleanup.append(ass)
        build_viral_ass(scenes, width, height, ass)

        sub = f"subtitles=f='{ass}':fontsdir='{FONTS_DIR}'"
        fade_st = max(0.0, total - 2)

        inputs = ["-i", silent]
        idx = 1
        narr_idx = music_idx = None
        if narr_wav:
            inputs += ["-i", narr_wav]
            narr_idx = idx
            idx += 1
        if music_path:
            inputs += ["-stream_loop", "-1", "-i", music_path]
            music_idx = idx
            idx += 1

        video_filters = sub
        if channel_name and channel_name.strip():
            video_filters += "," + _drawtext_watermark(channel_name, width, height)
        parts = [f"[0:v]{video_filters}[v]"]
        audio_label = None
        if narr_idx is not None and music_idx is not None:
            parts.append(f"[{narr_idx}:a]volume=1.0,aresample=44100[na]")
            parts.append(f"[{music_idx}:a]volume=0.12,"
                         f"afade=t=out:st={fade_st:.2f}:d=2,aresample=44100[ma]")
            parts.append("[na][ma]amix=inputs=2:duration=first:dropout_transition=0[a]")
            audio_label = "[a]"
        elif narr_idx is not None:
            parts.append(f"[{narr_idx}:a]volume=1.0[a]")
            audio_label = "[a]"
        elif music_idx is not None:
            parts.append(f"[{music_idx}:a]volume=0.28,afade=t=out:st={fade_st:.2f}:d=2[a]")
            audio_label = "[a]"

        args = [*inputs, "-filter_complex", ";".join(parts), "-map", "[v]"]
        if audio_label:
            args += ["-map", audio_label, "-c:a", "aac", "-b:a", "128k", "-shortest"]
        args += ["-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
                 "-movflags", "+faststart", output_path]
        _run_with_progress(args, total, on_progress)
    finally:
        for p in cleanup:
            Path(p).unlink(missing_ok=True)


# ---------- Originalizar (spin) para repostagem em outras redes ----------

def _make_logo(size: int, tmp_dir: str) -> str:
    logo_path = os.path.join(tmp_dir, f"logo_{random.randint(1000, 9999)}.png")
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([0, 0, size, size], fill=(255, 255, 255, 180))
    img.save(logo_path)
    return logo_path


def has_audio(path: str) -> bool:
    """Verifica se o arquivo tem faixa de áudio."""
    cmd = [_ffmpeg_bin(), "-i", path]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return "Audio:" in proc.stderr


def spin(input_path: str, output_path: str, on_progress=None):
    """Aplica transformações aleatórias leves para tornar o vídeo único nas plataformas.

    - Crop leve nas bordas (1–5%)
    - Espelhamento horizontal aleatório
    - Variação de velocidade ±3%
    - Ajuste sutil de brilho/contraste/saturação
    - Ruído granular 1–2% em cada frame
    - Mudança de framerate (ex: 30 → 29.97)
    - Logo micro no canto (altera hash binário)
    - Re-encode H.265 com CRF aleatório
    """
    tmp_dir = str(Path(input_path).parent)
    logo_size = random.randint(20, 50)
    logo_path = _make_logo(logo_size, tmp_dir)
    total_duration = probe_duration(input_path)
    audio_present = has_audio(input_path)

    try:
        crop_l = random.uniform(0.01, 0.05)
        crop_r = random.uniform(0.01, 0.05)
        crop_t = random.uniform(0.01, 0.05)
        crop_b = random.uniform(0.01, 0.05)
        # floor para dimensões pares — exigência do H.265/H.264 (yuv420p)
        crop = (
            f"crop=w=floor(iw*(1-{crop_l+crop_r:.4f})/2)*2:"
            f"h=floor(ih*(1-{crop_t+crop_b:.4f})/2)*2:"
            f"x=iw*{crop_l:.4f}:y=ih*{crop_t:.4f}"
        )

        hflip = ",hflip" if random.random() < 0.5 else ""
        speed = round(random.uniform(0.97, 1.03), 4)
        setpts = f"setpts={1/speed:.6f}*PTS"

        brightness = round(random.uniform(-0.05, 0.05), 3)
        contrast = round(random.uniform(0.95, 1.05), 3)
        saturation = round(random.uniform(0.95, 1.05), 3)
        eq = f"eq=brightness={brightness}:contrast={contrast}:saturation={saturation}"

        # Ruído granular 1–2%: strength 4–10 é imperceptível mas muda cada frame
        noise_strength = random.randint(4, 10)
        noise = f"noise=alls={noise_strength}:allf=t+u"

        # Framerate ligeiramente diferente do original
        fps_choices = [23.976, 24.0, 25.0, 29.97, 30.0]
        fps = random.choice(fps_choices)
        fps_filter = f"fps={fps}"

        logo_x = random.randint(10, 30)
        logo_y = random.randint(10, 30)
        crf = random.randint(23, 28)

        # filter_complex explícito: video pipeline → overlay logo
        fc = (
            f"[0:v]{crop}{hflip},{setpts},{eq},{noise},{fps_filter}[base];"
            f"[1:v]scale={logo_size}:{logo_size}[logo];"
            f"[base][logo]overlay=W-w-{logo_x}:H-h-{logo_y}[v]"
        )
        maps = ["-map", "[v]"]
        if audio_present:
            fc += f";[0:a]atempo={speed:.4f}[a]"
            maps += ["-map", "[a]"]

        args = [
            "-nostdin",
            "-i", input_path,
            "-loop", "1", "-i", logo_path,
            "-filter_complex", fc,
            *maps,
            "-c:v", "libx265",
            "-crf", str(crf),
            "-preset", "fast",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            "-shortest",
            output_path,
        ]
        _run_with_progress(args, total_duration, on_progress)
    finally:
        Path(logo_path).unlink(missing_ok=True)
