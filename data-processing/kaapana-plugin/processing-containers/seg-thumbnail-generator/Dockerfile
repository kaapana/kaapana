FROM local-only/base-python-cpu:latest

LABEL IMAGE="seg-thumbnail-generator"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

RUN apt-get update -y && apt-get install -y --no-install-recommends \
    ffmpeg  \
    libsm6  \
    libxext6 \
    libfreetype6-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY files/requirements.txt /
RUN pip3 install --no-cache-dir -r /requirements.txt

COPY files/* /kaapana/app/

CMD ["python3", "-u", "/kaapana/app/seg-thumbnail-generator.py"]