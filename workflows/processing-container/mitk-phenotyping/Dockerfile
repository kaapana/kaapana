FROM ubuntu:20.04
ARG DEBIAN_FRONTEND=noninteractive

LABEL REGISTRY="local-only"
LABEL IMAGE="mitk-phenotyping"
LABEL VERSION="2021-02-18-vdev"
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
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src
RUN wget --no-check-certificate https://www.mitk.org/download/kaapana/phenotyping/MITK-v2021.02-linux-x86_64.tar.gz -O /src/mitk.tar.gz \
    && tar -xzf /src/mitk.tar.gz --strip 1 -C /src/ && rm -rf /src/mitk.tar.gz

WORKDIR /src

CMD ["/bin/bash", "echo","Do not use this container directly - only as base-image!"]
