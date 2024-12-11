FROM local-only/base-python-cpu:latest

ARG DEBIAN_FRONTEND=noninteractive

LABEL REGISTRY="local-only"
LABEL IMAGE="base-mitk"
LABEL VERSION="latest"
LABEL BUILD_IGNORE="False"

WORKDIR /kaapana/app

RUN apt-get update -y && apt-get install -y --no-install-recommends \
    ca-certificates \
    # CVE-2023-46343 
    linux-libc-dev \
    libtiff5-dev \
    libwrap0-dev \
    libxcomposite1 \
    libxcursor1 \
    libxi-dev \
    libxkbcommon-x11-0 \
    mesa-common-dev \
    libssl-dev \
    libglu1-mesa-dev \
    libxt-dev \
    libgomp1 \
    qtbase5-dev \
    qtscript5-dev \
    libqt5svg5-dev \
    libqt5opengl5-dev \
    libqt5xmlpatterns5-dev \
    qtwebengine5-dev \
    qttools5-dev \
    libqt5x11extras5-dev \
    qtxmlpatterns5-dev-tools \
    libqt5webengine-data \
    at-spi2-core \
    libxcb-cursor0 \
    && rm -rf /var/lib/apt/lists/*

RUN wget --no-check-certificate https://www.mitk.org/download/kaapana/workbench/MITK-v2024.12-linux-x86_64.tar.gz -O /kaapana/app/mitk.tar.gz \
    && tar -xzf /kaapana/app/mitk.tar.gz --strip 1 -C /kaapana/app/ \
    && rm -rf /kaapana/app/mitk.tar.gz

    



CMD ["echo","Do not use this container directly - only as base-image!"]
