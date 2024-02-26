FROM ubuntu:22.04

LABEL REGISTRY="local-only"
LABEL IMAGE="base-python-cpu"
LABEL VERSION="latest"
LABEL BUILD_IGNORE="False"

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app
RUN apt-get update -y && apt-get install -y --no-install-recommends \
    git \
    htop \
    zip \
    unzip \
    nano \
    dcmtk \
    ca-certificates \
    build-essential \
    wget \
    curl \
    procps \
    python3.10 \
    python3-pip \
    python-is-python3 \
    && rm -rf /var/lib/apt/lists/*

# Common Python packages
RUN python -m pip install torch torchvision==0.15.2+cu118 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cu118

COPY files/requirements.txt /app/
RUN python -m pip install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.3.0/constraints.txt --upgrade setuptools pip && pip3 install -r /app/requirements.txt

# Code server
RUN wget https://code-server.dev/install.sh
RUN /bin/bash install.sh --version 4.2.0
RUN code-server --install-extension ms-python.python

COPY files/kaapana_federated /kaapana_federated

WORKDIR /kaapana/app
