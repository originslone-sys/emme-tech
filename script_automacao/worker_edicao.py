import os
import time
import json
import shutil
import logging
import subprocess
import random
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# =========================
# CONFIG
# =========================

@dataclass
class Config:
    base_url: str = "https://emmetech.digital"
    api_key: str = "a4aLYTawyy4HEUGQIoHCSjDOtSrxh4SA"
    worker_id: str = os.environ.get("WORKER_ID", "WIN-PC-01")

    # Quantas tarefas tentar "claim" por vez
    claim_batch: int = 1

    # Polling quando NÃO há tarefas (segundos)
    poll_seconds_idle: int = 12

    # Polling entre tarefas (segundos) — evita bater rápido demais
    poll_seconds_between_tasks: int = 1

    # Backoff mínimo quando der erro no loop (segundos)
    error_backoff_seconds: int = 8

    # Se true, apaga bruto no servidor ao concluir
    delete_on_server: bool = True

    local_root: str = r"D:\automacao_videos"
    input_dir: str = r"D:\automacao_videos\input"
    output_dir: str = r"D:\automacao_videos\output"
    processed_dir: str = r"D:\automacao_videos\processed"
    failed_dir: str = r"D:\automacao_videos\failed"
    logs_dir: str = r"D:\automacao_videos\logs"

    # Endpoints
    claim_ep: str = "/api/edicao_claim.php"
    status_ep: str = "/api/edicao_status.php"
    download_ep: str = "/api/bruto_download.php"
    delete_ep: str = "/api/bruto_delete.php"
    upload_final_ep: str = "/api/receber_video.php"

    # HTTP / Retry
    http_timeout_claim: int = 30
    http_timeout_status: int = 30
    http_timeout_download: int = 300
    http_timeout_upload: int = 300

    # Sanity checks
    min_download_bytes: int = 100_000
    min_output_bytes: int = 200_000

    # Se quiser remover legenda de vez, deixe True (envia legenda vazia no upload final)
    force_empty_legenda: bool = True


CFG = Config()

# =========================
# LOGGING
# =========================

os.makedirs(CFG.logs_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(CFG.logs_dir, "worker_edicao.log"), encoding="utf-8"),
        logging.StreamHandler()
    ],
)


def ensure_dirs():
    for d in [CFG.input_dir, CFG.output_dir, CFG.processed_dir, CFG.failed_dir]:
        os.makedirs(d, exist_ok=True)


def api_url(path: str) -> str:
    return CFG.base_url.rstrip("/") + path


def build_session() -> requests.Session:
    """
    Sessão HTTP hardenizada para evitar RemoteDisconnected:
    - força Connection: close (evita keep-alive problemático em alguns hosts/WAF)
    - retry com backoff em erros transitórios
    """
    s = requests.Session()
    s.headers.update({
        "User-Agent": f"VideoWorker/1.1 ({CFG.worker_id})",
        "Accept": "application/json",
        "Connection": "close",
    })

    retry = Retry(
        total=6,
        connect=6,
        read=6,
        backoff_factor=1.2,  # 1.2s, 2.4s, 4.8s...
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
        raise_on_status=False,
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(
        max_retries=retry,
        pool_connections=1,
        pool_maxsize=1
    )
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s


def req(session: requests.Session, method: str, url: str, *, params=None, data=None, files=None, stream=False, timeout=120) -> requests.Response:
    """
    Request com logs melhores. Se o servidor fechar conexão, vai cair aqui com exception,
    mas o loop se recupera com backoff.
    """
    try:
        r = session.request(
            method,
            url,
            params=params,
            data=data,
            files=files,
            stream=stream,
            timeout=timeout,
        )
        return r
    except Exception as e:
        # Inclui os parâmetros principais para facilitar debug
        p = ""
        if params:
            try:
                safe_params = dict(params)
                if "api_key" in safe_params:
                    safe_params["api_key"] = "***"
                p = f" params={safe_params}"
            except Exception:
                pass
        raise RuntimeError(f"HTTP error {method} {url}:{p} -> {e}") from e


def jitter(seconds: int, spread: float = 0.25) -> float:
    """
    adiciona jitter +- spread para reduzir padrão de polling (bom contra WAF/rate-limit)
    """
    return max(0.0, seconds * (1 + random.uniform(-spread, spread)))


def claim_tasks(session: requests.Session) -> List[Dict[str, Any]]:
    url = api_url(CFG.claim_ep)
    params = {
        "api_key": CFG.api_key,
        "worker_id": CFG.worker_id,
        "limit": str(CFG.claim_batch),
    }
    r = req(session, "GET", url, params=params, timeout=CFG.http_timeout_claim)
    if r.status_code != 200:
        # tenta logar um pedaço do body se houver
        body = ""
        try:
            body = r.text[:800]
        except Exception:
            pass
        raise RuntimeError(f"claim HTTP {r.status_code}: {body}")

    try:
        js = r.json()
    except Exception:
        raise RuntimeError(f"claim inválido (não-JSON): {r.text[:800]}")

    if not js.get("sucesso"):
        raise RuntimeError(f"claim failed: {js}")
    return js.get("tarefas", []) or []


def set_status(session: requests.Session, task_id: int, status: str, *, erro_msg: Optional[str] = None):
    url = api_url(CFG.status_ep)
    data = {
        "api_key": CFG.api_key,
        "id": str(task_id),
        "status": status,
        "worker_id": CFG.worker_id,
    }
    if erro_msg is not None:
        data["erro_msg"] = erro_msg[:2000]

    r = req(session, "POST", url, data=data, timeout=CFG.http_timeout_status)
    if r.status_code != 200:
        raise RuntimeError(f"status HTTP {r.status_code}: {r.text[:800]}")

    try:
        js = r.json()
    except Exception:
        raise RuntimeError(f"status inválido (não-JSON): {r.text[:800]}")

    if not js.get("sucesso"):
        raise RuntimeError(f"status failed: {js}")


def safe_local_name(name: str) -> str:
    base = os.path.basename(name)
    base = "".join(c for c in base if c.isalnum() or c in "._-")
    return base[:180] if base else "bruto.mp4"


def download_bruto(session: requests.Session, bruto_arquivo: str) -> str:
    url = api_url(CFG.download_ep)
    params = {"api_key": CFG.api_key, "file": bruto_arquivo}

    local_name = safe_local_name(bruto_arquivo)
    local_path = os.path.join(CFG.input_dir, local_name)

    # Sempre sobrescreve se existir (evita confusão em retry)
    if os.path.exists(local_path):
        try:
            os.remove(local_path)
        except Exception:
            pass

    with req(session, "GET", url, params=params, stream=True, timeout=CFG.http_timeout_download) as r:
        if r.status_code != 200:
            raise RuntimeError(f"download HTTP {r.status_code}: {r.text[:200]}")

        with open(local_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

    size = os.path.getsize(local_path)
    if size < CFG.min_download_bytes:
        raise RuntimeError(f"download pequeno demais: {local_path} ({size} bytes)")
    return local_path


def run_fabrica(input_path: str) -> str:
    """
    Mantive a mesma interface do seu fabrica_videos.py:
      python fabrica_videos.py --input <...> --output-dir <...>
    """
    cmd = [
        os.path.join(CFG.local_root, ".venv", "Scripts", "python.exe"),
        os.path.join(CFG.local_root, "fabrica_videos.py"),
        "--input", input_path,
        "--output-dir", CFG.output_dir,
        "--on-success", "keep"
    ]
    logging.info("Rodando fabrica: %s", " ".join(cmd))

    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        raise RuntimeError(
            f"fabrica falhou ({p.returncode})\n"
            f"STDOUT:\n{p.stdout}\n"
            f"STDERR:\n{p.stderr}"
        )

    outs = [os.path.join(CFG.output_dir, f) for f in os.listdir(CFG.output_dir)]
    outs = [p for p in outs if os.path.isfile(p) and p.lower().endswith(".mp4")]
    if not outs:
        raise RuntimeError("fabrica não gerou mp4 em output/")

    out = max(outs, key=os.path.getmtime)
    size = os.path.getsize(out)
    if size < CFG.min_output_bytes:
        raise RuntimeError(f"output pequeno demais: {out} ({size} bytes)")
    return out


def upload_editado(session: requests.Session, output_path: str, vmos_id: str, legenda: str) -> Dict[str, Any]:
    url = api_url(CFG.upload_final_ep)

    if CFG.force_empty_legenda:
        legenda = ""

    data = {"api_key": CFG.api_key, "vmos_id": vmos_id, "legenda": legenda}

    with open(output_path, "rb") as f:
        files = {"arquivo": ("editado.mp4", f, "video/mp4")}
        r = req(session, "POST", url, data=data, files=files, timeout=CFG.http_timeout_upload)

    if r.status_code != 200:
        raise RuntimeError(f"upload HTTP {r.status_code}: {r.text[:800]}")

    try:
        return r.json()
    except Exception:
        return {"raw": r.text[:1000]}


def delete_bruto_server(session: requests.Session, bruto_arquivo: str):
    url = api_url(CFG.delete_ep)
    data = {"api_key": CFG.api_key, "file": bruto_arquivo}

    r = req(session, "POST", url, data=data, timeout=CFG.http_timeout_status)
    if r.status_code != 200:
        raise RuntimeError(f"delete HTTP {r.status_code}: {r.text[:800]}")

    try:
        js = r.json()
    except Exception:
        raise RuntimeError(f"delete inválido (não-JSON): {r.text[:800]}")

    if not js.get("sucesso"):
        raise RuntimeError(f"delete failed: {js}")


def move_to(folder: str, path: str):
    # Se outro processo já moveu/deletou o arquivo (ex: fabrica com on-success move/delete), não falha.
    if not path or not os.path.exists(path):
        logging.warning("Arquivo não existe para mover (ignorando): %s", path)
        return
    os.makedirs(folder, exist_ok=True)
    dest = os.path.join(folder, os.path.basename(path))
    if os.path.exists(dest):
        base, ext = os.path.splitext(dest)
        dest = f"{base}_{int(time.time())}{ext}"
    shutil.move(path, dest)


def process_task(session: requests.Session, t: Dict[str, Any]):
    task_id = int(t["id"])
    vmos_id = str(t.get("vmos_id", "") or "")
    legenda = str(t.get("legenda", "") or "")
    bruto_arquivo = str(t.get("bruto_arquivo", "") or "")

    if not vmos_id or not bruto_arquivo:
        raise RuntimeError(f"Tarefa inválida: {t}")

    logging.info("Tarefa %s | vmos_id=%s | bruto=%s", task_id, vmos_id, bruto_arquivo)

    # Se claim já seta "baixando", aqui pulamos direto para editando
    set_status(session, task_id, "editando")

    local_in = download_bruto(session, bruto_arquivo)
    try:
        local_out = run_fabrica(local_in)

        resp = upload_editado(session, local_out, vmos_id, legenda)
        logging.info("Upload final resp: %s", json.dumps(resp, ensure_ascii=False)[:900])

        set_status(session, task_id, "concluido", erro_msg=None)

        if CFG.delete_on_server:
            delete_bruto_server(session, bruto_arquivo)

        move_to(CFG.processed_dir, local_in)

        # opcional: limpar output
        try:
            os.remove(local_out)
        except Exception:
            pass

    except Exception as e:
        logging.exception("Erro na tarefa %s", task_id)
        try:
            set_status(session, task_id, "erro", erro_msg=str(e))
        except Exception as e2:
            logging.error("Falha ao marcar erro no servidor (task %s): %s", task_id, e2)

        try:
            move_to(CFG.failed_dir, local_in)
        except Exception:
            pass

        # não re-raise para não matar loop
        return


def main():
    ensure_dirs()
    session = build_session()

    logging.info("Worker iniciado | worker_id=%s | base=%s", CFG.worker_id, CFG.base_url)

    while True:
        try:
            tasks = claim_tasks(session)
            if not tasks:
                time.sleep(jitter(CFG.poll_seconds_idle))
                continue

            for t in tasks:
                process_task(session, t)
                time.sleep(jitter(CFG.poll_seconds_between_tasks, spread=0.5))

        except Exception as e:
            logging.error("Loop error: %s", e)
            time.sleep(jitter(max(CFG.error_backoff_seconds, CFG.poll_seconds_idle)))


if __name__ == "__main__":
    main()
