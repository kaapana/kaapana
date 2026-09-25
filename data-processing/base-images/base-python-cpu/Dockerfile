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
    bzip2 \
    xz-utils \
    make \
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
# Keep pip's download cache out of every layer built on this image (the cache of a
# large package set weighs GBs and is never read again). Inherited by derived images.
ENV PIP_NO_CACHE_DIR=1

# No compilers: every pinned package ships a wheel. An image that has to compile a
# package installs build-essential itself. bzip2, xz-utils and make are listed above
# because they used to arrive with build-essential and derived images rely on them
# (tar unpacking .bz2/.xz archives, installers, `make html`). torch lives in
# base-python-gpu; base this image's derivatives on that one when they import torch
# (also through monai or kaapana_federated).

# Install requirements
COPY files/requirements.txt /app/
RUN python3 -m pip install --upgrade setuptools pip && pip3 install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.7.0/constraints.txt -r /app/requirements.txt

# No code-server here: a development server gets it from the code-server-init
# container of dev-server-chart (install in base-images/base-code-server).

# Install kaapanapy pip package
COPY files/kaapanapy-shim /app/kaapanapy-shim
WORKDIR /app/kaapanapy-shim
RUN python3 -m build 
RUN python3 -m pip install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.7.0/constraints.txt dist/kaapanapy-0.0.1.tar.gz

WORKDIR /kaapana/app
