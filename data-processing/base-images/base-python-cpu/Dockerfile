FROM docker.io/python:3.9.16-slim

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
COPY files/requirements.txt /app/
RUN python -m pip install -c https://raw.githubusercontent.com/kaapana/kaapana/0.2.0/build-scripts/constraints-0.2.0.txt --upgrade setuptools pip && pip3 install -r /app/requirements.txt

# Code server
RUN wget https://code-server.dev/install.sh
RUN /bin/bash install.sh --version 4.2.0
RUN code-server --install-extension ms-python.python

# Juyterlab
# Disable security token for Jupyter lab
RUN jupyter-lab --generate-config \
 && sed -i "s/^.*ServerApp.token.*$/c.ServerApp.token = ''/g" /root/.jupyter/jupyter_lab_config.py
COPY files/jupyterlab.sh /
COPY files/kaapana_federated /kaapana_federated

WORKDIR /kaapana/app
