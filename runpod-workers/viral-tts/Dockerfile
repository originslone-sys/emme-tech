# XTTS-v2 (Coqui TTS) na GPU. O modelo é baixado no build para acelerar o
# cold start. COQUI_TOS_AGREED aceita a licença do modelo XTTS.
FROM pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime

ENV DEBIAN_FRONTEND=noninteractive
ENV COQUI_TOS_AGREED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pré-baixa o modelo XTTS-v2 para a imagem (evita download no primeiro job)
RUN python -c "from TTS.api import TTS; TTS('tts_models/multilingual/multi-dataset/xtts_v2')"

COPY handler.py .

CMD ["python", "-u", "handler.py"]
