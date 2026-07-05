# FaceFusion — serviço de face swap de IMAGEM, self-contained no Railway (CPU).
# Todos os modelos são baixados no build (force-download) => zero download em runtime.
FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1

# Libs de sistema exigidas pelo FaceFusion (OpenCV, ffmpeg, download de modelos).
RUN apt-get update && apt-get install -y --no-install-recommends \
        git curl ffmpeg libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt

# Versão do FaceFusion. Fixe uma tag (ex: 3.4.1) para builds reproduzíveis;
# a CLI muda entre versões maiores.
ARG FACEFUSION_VERSION=master
RUN git clone https://github.com/facefusion/facefusion.git \
    && cd facefusion && git checkout "${FACEFUSION_VERSION}"

WORKDIR /opt/facefusion

# Instalação do FaceFusion com onnxruntime CPU (sem conda).
# 'onnxruntime' é argumento POSICIONAL (não --onnxruntime): use "default".
RUN python install.py default --skip-conda

# Pré-baixa TODOS os modelos no build -> imagem self-contained, nada em runtime.
# (Deixa a imagem grande. Se preferir enxugar, troque por um headless-run de
#  aquecimento só com os modelos usados — ver README.)
RUN python facefusion.py force-download

# Dependências do wrapper HTTP.
RUN pip install "fastapi==0.115.0" "uvicorn[standard]==0.30.6" "python-multipart==0.0.9"

COPY app.py /opt/facefusion/app.py

EXPOSE 8000
# Shell form para expandir $PORT (o Railway injeta a porta em runtime).
CMD uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}
