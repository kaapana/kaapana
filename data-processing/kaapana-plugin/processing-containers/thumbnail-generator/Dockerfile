FROM local-only/base-python-cpu:latest

LABEL IMAGE="thumbnail-generator"
LABEL BUILD_IGNORE="False"

RUN apt-get update -y && apt-get install -y --no-install-recommends \
    ffmpeg  \
    libsm6  \
    libxext6 \
    libfreetype6-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY files/requirements.txt /
COPY --from=constraints 0.7.0.txt /constraints.txt
RUN pip3 install -c /constraints.txt --no-cache-dir -r /requirements.txt

COPY files/* /kaapana/app/

CMD ["python3", "-u", "/kaapana/app/thumbnail-generator.py"]