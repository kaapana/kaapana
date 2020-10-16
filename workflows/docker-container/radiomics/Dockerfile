FROM ubuntu:20.04 as build_container

LABEL IMAGE="mitk-radiomics"
LABEL VERSION="15.10.20-master"
LABEL CI_IGNORE="False"

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

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
    qtbase5-dev qtscript5-dev libqt5svg5-dev libqt5opengl5-dev libqt5xmlpatterns5-dev qtwebengine5-dev qttools5-dev libqt5x11extras5-dev qtxmlpatterns5-dev-tools libqt5webengine-data \
    && rm -rf /var/lib/apt/lists/*

ENV CMAKE_VERSION_A=3.18
ENV CMAKE_VERSION_B=3.18.2

# Install Cmake
RUN curl --silent --location -o cmake-installer.sh https://cmake.org/files/v${CMAKE_VERSION_A}/cmake-${CMAKE_VERSION_B}-Linux-x86_64.sh  \
    && mkdir /opt/cmake \
    && chmod +x cmake-installer.sh \
    && sh ./cmake-installer.sh --prefix=/opt/cmake --skip-license \
    && ln -s /opt/cmake/bin/cmake /usr/local/bin/cmake \
    && rm cmake-installer.sh

##################################################
###############   Install the QT   ###############
##################################################
RUN apt-get update && apt-get install -y --no-install-recommends \
    libfontconfig1-dev \ 
    libdbus-1-3 \
    && rm -rf /var/lib/apt/lists/*
    
# Shallow-clone latest master branch of MITK into MITK directory
ENV MITK_BRANCH=master
# master @ Thu, Oct 15, 2020
ENV MITK_REV=0f33cec9e310
RUN git clone --single-branch --branch ${MITK_BRANCH} https://phabricator.mitk.org/source/mitk.git MITK && cd MITK && git checkout ${MITK_REV}

# Generate Ninja build script for MITK to build a minimum configuration with apps in Release mode into MITK-superbuild directory
RUN cmake -G Ninja -S MITK -B MITK-superbuild
RUN cmake -S MITK -B MITK-superbuild -D CMAKE_BUILD_TYPE:STRING=Release -D MITK_BUILD_CONFIGURATION:STRING=ClassificationCmdApps -D MITK_CUSTOM_REVISION_DESC:STRING=Radiomics

RUN git config --global url.https://github.com/.insteadOf git://github.com/
# Build MITK superbuild and configure MITK build
RUN cmake --build MITK-superbuild

# Build MitkFileConverter app
RUN cmake --build MITK-superbuild/MITK-build --target package 

RUN mkdir /opt/final_package
RUN cp /opt/MITK-superbuild/MITK-build/MITK-Radiomics-linux-x86_64.tar.gz /opt/final_package/MITK-Radiomics-linux-x86_64.tar.gz

################################################################################################################################
###################################################### Final Container #########################################################
################################################################################################################################
FROM ubuntu:20.04

ENV TZ=Europe/Berlin
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get update && apt-get install -y --no-install-recommends \
    libglu1-mesa-dev \
    libxt-dev \
    libgomp1 \
    xvfb \
    qtbase5-dev \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /tmp_src /mitk
WORKDIR /tmp_src
COPY --from=build_container /opt/final_package/MITK-Radiomics-linux-x86_64.tar.gz ./MITK-Radiomics-linux-x86_64.tar.gz
RUN tar -xzf MITK-Radiomics-linux-x86_64.tar.gz -C ./ && mv ./MITK-Radiomics-linux-x86_64/* /mitk && rm -rf /tmp_src

WORKDIR /
ENV BATCHES_INPUT_DIR /input
ENV OPERATOR_IN_DIR initial-input
ENV OPERATOR_OUT_DIR radiomics

COPY files/radiomics.sh /

CMD ["/bin/bash", "/radiomics.sh"]
