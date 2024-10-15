FROM local-only/base-python-cpu:latest

LABEL IMAGE="json2meta"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

RUN apt-get update -y && apt-get install -y --no-install-recommends \
    ffmpeg  \
    libsm6  \
    libxext6 \
    libfreetype6-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY files/* /kaapana/app/

CMD ["python3", "-u", "/kaapana/app/start.py"]