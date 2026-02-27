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

VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi", ".flv", ".wmv"}


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
    print(f"-> Resolução: {width}x{height}, FPS: {fps:.2f}")
    print(f"-> Frase:\n{texto_quebrado}")
    print(f"-> Áudio original detectado? {'Sim' if video_tem_audio else 'Não (Vídeo Mudo)'}")

    # Localiza fonte disponível no Windows
    font_path_obj = _find_font()
    usar_drawtext = font_path_obj is not None

    arquivo_texto_temp: Optional[Path] = None

    if usar_drawtext:
        arquivo_texto_temp = logs_dir / f"texto_temp_{input_file.stem}_{ts}.txt"
        arquivo_texto_temp.write_text(texto_quebrado, encoding="utf-8")
        font_path = _ff_path(font_path_obj)
        fontsize = max(20, int(height / 35))
        box_border = max(5, int(fontsize / 4))
        drawtext_filter = (
            f"drawtext="
            f"fontfile='{font_path}':"
            f"textfile='{_ff_path(arquivo_texto_temp)}':"
            f"fontcolor=white:fontsize={fontsize}:"
            f"box=1:boxcolor=black@0.5:boxborderw={box_border}:"
            f"line_spacing={int(fontsize/4)}:"
            f"x=(w-text_w)/2:y=h-(h/4)"
        )
        print(f"-> Fonte: {font_path_obj.name}")
    else:
        drawtext_filter = ""
        print("[AVISO] Nenhuma fonte Windows encontrada. Overlay de texto desativado.")

    crop_px_x = random.randint(2, 12)
    crop_px_y = random.randint(2, 12)
    crop_w_expr = f"iw-{crop_px_x * 2}"
    crop_h_expr = f"ih-{crop_px_y * 2}"

    scale_factor    = random.uniform(0.99, 1.01)
    rotate_angle    = random.uniform(-0.5, 0.5)
    grain_strength  = random.randint(1, 3)
    brightness      = random.uniform(-0.005, 0.005)
    contrast        = random.uniform(0.998, 1.002)
    saturation      = random.uniform(0.997, 1.003)
    speed_factor    = random.uniform(0.97, 1.03)
    pad_px          = random.randint(2, 8) * 2

    metadata_changes: List[str] = [
        f"title=Edited_{ts}",
        f"artist=Creator_{random.randint(1000, 9999)}",
        f"comment=Ref_{hash_original[:8]}_{ts}",
        "creation_time=1970-01-01T00:00:00.000000Z",
    ]

    filtro_base = (
        f"crop={crop_w_expr}:{crop_h_expr}:{crop_px_x}:{crop_px_y},"
        f"scale=trunc(iw*{scale_factor}/2)*2:trunc(ih*{scale_factor}/2)*2:flags=lanczos,"
        f"rotate={rotate_angle}*PI/180:fillcolor=black@1,"
        f"setpts={speed_factor}*PTS,"
        f"eq=brightness={brightness}:contrast={contrast}:saturation={saturation},"
        f"noise=alls={grain_strength}:allf=t+u,"
        f"pad=iw+{pad_px * 2}:ih+{pad_px * 2}:{pad_px}:{pad_px}:color=black"
    )
    filtro_video = filtro_base + ("," + drawtext_filter if usar_drawtext else "")

    musica_escolhida: Optional[Path] = None
    if pasta_mp3.exists() and pasta_mp3.is_dir():
        lista_mp3 = [m for m in pasta_mp3.iterdir() if m.suffix.lower() == ".mp3" and m.is_file()]
        if lista_mp3:
            musica_escolhida = random.choice(lista_mp3)

    comando: List[str] = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "warning", "-i", str(input_file)]

    if musica_escolhida:
        print(f"-> Música sorteada: '{musica_escolhida.name}'")
        comando.extend(["-i", str(musica_escolhida)])

        if video_tem_audio:
            audio_sync  = round(1.0 / speed_factor, 6)
            audio_pitch = random.uniform(0.999, 1.001)
            bg_vol = round(random.uniform(0.25, 0.40), 2)
            filter_complex = (
                f"[0:v]{filtro_video}[vout];"
                f"[0:a]atempo={audio_sync},asetrate=44100*{audio_pitch},volume=1.0[orig_a];"
                f"[1:a]volume={bg_vol}[bg_a];"
                f"[orig_a][bg_a]amix=inputs=2:duration=first:weights=1 {bg_vol}[aout]"
            )
            comando.extend(["-filter_complex", filter_complex, "-map", "[vout]", "-map", "[aout]"])
        else:
            bg_vol = round(random.uniform(0.25, 0.40), 2)
            filter_complex = f"[0:v]{filtro_video}[vout];[1:a]volume={bg_vol},atempo=1.0[aout]"
            comando.extend(["-filter_complex", filter_complex, "-map", "[vout]", "-map", "[aout]", "-shortest"])

        video_bitrate = random.choice(["1500k", "1800k", "2000k", "2200k", "2500k"])
        br = int(video_bitrate[:-1])
        maxrate = int(br * 1.2)
        bufsize = int(br * 2.0)

        comando.extend([
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", str(random.randint(21, 25)),
            "-b:v", video_bitrate,
            "-maxrate", f"{maxrate}k",
            "-bufsize", f"{bufsize}k",
            "-c:a", "aac",
            "-b:a", random.choice(["128k", "160k", "192k"]),
            "-ar", random.choice(["44100", "48000"]),
            "-pix_fmt", "yuv420p",
        ])
    else:
        print("-> Nenhuma música encontrada. Processando apenas vídeo e texto...")
        comando.extend(["-vf", filtro_video])
        if video_tem_audio:
            audio_sync = round(1.0 / speed_factor, 6)
            comando.extend(["-af", f"atempo={audio_sync}"])
            comando.extend(["-c:a", "aac", "-b:a", "128k", "-ar", "44100"])
        comando.extend([
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", str(random.randint(21, 25)),
            "-b:v", random.choice(["1500k", "2000k", "2500k"]),
            "-pix_fmt", "yuv420p",
        ])

    for kv in metadata_changes:
        comando.extend(["-metadata", kv])

    comando.extend([
        "-metadata", f"encoder=FFmpeg Custom {random.randint(1000, 9999)}",
        "-metadata", f"creation_time={time.strftime('%Y-%m-%dT%H:%M:%S.000000Z', time.gmtime(ts//1000))}",
        "-movflags", "+faststart",
        str(output_file)
    ])

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
