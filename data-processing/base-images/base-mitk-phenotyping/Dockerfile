FROM ubuntu:20.04

ARG DEBIAN_FRONTEND=noninteractive

LABEL REGISTRY="local-only"
LABEL IMAGE="base-mitk-phenotyping"
LABEL VERSION="latest"
LABEL CI_IGNORE="False"

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    libfreetype6 \
    libglu1-mesa-dev \
    libglib2.0-0 \
    libgomp1 \
    libxt-dev \
    xvfb \
    qtbase5-dev \
    python3 \
    python3-pip \
    dcmtk \
    jq \
    && rm -rf /var/lib/apt/lists/*

COPY files/requirements.txt /
RUN python3 -m pip install --no-cache-dir -r /requirements.txt && rm /requirements.txt 

WORKDIR /kaapanasrc
RUN wget --no-check-certificate https://www.mitk.org/download/kaapana/phenotyping/MITK-v2021.02-linux-x86_64.tar.gz -O /kaapanasrc/mitk.tar.gz \
    && tar -xzf /kaapanasrc/mitk.tar.gz --strip 1 -C /kaapanasrc/ && rm -rf /kaapanasrc/mitk.tar.gz

WORKDIR /kaapanasrc

CMD ["echo","Do not use this container directly - only as base-image!"]
