FROM ubuntu:20.04

LABEL REGISTRY="local-only"
LABEL IMAGE="mitk-base"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

# =================================================================================================
# MITK-build base image
# =================================================================================================

# CMAKE config
ENV CMAKE_VERSION_A=3.18
ENV CMAKE_VERSION_B=3.18.2

# QT config
ENV QT_VERSION_MINOR 5.12
ENV QT_VERSION_PATCH 5.12.9

WORKDIR /opt

RUN echo 'debconf debconf/frontend select Noninteractive' | debconf-set-selections &&  apt-get update && apt-get install -q -y --no-install-recommends \
    build-essential \
    git \
    libglu1-mesa-dev \
    libtiff5-dev \
    libwrap0-dev \
    libxcomposite1 \
    libxcursor1 \
    libxi-dev \
    libxkbcommon-x11-0 \
    libxt-dev \
    mesa-common-dev \
    ca-certificates \
    curl \
    ninja-build \
    libasound2 \
    libnss3-dev \
    libnss3 \
    libnspr4-dev \
    libxtst6 \
    file \
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
    libfontconfig1-dev \ 
    libdbus-1-3 \
    doxygen \
    && rm -rf /var/lib/apt/lists/*

# Install Cmake
RUN curl --silent --location -o cmake-installer.sh https://cmake.org/files/v${CMAKE_VERSION_A}/cmake-${CMAKE_VERSION_B}-Linux-x86_64.sh  \
    && mkdir /opt/cmake \
    && chmod +x cmake-installer.sh \
    && sh ./cmake-installer.sh --prefix=/opt/cmake --skip-license \
    && ln -s /opt/cmake/bin/cmake /usr/local/bin/cmake \
    && rm cmake-installer.sh

