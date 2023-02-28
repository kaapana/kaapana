FROM python:3.9.16-slim

LABEL REGISTRY="local-only"
LABEL IMAGE="base-python-cpu"
LABEL VERSION="latest"
LABEL CI_IGNORE="False"

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /kaapana/base

<<<<<<< HEAD
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
    && rm -rf /var/lib/apt/lists/*
=======
COPY files/requirements.system /kaapana/base/
RUN apt-get update -q -y && apt-get install -y --no-install-recommends apt-utils && \
    cat /kaapana/base/requirements.system | xargs apt-get install -y --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*
>>>>>>> b0d47d1c823a51dd3af874a59ed61ecd4d468b94

# Common Python packages
COPY files/requirements.txt /kaapana/base/
RUN python -m pip install --upgrade setuptools pip && pip3 install -r /kaapana/base/requirements.txt

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
