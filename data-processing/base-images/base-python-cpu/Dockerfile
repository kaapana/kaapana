FROM docker.io/python:3.9.17-slim

LABEL REGISTRY="local-only"
LABEL IMAGE="base-python-cpu"
LABEL VERSION="latest"
LABEL BUILD_IGNORE="False"

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
RUN python -m pip install -c https://raw.githubusercontent.com/kaapana/kaapana/0.2.1/build-scripts/constraints-0.2.1.txt --upgrade setuptools pip && pip3 install -r /app/requirements.txt

# Code server
RUN wget https://code-server.dev/install.sh
RUN /bin/bash install.sh --version 4.2.0
RUN code-server --install-extension ms-python.python

COPY files/kaapana_federated /kaapana_federated

WORKDIR /kaapana/app
