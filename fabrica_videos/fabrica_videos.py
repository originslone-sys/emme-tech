import argparse
import random
import subprocess
import sys
import textwrap
import time
import hashlib
from pathlib import Path
from typing import Optional, List

import requests

DEFAULT_API_URL = "https://emmetech.digital/api/receber_video.php"
DEFAULT_API_KEY  = "a4aLYTawyy4HEUGQIoHCSjDOtSrxh4SA"

# Fontes: Windows, Linux e macOS (primeira encontrada é usada)
FONT_PATHS = [
    # Windows
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\Arial.ttf",
    r"C:\Windows\Fonts\calibri.ttf",
    r"C:\Windows\Fonts\Calibri.ttf",
    r"C:\Windows\Fonts\verdana.ttf",
    r"C:\Windows\Fonts\Verdana.ttf",
    r"C:\Windows\Fonts\tahoma.ttf",
    r"C:\Windows\Fonts\Tahoma.ttf",
    # Linux (Debian/Ubuntu/Arch)
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    # macOS
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

# Posições possíveis para o texto (variação visual)
TEXT_POSITIONS = [
    "x=(w-text_w)/2:y=h-(h/4)",        # baixo centro
    "x=(w-text_w)/2:y=(h/10)",          # topo centro
    "x=20:y=h-(h/4)",                   # baixo esquerda
    "x=(w-text_w)-20:y=h-(h/4)",        # baixo direita
    "x=(w-text_w)/2:y=(h/2)-(text_h/2)",# meio centro
]

# Cores de texto (variação visual)
TEXT_COLORS = ["white", "yellow", "white@0.92", "cyan@0.90"]

# Filtros EQ de áudio sutis (mudam assinatura espectral sem afetar percepção)
AUDIO_EQ_OPTIONS: List[List[str]] = [
    [],                                                              # sem EQ
    ["equalizer=f=80:width_type=o:width=2:g=-2.0"],                 # roll-off grave
    ["equalizer=f=10000:width_type=o:width=2:g=1.5"],               # leve boost agudo
    ["equalizer=f=3500:width_type=o:width=2:g=1.2"],                # boost médio-alto
    ["equalizer=f=200:width_type=o:width=2:g=1.5"],                 # boost grave leve
    ["equalizer=f=80:width_type=o:width=2:g=-1.5",
     "equalizer=f=8000:width_type=o:width=2:g=1.0"],                # dual-band
]

VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi", ".flv", ".wmv"}


def _ff_path(p: Path) -> str:
    r"""
    FFmpeg aceita melhor paths com / do que com \.
    E dentro de filtros (drawtext etc), ':' precisa ser escapado.
    Ex: D:/pasta/arq.txt -> D\:/pasta/arq.txt
    """
    s = str(p.resolve()).replace("\\", "/")
    s = s.replace(":", r"\:")
    return s


def _find_font() -> Optional[Path]:
    """Retorna o Path da primeira fonte encontrada (multiplataforma), ou None."""
    for fp in FONT_PATHS:
        p = Path(fp)
        if p.exists():
            return p
    return None


def calcular_hash_arquivo(arquivo: Path, algoritmo: str = "md5") -> str:
    """Calcula o hash de um arquivo para verificação de integridade."""
    hash_obj = hashlib.new(algoritmo)
    with arquivo.open("rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()


def tem_audio(arquivo_video: Path) -> bool:
    comando = [
        "ffprobe", "-v", "error", "-select_streams", "a",
        "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(arquivo_video)
    ]
    try:
        resultado = subprocess.check_output(comando, text=True).strip()
        return "audio" in resultado.lower()
    except Exception:
        return False


def obter_info_video(arquivo_video: Path) -> dict:
    """Obtém informações básicas do vídeo (resolução, fps, codec)."""
    info: dict = {}

    cmd_res = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height", "-of", "csv=p=0", str(arquivo_video)
    ]
    try:
        res = subprocess.check_output(cmd_res, text=True).strip().split(",")
        if len(res) == 2:
            info["width"] = int(res[0])
            info["height"] = int(res[1])
    except Exception:
        info["width"] = 1920
        info["height"] = 1080

    cmd_fps = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=r_frame_rate", "-of", "default=noprint_wrappers=1:nokey=1", str(arquivo_video)
    ]
    try:
        fps_str = subprocess.check_output(cmd_fps, text=True).strip()
        if "/" in fps_str:
            num, den = map(int, fps_str.split("/"))
            info["fps"] = num / den if den else 30.0
        else:
            info["fps"] = float(fps_str) if fps_str else 30.0
    except Exception:
        info["fps"] = 30.0

    cmd_codec = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=codec_name", "-of", "default=noprint_wrappers=1:nokey=1", str(arquivo_video)
    ]
    try:
        info["codec"] = subprocess.check_output(cmd_codec, text=True).strip()
    except Exception:
        info["codec"] = "h264"

    return info


def _build_video_filters(width: int, height: int, ts: int,
                         logs_dir: Path, input_stem: str,
                         font_path_obj: Optional[Path],
                         texto_quebrado: str) -> tuple[str, Optional[Path], dict]:
    """
    Monta a cadeia de filtros de vídeo FFmpeg.
    Retorna: (filtro_video_str, arquivo_texto_temp, info_transformacoes)
    """
    info_tx: dict = {}

    # ------------------------------------------------------------------ #
    # 1. CROP: 5-30px em cada lado (~0.3-1.5% para 1920px)
    #    Faixa maior que v1 (era 2-12px) -> mais variação de fingerprint
    # ------------------------------------------------------------------ #
    crop_px_x = random.randint(5, 30)
    crop_px_y = random.randint(5, 30)
    crop_w_expr = f"iw-{crop_px_x * 2}"
    crop_h_expr = f"ih-{crop_px_y * 2}"

    # ------------------------------------------------------------------ #
    # 2. SCALE: ±1.5% (era ±1%)
    # ------------------------------------------------------------------ #
    scale_factor = round(random.uniform(0.985, 1.015), 5)

    # ------------------------------------------------------------------ #
    # 3. FLIP HORIZONTAL: 50% de chance
    #    Uma das transformações mais eficazes contra perceptual hash.
    # ------------------------------------------------------------------ #
    use_hflip = random.random() < 0.5

    # ------------------------------------------------------------------ #
    # 4. ROTATE: ±1.5° (era ±0.5°)
    # ------------------------------------------------------------------ #
    rotate_angle = round(random.uniform(-1.5, 1.5), 4)

    # ------------------------------------------------------------------ #
    # 5. SPEED: ±5% (era ±3%)
    #    Altera fingerprint temporal e força resync do áudio.
    # ------------------------------------------------------------------ #
    speed_factor = round(random.uniform(0.95, 1.05), 5)

    # ------------------------------------------------------------------ #
    # 6. COLOR EQ: brightness e contrast (saturation gerida pelo hue)
    # ------------------------------------------------------------------ #
    brightness = round(random.uniform(-0.015, 0.015), 5)
    contrast   = round(random.uniform(0.993, 1.007), 5)

    # ------------------------------------------------------------------ #
    # 7. HUE ROTATION: ±15° + ajuste de saturação ±5%
    #    Muda completamente a assinatura de cor frame-a-frame.
    #    Imperceptível ao espectador mas derrota comparação RGB/HSV.
    # ------------------------------------------------------------------ #
    hue_shift = round(random.uniform(-15.0, 15.0), 3)
    hue_sat   = round(random.uniform(0.96, 1.04), 4)

    # ------------------------------------------------------------------ #
    # 8. NOISE/GRAIN: 1-6 (era 1-3)
    # ------------------------------------------------------------------ #
    grain_strength = random.randint(1, 6)

    # ------------------------------------------------------------------ #
    # 9. PADDING: 8-40px em cada lado (era 4-16px)
    # ------------------------------------------------------------------ #
    pad_px = random.randint(4, 20) * 2   # sempre par

    info_tx = {
        "crop": f"{crop_px_x}x{crop_px_y}px",
        "scale": f"{scale_factor:.4f}",
        "hflip": use_hflip,
        "rotate": f"{rotate_angle:.2f}°",
        "speed": f"{speed_factor:.4f}",
        "brightness": brightness,
        "hue_shift": f"{hue_shift:.1f}°",
        "hue_sat": hue_sat,
        "grain": grain_strength,
        "pad": f"{pad_px}px",
    }

    # ------------------------------------------------------------------ #
    # DRAWTEXT: multiplataforma, posição e cor aleatórias
    # ------------------------------------------------------------------ #
    arquivo_texto_temp: Optional[Path] = None
    drawtext_filter = ""

    if font_path_obj is not None:
        arquivo_texto_temp = logs_dir / f"texto_temp_{input_stem}_{ts}.txt"
        arquivo_texto_temp.write_text(texto_quebrado, encoding="utf-8")

        font_path  = _ff_path(font_path_obj)
        fontsize   = max(18, int(height / 38))
        box_border = max(4, int(fontsize / 5))
        font_color = random.choice(TEXT_COLORS)
        text_pos   = random.choice(TEXT_POSITIONS)

        drawtext_filter = (
            f"drawtext="
            f"fontfile='{font_path}':"
            f"textfile='{_ff_path(arquivo_texto_temp)}':"
            f"fontcolor={font_color}:fontsize={fontsize}:"
            f"box=1:boxcolor=black@0.5:boxborderw={box_border}:"
            f"line_spacing={int(fontsize / 4)}:"
            f"{text_pos}"
        )
        info_tx["font"] = font_path_obj.name
        info_tx["text_color"] = font_color
    else:
        info_tx["font"] = "N/A (desativado)"

    # ------------------------------------------------------------------ #
    # MONTA CADEIA DE FILTROS (lista -> evita vírgula dupla)
    # ------------------------------------------------------------------ #
    filters: List[str] = []

    filters.append(f"crop={crop_w_expr}:{crop_h_expr}:{crop_px_x}:{crop_px_y}")
    filters.append(
        f"scale=trunc(iw*{scale_factor}/2)*2:trunc(ih*{scale_factor}/2)*2:flags=lanczos"
    )
    if use_hflip:
        filters.append("hflip")
    filters.append(f"rotate={rotate_angle}*PI/180:fillcolor=black@1")
    filters.append(f"setpts={speed_factor}*PTS")
    filters.append(f"eq=brightness={brightness}:contrast={contrast}")
    filters.append(f"hue=h={hue_shift}:s={hue_sat}")
    filters.append(f"noise=alls={grain_strength}:allf=t+u")
    filters.append(
        f"pad=iw+{pad_px * 2}:ih+{pad_px * 2}:{pad_px}:{pad_px}:color=black"
    )
    if drawtext_filter:
        filters.append(drawtext_filter)

    filtro_video = ",".join(filters)
    return filtro_video, arquivo_texto_temp, info_tx


def _build_audio_af(speed_factor: float, audio_pitch: float,
                    audio_eq: List[str], base_vol: float = 1.0) -> str:
    """
    Monta filtro de áudio:
      - EQ espectral (opcional, muda assinatura ACR)
      - atempo (resync temporal com speed do vídeo)
      - asetrate + aresample (pitch shift real sem mudar velocidade)
      - volume
    """
    audio_sync = round(1.0 / speed_factor, 6)
    parts: List[str] = []

    parts.extend(audio_eq)
    parts.append(f"atempo={audio_sync}")
    # Pitch shift: asetrate muda taxa de amostragem (altera pitch),
    # aresample restaura para 44100Hz sem alterar velocidade.
    parts.append(f"asetrate=44100*{audio_pitch}")
    parts.append("aresample=44100")
    if base_vol != 1.0:
        parts.append(f"volume={base_vol}")

    return ",".join(parts)


def processar_video(input_file: Path, output_file: Path, logs_dir: Path, pasta_mp3: Path) -> bool:
    logs_dir.mkdir(parents=True, exist_ok=True)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    if not input_file.exists():
        print(f"[ERRO] Input não existe: {input_file}")
        return False

    hash_original = calcular_hash_arquivo(input_file)[:16]
    texto_escolhido = random.choice(FRASES_MOTIVACIONAIS)
    video_tem_audio = tem_audio(input_file)
    info_video = obter_info_video(input_file)
    width, height = info_video.get("width", 1920), info_video.get("height", 1080)
    fps = float(info_video.get("fps", 30.0))

    chars_por_linha = max(20, int(width / 40))
    texto_quebrado = textwrap.fill(texto_escolhido, width=chars_por_linha)

    ts = int(time.time() * 1000)

    print(f"\n[{input_file.name}] Iniciando processamento...")
    print(f"-> Hash original (ref): {hash_original}")
    print(f"-> Resolução: {width}x{height} | FPS: {fps:.2f}")
    print(f"-> Áudio detectado: {'Sim' if video_tem_audio else 'Não'}")

    font_path_obj = _find_font()
    if font_path_obj is None:
        print("[AVISO] Nenhuma fonte encontrada. Overlay de texto desativado.")

    # Monta cadeia de filtros de vídeo
    filtro_video, arquivo_texto_temp, info_tx = _build_video_filters(
        width, height, ts, logs_dir, input_file.stem, font_path_obj, texto_quebrado
    )

    # Parâmetros de áudio
    speed_factor = float(filtro_video.split("setpts=")[1].split("*PTS")[0])
    audio_pitch  = round(random.uniform(0.97, 1.03), 5)
    audio_eq     = random.choice(AUDIO_EQ_OPTIONS)

    print(f"-> Flip H: {'Sim' if info_tx['hflip'] else 'Não'} | "
          f"Hue: {info_tx['hue_shift']} | "
          f"Rot: {info_tx['rotate']} | "
          f"Speed: {info_tx['speed']} | "
          f"Pitch: {audio_pitch:.4f}")
    print(f"-> Grain: {info_tx['grain']} | Pad: {info_tx['pad']} | "
          f"EQ áudio: {'Sim' if audio_eq else 'Não'}")
    print(f"-> Fonte: {info_tx.get('font', 'N/A')} | "
          f"Cor texto: {info_tx.get('text_color', 'N/A')}")

    # Música de fundo
    musica_escolhida: Optional[Path] = None
    if pasta_mp3.exists() and pasta_mp3.is_dir():
        lista_mp3 = [m for m in pasta_mp3.iterdir() if m.suffix.lower() == ".mp3" and m.is_file()]
        if lista_mp3:
            musica_escolhida = random.choice(lista_mp3)

    # ------------------------------------------------------------------ #
    # MONTA COMANDO FFMPEG
    # ------------------------------------------------------------------ #
    comando: List[str] = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
        "-i", str(input_file)
    ]

    if musica_escolhida:
        print(f"-> Música: '{musica_escolhida.name}'")
        comando.extend(["-i", str(musica_escolhida)])

        bg_vol = round(random.uniform(0.20, 0.45), 2)

        if video_tem_audio:
            orig_af = _build_audio_af(speed_factor, audio_pitch, audio_eq)
            filter_complex = (
                f"[0:v]{filtro_video}[vout];"
                f"[0:a]{orig_af}[orig_a];"
                f"[1:a]volume={bg_vol}[bg_a];"
                f"[orig_a][bg_a]amix=inputs=2:duration=first:weights=1 {bg_vol}[aout]"
            )
            comando.extend([
                "-filter_complex", filter_complex,
                "-map", "[vout]", "-map", "[aout]"
            ])
        else:
            filter_complex = (
                f"[0:v]{filtro_video}[vout];"
                f"[1:a]volume={bg_vol},atempo=1.0[aout]"
            )
            comando.extend([
                "-filter_complex", filter_complex,
                "-map", "[vout]", "-map", "[aout]",
                "-shortest"
            ])

    else:
        print("-> Sem música. Processando apenas vídeo e áudio original...")
        comando.extend(["-vf", filtro_video])
        if video_tem_audio:
            orig_af = _build_audio_af(speed_factor, audio_pitch, audio_eq)
            comando.extend(["-af", orig_af])

    # ------------------------------------------------------------------ #
    # PARÂMETROS DE ENCODING
    # ------------------------------------------------------------------ #
    video_bitrate = random.choice(["1500k", "1800k", "2000k", "2200k", "2500k"])
    br      = int(video_bitrate[:-1])
    maxrate = int(br * 1.2)
    bufsize = int(br * 2.0)
    crf     = random.randint(20, 26)

    comando.extend([
        "-c:v", "libx264",
        "-preset", random.choice(["medium", "slow"]),
        "-crf", str(crf),
        "-b:v", video_bitrate,
        "-maxrate", f"{maxrate}k",
        "-bufsize", f"{bufsize}k",
        "-pix_fmt", "yuv420p",
    ])

    if musica_escolhida or video_tem_audio:
        comando.extend([
            "-c:a", "aac",
            "-b:a", random.choice(["128k", "160k", "192k"]),
            "-ar",  random.choice(["44100", "48000"]),
        ])

    # ------------------------------------------------------------------ #
    # METADATA: apaga TUDO do original, então injeta custom
    # -map_metadata -1 remove: câmera, GPS, datas, encoder original, etc.
    # ------------------------------------------------------------------ #
    comando.extend(["-map_metadata", "-1"])

    custom_metadata: List[str] = [
        f"title=Video_{ts}",
        f"artist=Creator_{random.randint(1000, 9999)}",
        f"comment=ID_{hash_original[:8]}_{ts}",
        "creation_time=1970-01-01T00:00:00.000000Z",
        f"encoder=FFmpeg Custom {random.randint(1000, 9999)}",
        "copyright=",
        "description=",
        "location=",
    ]
    for kv in custom_metadata:
        comando.extend(["-metadata", kv])

    comando.extend([
        "-movflags", "+faststart",
        str(output_file)
    ])

    # ------------------------------------------------------------------ #
    # EXECUÇÃO
    # ------------------------------------------------------------------ #
    ffmpeg_log = logs_dir / f"ffmpeg_{input_file.stem}.log"

    try:
        print("-> Executando FFmpeg...")
        with ffmpeg_log.open("w", encoding="utf-8", errors="ignore") as lf:
            lf.write("CMD:\n" + " ".join(comando) + "\n\n")
            proc = subprocess.run(comando, stdout=lf, stderr=lf, text=True)

        if proc.returncode != 0:
            log_content = ""
            try:
                log_content = ffmpeg_log.read_text(encoding="utf-8", errors="replace")
            except Exception:
                pass
            print(f"\n[ERRO] FFmpeg falhou (código {proc.returncode}). Log:\n{log_content}")
            return False

        if not output_file.exists():
            print(f"\n[ERRO] Output não foi criado: {output_file}")
            return False
        if output_file.stat().st_size < 200_000:
            print(f"\n[ERRO] Output muito pequeno ({output_file.stat().st_size} bytes): {output_file}")
            return False

        hash_novo = calcular_hash_arquivo(output_file)[:16]
        print(f"-> Hash novo (ref): {hash_novo}")
        print(f"[{input_file.name}] Sucesso! Salvo em: {output_file}")
        return True

    finally:
        if arquivo_texto_temp is not None:
            try:
                arquivo_texto_temp.unlink(missing_ok=True)
            except Exception:
                pass


def enviar_para_servidor(caminho_video: Path, vmos_id: str, legenda: str, api_url: str, api_key: str = DEFAULT_API_KEY) -> bool:
    dados_texto = {
        "api_key": api_key,
        "vmos_id": vmos_id,
        "legenda": legenda,
    }
    try:
        with caminho_video.open("rb") as arquivo_mp4:
            resp = requests.post(
                api_url,
                data=dados_texto,
                files={"arquivo_mp4": arquivo_mp4},
                timeout=180
            )
        if resp.status_code == 403:
            print("[ERRO] Upload rejeitado (403 Forbidden). Verifique a api_key.")
            return False
        try:
            resultado = resp.json()
        except Exception:
            print(f"[ERRO] Servidor retornou não-JSON: HTTP {resp.status_code} | {resp.text[:300]}")
            return False

        if resultado.get("sucesso"):
            print(f"Upload OK! Vídeo entrou na fila da conta '{vmos_id}'.")
            return True
        print(f"[ERRO] Servidor recusou upload: {resultado.get('mensagem')}")
        return False
    except Exception as ex:
        print(f"[ERRO] Falha ao enviar (upload): {ex}")
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
    ts = int(time.time() * 1000)
    alt = dst_dir / f"{src.stem}_{ts}{src.suffix}"
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
    payload = {
        "api_key": api_key,
        "nonce": nonce,
        "status": status,
        "result_ok": str(ok),
        "result_fail": str(fail),
        "message": message,
    }
    r = requests.post(ack_url, data=payload, timeout=30)
    r.raise_for_status()
    data = r.json()
    if not data.get("sucesso"):
        raise RuntimeError(f"Job ACK falhou: {data}")


def main():
    parser = argparse.ArgumentParser(description="Worker local: edita vídeos e faz upload (controlado pelo painel).")
    parser.add_argument("--input", required=True, help="Arquivo ou pasta (ex: input)")
    parser.add_argument("--output-dir", default="output")
    parser.add_argument("--music-dir", default="musicas_fundo")
    parser.add_argument("--logs-dir", default="logs")
    parser.add_argument("--api-url", default=DEFAULT_API_URL)
    parser.add_argument("--api-key", default=DEFAULT_API_KEY, help="Chave de API para autenticação")

    # modo job (painel)
    parser.add_argument("--job-url", default="", help="URL do edicao_job_get.php")
    parser.add_argument("--ack-url", default="", help="URL do edicao_job_ack.php")

    # modo manual (fallback)
    parser.add_argument("--upload", action="store_true")
    parser.add_argument("--vmos-id", default="")
    parser.add_argument("--legenda", default="")
    parser.add_argument("--on-success", choices=["move", "delete", "keep"], default="move")
    parser.add_argument("--processed-dir", default="processed")
    parser.add_argument("--failed-dir", default="failed")
    parser.add_argument("--clean-output-after-upload", action="store_true")
    parser.add_argument("--max-videos", type=int, default=0, help="0 = sem limite")

    args = parser.parse_args()

    input_path    = Path(args.input)
    output_dir    = Path(args.output_dir)
    music_dir     = Path(args.music_dir)
    logs_dir      = Path(args.logs_dir)
    processed_dir = Path(args.processed_dir)
    failed_dir    = Path(args.failed_dir)
    api_key       = args.api_key

    output_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    failed_dir.mkdir(parents=True, exist_ok=True)

    # JOB MODE
    if args.job_url and args.ack_url:
        job = job_get(args.job_url, api_key)
        status = (job.get("status") or "idle").lower()
        if status not in ("pending", "running"):
            print(f"Nenhum job pendente. status={status}")
            return

        nonce = job.get("nonce") or ""
        if not nonce:
            print("Job inválido: falta nonce.")
            return

        vmos_id    = (job.get("vmos_id") or "").strip()
        legenda    = (job.get("legenda") or "").strip()
        max_videos = int(job.get("max_videos") or 1)
        on_success = job.get("on_success") or "move"
        clean_output_after_upload = bool(job.get("clean_output_after_upload") or False)

        if not vmos_id:
            job_ack(args.ack_url, nonce, "error", 0, 0, "Job inválido: vmos_id vazio.", api_key)
            return

        job_ack(args.ack_url, nonce, "running", 0, 0, "Worker iniciou processamento.", api_key)

        args.upload = True
        args.vmos_id = vmos_id
        args.legenda = legenda
        args.max_videos = max_videos
        args.on_success = on_success
        args.clean_output_after_upload = clean_output_after_upload

    # PROCESSAMENTO
    inputs = listar_inputs(input_path)
    if not inputs:
        print(f"Nenhum vídeo encontrado em: {input_path}")
        if args.job_url and args.ack_url:
            try:
                job = job_get(args.job_url, api_key)
                nonce = job.get("nonce") or ""
                if nonce:
                    job_ack(args.ack_url, nonce, "error", 0, 0, "Nenhum vídeo encontrado no input.", api_key)
            except Exception:
                pass
        return

    if args.max_videos and args.max_videos > 0:
        inputs = inputs[: args.max_videos]

    if args.upload and (not str(args.vmos_id).strip()):
        print("[ERRO] Para usar upload, precisa --vmos-id (ou job mode).")
        return

    ok   = 0
    fail = 0
    last_nonce = ""

    if args.job_url and args.ack_url:
        try:
            job = job_get(args.job_url, api_key)
            last_nonce = job.get("nonce") or ""
        except Exception:
            last_nonce = ""

    for vid in inputs:
        ts  = int(time.time())
        out = output_dir / f"{vid.stem}_edit_{ts}{vid.suffix.lower()}"

        sucesso = processar_video(vid, out, logs_dir, music_dir)
        if not sucesso:
            fail += 1
            cleanup_input_on_fail(vid, failed_dir)
            continue

        if args.upload:
            up_ok = enviar_para_servidor(
                out,
                str(args.vmos_id).strip(),
                str(args.legenda or "").strip(),
                args.api_url,
                api_key,
            )
            if not up_ok:
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
        msg = "Concluído com sucesso." if fail == 0 else "Concluído com falhas (verifique failed/ logs)."
        job_ack(args.ack_url, last_nonce, final_status, ok, fail, msg, api_key)

    sys.exit(1 if fail > 0 else 0)


if __name__ == "__main__":
    main()
