FROM python:3.12-slim

LABEL IMAGE="nninteractive-proxy"
LABEL BUILD_IGNORE="False"

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive

RUN apt-get update -y && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /kaapana/app

COPY files/requirements.txt /kaapana/app/requirements.txt
RUN pip install --upgrade pip setuptools wheel \
    && pip install -r /kaapana/app/requirements.txt

COPY files/app /kaapana/app/app

EXPOSE 8002

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
