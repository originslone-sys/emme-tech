# Imagem CUDA com FFmpeg (h264_nvenc habilitado) + Python para o worker RunPod.
FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        fonts-dejavu-core \
        python3 \
        python3-pip \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Caminhos a partir da RAIZ do repositório (contexto de build do RunPod/GitHub).
# Para build manual, rode a partir da raiz com:
#   docker build -f runpod-workers/viral-render/Dockerfile -t SEU_USUARIO/emme-viral-render .
COPY runpod-workers/viral-render/requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY runpod-workers/viral-render/handler.py .

CMD ["python3", "-u", "handler.py"]
