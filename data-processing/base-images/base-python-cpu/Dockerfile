FROM ubuntu:24.04

LABEL REGISTRY="local-only"
LABEL IMAGE="base-python-cpu"
LABEL VERSION="latest"
LABEL BUILD_IGNORE="False"

ENV DEBIAN_FRONTEND=noninteractive

# Remove default non-root user 1000 introduced in ubuntu23.04, it affects all adduser commands in subsequent Dockerfiles
# https://bugs.launchpad.net/cloud-images/+bug/2005129
RUN userdel -r ubuntu

# Install apt packages
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
    python3.12 \
    python3.12-venv \
    python3-pip \
    python-is-python3 \
    && rm -rf /var/lib/apt/lists/*

# For python3.11+ externally managed environments are introduced
# It requires the use of venv, see PEP668 https://peps.python.org/pep-0668/

# Create venv to handle pip installations
RUN python3 -m venv /opt/venv
# Activate venv and upgrade pip inside it
RUN /opt/venv/bin/pip install --upgrade pip
# Make venv's python and pip accessible in the PATH
ENV PATH="/opt/venv/bin:$PATH"

# Install torch for cuda 11.8
RUN python3 -m pip install torch torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu118

# Install requirements
COPY files/requirements.txt /app/
RUN python3 -m pip install --upgrade setuptools pip && pip3 install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.3.0/constraints.txt -r /app/requirements.txt

# Install code server and python extension
RUN wget https://code-server.dev/install.sh
RUN /bin/bash install.sh --version 4.95.2
RUN code-server --install-extension ms-python.python

# Copy federated files
COPY files/kaapana_federated /kaapana_federated

# Install kaapanapy pip package
COPY files/kaapana_python /kaapana_python
WORKDIR /kaapana_python
RUN python3 -m build 
RUN python3 -m pip install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.3.0/constraints.txt dist/kaapanapy-0.0.1.tar.gz

WORKDIR /kaapana/app
