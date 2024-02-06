FROM docker.io/python:3.9.18-slim

LABEL REGISTRY="local-only"
LABEL IMAGE="base-python-cpu"
LABEL VERSION="latest"
LABEL CI_IGNORE="False"

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app
RUN apt-get update -y && apt-get install -y --no-install-recommends \
    apt-utils \
    git \
    htop \
    zip \
    unzip \
    nano \
    dcmtk \
    pandoc \
    texlive-xetex \
    texlive-fonts-recommended \
    texlive-plain-generic \
    ca-certificates \
    build-essential \
    wget \
    curl \
    procps \
    libpng-dev \
    libjpeg-dev \
    && rm -rf /var/lib/apt/lists/*

# Common Python packages
RUN python -m pip install torch torchvision==0.15.2+cu118 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cu118

COPY files/requirements.txt /app/
RUN python -m pip install -c https://raw.githubusercontent.com/kaapana/kaapana/feature/PoC/build-scripts/constraints-0.2.6.txt --upgrade setuptools pip && pip3 install -r /app/requirements.txt

# Code server and jupiterlab are not installed in this project and can therefore not be used
# as "dev_server" to debug pods.

COPY files/kaapana_federated /kaapana_federated

WORKDIR /kaapana/app
